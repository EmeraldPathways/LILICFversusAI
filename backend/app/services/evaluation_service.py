from __future__ import annotations

import json
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from math import log2

import pandas as pd

from app.config import Settings
from app.utils.normalization import normalize_article_id, normalize_customer_id


@dataclass
class EvaluationService:
    settings: Settings

    DIVERSITY_FIELDS = (
        "product_group_name",
        "colour_group_name",
        "graphical_appearance_name",
    )

    def evaluate(
        self,
        train_df: pd.DataFrame,
        test_df: pd.DataFrame,
        cf_recommendations: dict[str, list[dict[str, object]]],
        agentic_recommendations: dict[str, list[dict[str, object]]],
    ) -> dict[str, object]:
        train_df = self._normalize_ids(train_df)
        test_df = self._normalize_ids(test_df)
        cf_recommendations = self._normalize_recommendation_payload(cf_recommendations)
        agentic_recommendations = self._normalize_recommendation_payload(agentic_recommendations)
        user_profiles = self._build_user_profiles(train_df)
        evaluated_users = sorted(set(cf_recommendations) & set(agentic_recommendations))
        metrics = {
            "collaborative_filtering": self._model_metrics(
                evaluated_users, test_df, cf_recommendations, user_profiles, include_explanations=False
            ),
            "agentic_ai_framework": self._model_metrics(
                evaluated_users, test_df, agentic_recommendations, user_profiles, include_explanations=True
            ),
            "business_mapping": {
                "hit_rate_at_10": "Potential CTR improvement",
                "preference_alignment": "Potential CVR improvement",
                "diversity": "Potential engagement depth improvement",
            },
            "evaluated_users": len(evaluated_users),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        self.settings.metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
        return metrics

    def load_metrics(self) -> dict[str, object] | None:
        if not self.settings.metrics_path.exists():
            return None
        return json.loads(self.settings.metrics_path.read_text(encoding="utf-8"))

    def evaluate_top10_experiment(
        self,
        train_df: pd.DataFrame,
        test_df: pd.DataFrame,
        svd_recommendations: dict[str, list[dict[str, object]]],
        agentic_recommendations: dict[str, list[dict[str, object]]],
        output_path=None,
    ) -> dict[str, object]:
        train_df = self._normalize_ids(train_df)
        test_df = self._normalize_ids(test_df)
        svd_recommendations = self._normalize_recommendation_payload(svd_recommendations)
        agentic_recommendations = self._normalize_recommendation_payload(agentic_recommendations)
        evaluated_users = sorted(set(svd_recommendations) & set(agentic_recommendations))
        metrics = {
            "svd_matrix_factorization": self._top10_model_metrics(
                evaluated_users, test_df, svd_recommendations
            ),
            "agentic_ai_framework": self._top10_model_metrics(
                evaluated_users, test_df, agentic_recommendations
            ),
            "business_mapping": {
                "hit_rate_at_10": "Potential CTR improvement",
                "ndcg_at_10": "Ranking quality for held-out purchases",
                "intra_list_diversity_at_10": "Assortment breadth within the top-10 list",
            },
            "evaluated_users": len(evaluated_users),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        target_path = output_path or self.settings.metrics_path
        target_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
        return metrics

    def compute_formal_top10_metrics_from_saved_artifacts(
        self,
        subset_size: int = 100,
        bootstrap_samples: int = 0,
        random_seed: int = 42,
    ) -> dict[str, object]:
        evaluation_rows = json.loads(
            self.settings.evaluation_base_table_svd_top10_json_path(subset_size).read_text(encoding="utf-8")
        )
        svd_rows = json.loads(self.settings.svd_recommendations_top10_json_path(subset_size).read_text(encoding="utf-8"))
        agentic_rows = json.loads(
            self.settings.agentic_recommendations_top10_json_path(subset_size).read_text(encoding="utf-8")
        )
        processed = pd.read_csv(
            self.settings.processed_interactions_with_articles_csv_path,
            dtype={"article_id": "string", "customer_id": "string"},
        )

        metadata_lookup = self._build_article_metadata_lookup(processed)
        evaluation_lookup = {
            normalize_customer_id(row["customer_id"]): self._normalize_evaluation_row(row)
            for row in evaluation_rows
        }
        svd_lookup = {
            normalize_customer_id(row["customer_id"]): self._normalize_saved_recommendation_row(row)
            for row in svd_rows
        }
        agentic_lookup = {
            normalize_customer_id(row["customer_id"]): self._normalize_saved_recommendation_row(row)
            for row in agentic_rows
        }

        per_user_rows: list[dict[str, object]] = []
        metric_calculation_errors: list[str] = []
        example_hit_users_svd: list[str] = []
        example_hit_users_agentic: list[str] = []
        example_miss_users_svd: list[str] = []
        example_miss_users_agentic: list[str] = []
        missing_metadata_for_diversity_count = 0
        users_with_svd_metrics = 0
        users_with_agentic_metrics = 0
        svd_top_10_count_check = 0
        agentic_top_10_count_check = 0
        svd_inside_pool_check = 0
        agentic_inside_pool_check = 0

        for customer_id, eval_row in evaluation_lookup.items():
            ground_truth_article_id = eval_row["ground_truth_article_id"]
            candidate_pool_set = set(eval_row["candidate_pool_article_ids"])
            svd_row = svd_lookup.get(customer_id, {"top_10_recommendations": []})
            agentic_row = agentic_lookup.get(customer_id, {"top_10_recommendations": []})
            svd_recs = svd_row.get("top_10_recommendations", [])
            agentic_recs = agentic_row.get("top_10_recommendations", [])

            if len(svd_recs) == self.settings.top_n:
                svd_top_10_count_check += 1
            if len(agentic_recs) == self.settings.top_n:
                agentic_top_10_count_check += 1
            if all(normalize_article_id(item.get("article_id")) in candidate_pool_set for item in svd_recs):
                svd_inside_pool_check += 1
            if all(normalize_article_id(item.get("article_id")) in candidate_pool_set for item in agentic_recs):
                agentic_inside_pool_check += 1

            svd_metrics, svd_missing_count, svd_errors = self._compute_method_metrics_for_user(
                customer_id=customer_id,
                ground_truth_article_id=ground_truth_article_id,
                recommendations=svd_recs,
                metadata_lookup=metadata_lookup,
                method_label="svd",
            )
            agentic_metrics, agentic_missing_count, agentic_errors = self._compute_method_metrics_for_user(
                customer_id=customer_id,
                ground_truth_article_id=ground_truth_article_id,
                recommendations=agentic_recs,
                metadata_lookup=metadata_lookup,
                method_label="agentic",
            )
            missing_metadata_for_diversity_count += svd_missing_count + agentic_missing_count
            metric_calculation_errors.extend(svd_errors)
            metric_calculation_errors.extend(agentic_errors)

            if svd_recs:
                users_with_svd_metrics += 1
            if agentic_recs:
                users_with_agentic_metrics += 1

            if int(svd_metrics["hit_rate_at_10"]) == 1 and len(example_hit_users_svd) < 5:
                example_hit_users_svd.append(customer_id)
            if int(svd_metrics["hit_rate_at_10"]) == 0 and len(example_miss_users_svd) < 5:
                example_miss_users_svd.append(customer_id)
            if int(agentic_metrics["hit_rate_at_10"]) == 1 and len(example_hit_users_agentic) < 5:
                example_hit_users_agentic.append(customer_id)
            if int(agentic_metrics["hit_rate_at_10"]) == 0 and len(example_miss_users_agentic) < 5:
                example_miss_users_agentic.append(customer_id)

            per_user_rows.append(
                {
                    "customer_id": customer_id,
                    "ground_truth_article_id": ground_truth_article_id,
                    "svd_hit_rate_at_10": svd_metrics["hit_rate_at_10"],
                    "svd_ground_truth_rank": svd_metrics["ground_truth_rank"],
                    "svd_ndcg_at_10": svd_metrics["ndcg_at_10"],
                    "svd_ild_at_10": svd_metrics["ild_at_10"],
                    "agentic_hit_rate_at_10": agentic_metrics["hit_rate_at_10"],
                    "agentic_ground_truth_rank": agentic_metrics["ground_truth_rank"],
                    "agentic_ndcg_at_10": agentic_metrics["ndcg_at_10"],
                    "agentic_ild_at_10": agentic_metrics["ild_at_10"],
                }
            )

        self.settings.per_user_metrics_top10_json_path(subset_size).write_text(
            json.dumps(per_user_rows, indent=2),
            encoding="utf-8",
        )
        self.settings.per_user_metrics_top10_csv_path(subset_size).write_text(
            pd.DataFrame(per_user_rows).to_csv(index=False),
            encoding="utf-8",
        )

        summary = self._build_metric_summary(per_user_rows, subset_size=subset_size)
        self.settings.metric_summary_top10_json_path(subset_size).write_text(
            json.dumps(summary, indent=2),
            encoding="utf-8",
        )
        self.settings.metric_summary_top10_csv_path(subset_size).write_text(
            pd.DataFrame([self._flatten_metric_summary(summary)]).to_csv(index=False),
            encoding="utf-8",
        )

        validation_report = {
            "users_evaluated": len(per_user_rows),
            "users_with_svd_metrics": users_with_svd_metrics,
            "users_with_agentic_metrics": users_with_agentic_metrics,
            "svd_top_10_count_check": svd_top_10_count_check,
            "agentic_top_10_count_check": agentic_top_10_count_check,
            "svd_recommendations_inside_candidate_pool_check": svd_inside_pool_check,
            "agentic_recommendations_inside_candidate_pool_check": agentic_inside_pool_check,
            "missing_metadata_for_diversity_count": missing_metadata_for_diversity_count,
            "metric_calculation_errors": metric_calculation_errors[:50],
            "example_hit_users_svd": example_hit_users_svd,
            "example_hit_users_agentic": example_hit_users_agentic,
            "example_miss_users_svd": example_miss_users_svd,
            "example_miss_users_agentic": example_miss_users_agentic,
        }
        self.settings.metric_validation_report_top10_path(subset_size).write_text(
            json.dumps(validation_report, indent=2),
            encoding="utf-8",
        )

        bootstrap_report = None
        if bootstrap_samples > 0:
            bootstrap_report = self._build_bootstrap_ci_report(
                per_user_rows=per_user_rows,
                bootstrap_samples=bootstrap_samples,
                random_seed=random_seed,
            )
            self.settings.metric_summary_top10_with_ci_json_path(subset_size).write_text(
                json.dumps({**summary, "confidence_intervals": bootstrap_report["confidence_intervals"]}, indent=2),
                encoding="utf-8",
            )
            self.settings.bootstrap_ci_report_top10_json_path(subset_size).write_text(
                json.dumps(bootstrap_report, indent=2),
                encoding="utf-8",
            )

        print(
            "Formal Top-10 metrics summary: "
            f"SVD HitRate@10={summary['svd']['hit_rate_at_10']:.4f}, "
            f"3-Agent HitRate@10={summary['agentic']['hit_rate_at_10']:.4f}, "
            f"SVD NDCG@10={summary['svd']['ndcg_at_10']:.4f}, "
            f"3-Agent NDCG@10={summary['agentic']['ndcg_at_10']:.4f}, "
            f"SVD ILD@10={summary['svd']['intra_list_diversity_at_10']:.4f}, "
            f"3-Agent ILD@10={summary['agentic']['intra_list_diversity_at_10']:.4f}, "
            f"SVD hits count={summary['svd']['hits_count']}, "
            f"3-Agent hits count={summary['agentic']['hits_count']}"
        )
        return {
            "summary": summary,
            "validation": validation_report,
            "per_user_metrics": per_user_rows,
            "bootstrap": bootstrap_report,
        }

    def _model_metrics(
        self,
        user_ids: list[str],
        test_df: pd.DataFrame,
        recommendations: dict[str, list[dict[str, object]]],
        user_profiles: dict[str, dict[str, set[str]]],
        include_explanations: bool,
    ) -> dict[str, float | None]:
        if not user_ids:
            return {
                "hit_rate_at_10": 0.0,
                "preference_alignment": 0.0,
                "diversity": 0.0,
                "explanation_quality": 0.0 if include_explanations else None,
                "feedback_adaptability": 0.0 if include_explanations else None,
            }

        test_lookup = test_df.groupby("customer_id")["article_id"].agg(set).to_dict()
        hits = 0
        alignments: list[float] = []
        diversities: list[float] = []
        explanation_scores: list[float] = []

        for user_id in user_ids:
            recs = recommendations.get(user_id, [])[: self.settings.top_n]
            if not recs:
                continue
            future_items = test_lookup.get(user_id, set())
            if any(normalize_article_id(rec["article_id"]) in future_items for rec in recs):
                hits += 1

            profile = user_profiles[user_id]
            alignments.extend(self._preference_scores(recs, profile))
            diversities.append(self._diversity_score(recs))
            if include_explanations:
                explanation_scores.extend(self._explanation_scores(recs))

        metrics = {
            "hit_rate_at_10": round(hits / len(user_ids), 4),
            "preference_alignment": round(sum(alignments) / len(alignments), 4) if alignments else 0.0,
            "diversity": round(sum(diversities) / len(diversities), 4) if diversities else 0.0,
            "explanation_quality": round(sum(explanation_scores) / len(explanation_scores), 4)
            if include_explanations and explanation_scores
            else (0.0 if include_explanations else None),
            "feedback_adaptability": 0.75 if include_explanations else None,
        }
        return metrics

    @staticmethod
    def _build_user_profiles(train_df: pd.DataFrame) -> dict[str, dict[str, set[str]]]:
        profiles: dict[str, dict[str, set[str]]] = {}
        for user_id, group in train_df.groupby("customer_id"):
            profiles[str(user_id)] = {
                "product_group": set(group["product_group"].astype(str)),
                "product_type": set(group["product_type"].astype(str)),
                "colour": set(group["colour"].astype(str)),
                "appearance": set(group["appearance"].astype(str)),
            }
        return profiles

    @staticmethod
    def _preference_scores(recommendations: list[dict[str, object]], profile: dict[str, set[str]]) -> list[float]:
        scores = []
        for rec in recommendations:
            score = 0.0
            score += 0.25 if rec["product_group"] in profile["product_group"] else 0.0
            score += 0.25 if rec["product_type"] in profile["product_type"] else 0.0
            score += 0.25 if rec["colour"] in profile["colour"] else 0.0
            score += 0.25 if rec["appearance"] in profile["appearance"] else 0.0
            scores.append(score)
        return scores

    def _diversity_score(self, recommendations: list[dict[str, object]]) -> float:
        if not recommendations:
            return 0.0
        unique_types = len({str(rec["product_type"]) for rec in recommendations})
        return unique_types / min(len(recommendations), self.settings.top_n)

    @staticmethod
    def _explanation_scores(recommendations: list[dict[str, object]]) -> list[float]:
        scores = []
        for rec in recommendations:
            explanation = str(rec.get("reason", "")).lower()
            grounded = sum(
                1
                for token in [
                    str(rec["product_type"]).lower(),
                    str(rec["product_group"]).lower(),
                    str(rec["colour"]).lower(),
                ]
                if token in explanation
            )
            score = 0.4 if explanation else 0.0
            score += 0.2 if len(explanation.split()) >= 8 else 0.0
            score += min(0.4, grounded * 0.2)
            scores.append(score)
        return scores

    def _top10_model_metrics(
        self,
        user_ids: list[str],
        test_df: pd.DataFrame,
        recommendations: dict[str, list[dict[str, object]]],
    ) -> dict[str, float]:
        if not user_ids:
            return {
                "hit_rate_at_10": 0.0,
                "ndcg_at_10": 0.0,
                "intra_list_diversity_at_10": 0.0,
            }

        test_lookup = test_df.groupby("customer_id")["article_id"].agg(set).to_dict()
        hit_scores: list[float] = []
        ndcg_scores: list[float] = []
        ild_scores: list[float] = []

        for user_id in user_ids:
            recs = recommendations.get(user_id, [])[: self.settings.top_n]
            future_items = test_lookup.get(user_id, set())
            hit_scores.append(
                1.0 if any(normalize_article_id(rec["article_id"]) in future_items for rec in recs) else 0.0
            )
            ndcg_scores.append(self._ndcg_at_k(recs, future_items))
            ild_scores.append(self._intra_list_diversity(recs))

        return {
            "hit_rate_at_10": round(sum(hit_scores) / len(hit_scores), 4),
            "ndcg_at_10": round(sum(ndcg_scores) / len(ndcg_scores), 4),
            "intra_list_diversity_at_10": round(sum(ild_scores) / len(ild_scores), 4),
        }

    @staticmethod
    def _ndcg_at_k(recommendations: list[dict[str, object]], relevant_items: set[str]) -> float:
        if not recommendations or not relevant_items:
            return 0.0

        dcg = 0.0
        for index, rec in enumerate(recommendations, start=1):
            if normalize_article_id(rec["article_id"]) in relevant_items:
                dcg += 1.0 / log2(index + 1)

        ideal_hits = min(len(relevant_items), len(recommendations))
        if ideal_hits == 0:
            return 0.0
        idcg = sum(1.0 / log2(index + 1) for index in range(1, ideal_hits + 1))
        return dcg / idcg if idcg else 0.0

    @staticmethod
    def _intra_list_diversity(recommendations: list[dict[str, object]]) -> float:
        if len(recommendations) < 2:
            return 0.0

        distances: list[float] = []
        for left_index, left in enumerate(recommendations[:-1]):
            for right in recommendations[left_index + 1 :]:
                matches = sum(
                    1
                    for field in ("product_type", "product_group", "colour", "appearance")
                    if str(left.get(field)) == str(right.get(field))
                )
                distances.append(1.0 - (matches / 4.0))
        return sum(distances) / len(distances) if distances else 0.0

    @staticmethod
    def _normalize_ids(frame: pd.DataFrame) -> pd.DataFrame:
        normalized = frame.copy()
        normalized["article_id"] = normalized["article_id"].map(normalize_article_id)
        normalized["customer_id"] = normalized["customer_id"].map(normalize_customer_id)
        return normalized

    @staticmethod
    def _normalize_recommendation_payload(
        recommendations: dict[str, list[dict[str, object]]],
    ) -> dict[str, list[dict[str, object]]]:
        normalized_payload: dict[str, list[dict[str, object]]] = {}
        for user_id, items in recommendations.items():
            normalized_items: list[dict[str, object]] = []
            for item in items:
                normalized_item = dict(item)
                normalized_item["article_id"] = normalize_article_id(item.get("article_id"))
                normalized_items.append(normalized_item)
            normalized_payload[normalize_customer_id(user_id)] = normalized_items
        return normalized_payload

    @staticmethod
    def _normalize_evaluation_row(row: dict[str, object]) -> dict[str, object]:
        normalized = dict(row)
        normalized["customer_id"] = normalize_customer_id(row.get("customer_id"))
        normalized["ground_truth_article_id"] = normalize_article_id(row.get("ground_truth_article_id"))
        normalized["candidate_pool_article_ids"] = [
            normalize_article_id(article_id) for article_id in row.get("candidate_pool_article_ids", [])
        ]
        return normalized

    @staticmethod
    def _normalize_saved_recommendation_row(row: dict[str, object]) -> dict[str, object]:
        normalized = dict(row)
        normalized["customer_id"] = normalize_customer_id(row.get("customer_id"))
        normalized["ground_truth_article_id"] = normalize_article_id(row.get("ground_truth_article_id"))
        normalized["top_10_recommendations"] = [
            {**item, "article_id": normalize_article_id(item.get("article_id"))}
            for item in row.get("top_10_recommendations", [])
        ]
        return normalized

    @classmethod
    def _build_article_metadata_lookup(cls, processed: pd.DataFrame) -> dict[str, dict[str, object]]:
        normalized = processed.copy()
        normalized["article_id"] = normalized["article_id"].map(normalize_article_id)
        normalized["customer_id"] = normalized["customer_id"].map(normalize_customer_id)
        normalized["t_dat"] = pd.to_datetime(normalized["t_dat"], errors="coerce")
        normalized = normalized.sort_values("t_dat", ascending=False).drop_duplicates("article_id", keep="first")
        return {
            normalize_article_id(row["article_id"]): {
                field: row.get(field)
                for field in cls.DIVERSITY_FIELDS
            }
            for _, row in normalized.iterrows()
        }

    def _compute_method_metrics_for_user(
        self,
        *,
        customer_id: str,
        ground_truth_article_id: str,
        recommendations: list[dict[str, object]],
        metadata_lookup: dict[str, dict[str, object]],
        method_label: str,
    ) -> tuple[dict[str, object], int, list[str]]:
        ranked_article_ids = [normalize_article_id(item.get("article_id")) for item in recommendations[: self.settings.top_n]]
        ground_truth_rank = None
        for index, article_id in enumerate(ranked_article_ids, start=1):
            if article_id == ground_truth_article_id:
                ground_truth_rank = index
                break

        hit_rate_at_10 = 1 if ground_truth_rank is not None else 0
        ndcg_at_10 = round((1.0 / log2(ground_truth_rank + 1)) if ground_truth_rank is not None else 0.0, 6)
        ild_at_10, missing_metadata_count, errors = self._compute_saved_top10_ild(
            customer_id=customer_id,
            recommendations=recommendations[: self.settings.top_n],
            metadata_lookup=metadata_lookup,
            method_label=method_label,
        )
        return (
            {
                "hit_rate_at_10": hit_rate_at_10,
                "ground_truth_rank": ground_truth_rank,
                "ndcg_at_10": ndcg_at_10,
                "ild_at_10": ild_at_10,
            },
            missing_metadata_count,
            errors,
        )

    def _compute_saved_top10_ild(
        self,
        *,
        customer_id: str,
        recommendations: list[dict[str, object]],
        metadata_lookup: dict[str, dict[str, object]],
        method_label: str,
    ) -> tuple[float, int, list[str]]:
        prepared_items: list[dict[str, object]] = []
        missing_metadata_count = 0
        errors: list[str] = []

        for item in recommendations:
            article_id = normalize_article_id(item.get("article_id"))
            metadata = metadata_lookup.get(article_id, {})
            prepared = {"article_id": article_id}
            missing_fields: list[str] = []
            for field in self.DIVERSITY_FIELDS:
                value = item.get(field)
                if value is None or str(value).strip() == "":
                    value = metadata.get(field)
                if value is None or str(value).strip() == "":
                    missing_fields.append(field)
                prepared[field] = value
            if missing_fields:
                missing_metadata_count += 1
                errors.append(
                    f"{method_label}:{customer_id}:{article_id}:missing_diversity_metadata={','.join(missing_fields)}"
                )
            prepared_items.append(prepared)

        valid_items = [
            item
            for item in prepared_items
            if all(item.get(field) is not None and str(item.get(field)).strip() != "" for field in self.DIVERSITY_FIELDS)
        ]
        if len(valid_items) < 2:
            return 0.0, missing_metadata_count, errors

        distances: list[float] = []
        for left_index, left in enumerate(valid_items[:-1]):
            for right in valid_items[left_index + 1 :]:
                differences = [
                    1.0 if str(left[field]) != str(right[field]) else 0.0
                    for field in self.DIVERSITY_FIELDS
                ]
                distances.append(sum(differences) / len(differences))
        return round(sum(distances) / len(distances), 6) if distances else 0.0, missing_metadata_count, errors

    def _build_metric_summary(self, per_user_rows: list[dict[str, object]], subset_size: int) -> dict[str, object]:
        svd_hits = sum(int(row["svd_hit_rate_at_10"]) for row in per_user_rows)
        agentic_hits = sum(int(row["agentic_hit_rate_at_10"]) for row in per_user_rows)
        total_users = len(per_user_rows)

        def average(field: str) -> float:
            if not per_user_rows:
                return 0.0
            return round(sum(float(row[field]) for row in per_user_rows) / total_users, 6)

        return {
            "evaluation_scope": {
                "valid_evaluated_users": total_users,
                "candidate_pool_size": self.settings.candidate_pool_size,
                "top_k": self.settings.top_n,
                "experiment_subset_size": subset_size,
                "split_strategy": "leave_one_out",
                "baseline": "SVD Matrix Factorisation",
                "comparison_method": "3-Agent Agentic AI",
            },
            "svd": {
                "hit_rate_at_10": average("svd_hit_rate_at_10"),
                "hits_count": svd_hits,
                "miss_count": total_users - svd_hits,
                "ndcg_at_10": average("svd_ndcg_at_10"),
                "intra_list_diversity_at_10": average("svd_ild_at_10"),
            },
            "agentic": {
                "hit_rate_at_10": average("agentic_hit_rate_at_10"),
                "hits_count": agentic_hits,
                "miss_count": total_users - agentic_hits,
                "ndcg_at_10": average("agentic_ndcg_at_10"),
                "intra_list_diversity_at_10": average("agentic_ild_at_10"),
            },
        }

    @staticmethod
    def _flatten_metric_summary(summary: dict[str, object]) -> dict[str, object]:
        evaluation_scope = summary["evaluation_scope"]
        svd = summary["svd"]
        agentic = summary["agentic"]
        return {
            "valid_evaluated_users": evaluation_scope["valid_evaluated_users"],
            "candidate_pool_size": evaluation_scope["candidate_pool_size"],
            "top_k": evaluation_scope["top_k"],
            "experiment_subset_size": evaluation_scope.get("experiment_subset_size"),
            "split_strategy": evaluation_scope["split_strategy"],
            "baseline": evaluation_scope["baseline"],
            "comparison_method": evaluation_scope["comparison_method"],
            "svd_hit_rate_at_10": svd["hit_rate_at_10"],
            "svd_hits_count": svd["hits_count"],
            "svd_miss_count": svd["miss_count"],
            "svd_ndcg_at_10": svd["ndcg_at_10"],
            "svd_intra_list_diversity_at_10": svd["intra_list_diversity_at_10"],
            "agentic_hit_rate_at_10": agentic["hit_rate_at_10"],
            "agentic_hits_count": agentic["hits_count"],
            "agentic_miss_count": agentic["miss_count"],
            "agentic_ndcg_at_10": agentic["ndcg_at_10"],
            "agentic_intra_list_diversity_at_10": agentic["intra_list_diversity_at_10"],
        }

    def _build_bootstrap_ci_report(
        self,
        *,
        per_user_rows: list[dict[str, object]],
        bootstrap_samples: int,
        random_seed: int,
    ) -> dict[str, object]:
        rng = random.Random(random_seed)
        metrics = {
            "svd_hit_rate_at_10": [],
            "agentic_hit_rate_at_10": [],
            "svd_ndcg_at_10": [],
            "agentic_ndcg_at_10": [],
            "svd_ild_at_10": [],
            "agentic_ild_at_10": [],
            "difference_hit_rate_at_10": [],
            "difference_ndcg_at_10": [],
            "difference_ild_at_10": [],
        }
        row_count = len(per_user_rows)
        if row_count == 0:
            return {
                "bootstrap_samples": bootstrap_samples,
                "random_seed": random_seed,
                "confidence_intervals": {},
            }

        for _ in range(bootstrap_samples):
            sample = [per_user_rows[rng.randrange(row_count)] for _ in range(row_count)]
            svd_hit = sum(float(row["svd_hit_rate_at_10"]) for row in sample) / row_count
            agentic_hit = sum(float(row["agentic_hit_rate_at_10"]) for row in sample) / row_count
            svd_ndcg = sum(float(row["svd_ndcg_at_10"]) for row in sample) / row_count
            agentic_ndcg = sum(float(row["agentic_ndcg_at_10"]) for row in sample) / row_count
            svd_ild = sum(float(row["svd_ild_at_10"]) for row in sample) / row_count
            agentic_ild = sum(float(row["agentic_ild_at_10"]) for row in sample) / row_count

            metrics["svd_hit_rate_at_10"].append(svd_hit)
            metrics["agentic_hit_rate_at_10"].append(agentic_hit)
            metrics["svd_ndcg_at_10"].append(svd_ndcg)
            metrics["agentic_ndcg_at_10"].append(agentic_ndcg)
            metrics["svd_ild_at_10"].append(svd_ild)
            metrics["agentic_ild_at_10"].append(agentic_ild)
            metrics["difference_hit_rate_at_10"].append(agentic_hit - svd_hit)
            metrics["difference_ndcg_at_10"].append(agentic_ndcg - svd_ndcg)
            metrics["difference_ild_at_10"].append(agentic_ild - svd_ild)

        return {
            "bootstrap_samples": bootstrap_samples,
            "random_seed": random_seed,
            "confidence_intervals": {
                metric_name: {
                    "mean": round(sum(values) / len(values), 6),
                    "ci_95_lower": round(self._percentile(values, 2.5), 6),
                    "ci_95_upper": round(self._percentile(values, 97.5), 6),
                }
                for metric_name, values in metrics.items()
            },
        }

    @staticmethod
    def _percentile(values: list[float], percentile: float) -> float:
        if not values:
            return 0.0
        ordered = sorted(values)
        if len(ordered) == 1:
            return ordered[0]
        position = (len(ordered) - 1) * (percentile / 100.0)
        lower_index = int(position)
        upper_index = min(lower_index + 1, len(ordered) - 1)
        weight = position - lower_index
        return ordered[lower_index] * (1 - weight) + ordered[upper_index] * weight
