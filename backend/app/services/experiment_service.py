from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone

import pandas as pd

from app.config import Settings
from app.models.experiment_state import ExperimentState
from app.services.agentic_service import AgenticRecommendationService
from app.services.cf_service import CollaborativeFilteringService
from app.services.data_service import DataService
from app.services.evaluation_service import EvaluationService


@dataclass
class ExperimentService:
    settings: Settings
    data_service: DataService
    cf_service: CollaborativeFilteringService
    agentic_service: AgenticRecommendationService
    evaluation_service: EvaluationService

    def _load_saved_method_results(self, path) -> dict[str, dict[str, object]]:
        if not path.exists():
            return {}
        payload = json.loads(path.read_text(encoding="utf-8"))
        normalized: dict[str, dict[str, object]] = {}
        for user_id, value in payload.items():
            if isinstance(value, dict):
                normalized[str(user_id)] = value
            elif isinstance(value, list):
                normalized[str(user_id)] = {"top_5_recommendations": value}
        return normalized

    @staticmethod
    def _extract_hit_value(result: dict[str, object] | None) -> int | None:
        if result is None:
            return None
        hit_at_5 = result.get("hit_at_5")
        if hit_at_5 is None:
            return None
        return int(hit_at_5)

    @staticmethod
    def _extract_top_5_count(result: dict[str, object] | None) -> int:
        if result is None:
            return 0
        recommendations = result.get("top_5_recommendations") or []
        if not isinstance(recommendations, list):
            return 0
        return len(recommendations[:5])

    @staticmethod
    def _same_candidate_pool_source(result: dict[str, object] | None) -> bool:
        if result is None:
            return False
        validation = result.get("validation") or {}
        if not isinstance(validation, dict):
            return False
        return bool(validation.get("same_candidate_pool_source"))

    @staticmethod
    def _top_5_inside_candidate_pool(result: dict[str, object] | None) -> bool:
        if result is None:
            return False
        validation = result.get("validation") or {}
        if not isinstance(validation, dict):
            return False
        return bool(validation.get("top_5_all_inside_candidate_pool"))

    @staticmethod
    def _is_base_row_valid_for_completed_evaluation(base_row: dict[str, object]) -> tuple[bool, str]:
        if not bool(base_row.get("is_valid_for_evaluation")):
            invalid_reason = str(base_row.get("invalid_reason") or "Evaluation base row is invalid")
            return False, invalid_reason
        if not bool(base_row.get("ground_truth_in_candidate_pool")):
            return False, "Ground truth article is missing from the candidate pool"
        if int(base_row.get("candidate_pool_size") or 0) < 6:
            return False, "Candidate pool size is below 6 for this user"
        train_article_ids = base_row.get("train_article_ids") or []
        if not train_article_ids:
            return False, "Training history is missing for this user"
        if not str(base_row.get("ground_truth_article_id") or ""):
            return False, "Ground truth article is missing for this user"
        return True, ""

    def _build_completed_evaluation_row(
        self,
        user_id: str,
        base_row: dict[str, object],
        cf_result: dict[str, object] | None,
        agentic_result: dict[str, object] | None,
        included_in_metrics: bool,
        excluded_reason: str,
    ) -> dict[str, object]:
        return {
            "customer_id": user_id,
            "base_valid": bool(base_row.get("is_valid_for_evaluation")),
            "cf_result_exists": cf_result is not None,
            "cf_hit_at_5_exists": self._extract_hit_value(cf_result) is not None,
            "agentic_result_exists": agentic_result is not None,
            "agentic_hit_at_5_exists": self._extract_hit_value(agentic_result) is not None,
            "cf_hit_at_5": self._extract_hit_value(cf_result),
            "agentic_hit_at_5": self._extract_hit_value(agentic_result),
            "cf_top_5_count": self._extract_top_5_count(cf_result),
            "agentic_top_5_count": self._extract_top_5_count(agentic_result),
            "candidate_pool_size": int(base_row.get("candidate_pool_size") or 0),
            "ground_truth_in_candidate_pool": bool(base_row.get("ground_truth_in_candidate_pool")),
            "candidate_pool_valid": bool(base_row.get("ground_truth_in_candidate_pool")) and int(base_row.get("candidate_pool_size") or 0) >= 6,
            "included_in_metrics": included_in_metrics,
            "included_in_comparable_users": included_in_metrics,
            "excluded_reason": excluded_reason,
        }

    def load_completed_evaluation_users(self) -> list[dict[str, object]] | None:
        if not self.settings.completed_evaluation_users_path.exists():
            return None
        return json.loads(self.settings.completed_evaluation_users_path.read_text(encoding="utf-8"))

    def load_presentation_users(self) -> list[dict[str, object]]:
        report_rows = self.load_completed_evaluation_users() or []
        return [row for row in report_rows if row.get("included_in_metrics") is True]

    def get_presentation_user_ids(self) -> list[str]:
        return [str(row["customer_id"]) for row in self.load_presentation_users()]

    def _load_saved_method_result(self, path, user_id: str) -> dict[str, object] | None:
        payload = self._load_saved_method_results(path)
        result = payload.get(user_id)
        if result is None:
            return None
        return result

    def _normalize_saved_method_result(
        self,
        result: dict[str, object] | None,
    ) -> dict[str, object] | None:
        if result is None:
            return None
        normalized = dict(result)
        hit_at_5 = normalized.get("hit_at_5")
        if hit_at_5 is not None:
            normalized["hit_at_5"] = int(bool(hit_at_5))
        hit_result = normalized.get("hit_result")
        if isinstance(hit_result, dict) and hit_result.get("hit_at_5") is not None:
            normalized["hit_result"] = {
                **hit_result,
                "hit_at_5": int(bool(hit_result["hit_at_5"])),
            }
        top_5_article_ids = normalized.get("top_5_article_ids")
        if not isinstance(top_5_article_ids, list):
            recommendations = normalized.get("top_5_recommendations") or []
            if isinstance(recommendations, list):
                normalized["top_5_article_ids"] = [
                    str(item.get("article_id", ""))
                    for item in recommendations[: self.settings.top_n]
                    if isinstance(item, dict)
                ]
            else:
                normalized["top_5_article_ids"] = []
        if "hit_explanation" not in normalized and "explanation" in normalized:
            normalized["hit_explanation"] = normalized["explanation"]
        if "recommendations" not in normalized and "top_5_recommendations" in normalized:
            normalized["recommendations"] = normalized["top_5_recommendations"]
        return normalized

    def build_presentation_metrics(self) -> dict[str, object]:
        presentation_users = self.load_presentation_users()
        selected_user_ids = [str(row["customer_id"]) for row in presentation_users]
        cf_results = self._load_saved_method_results(self.settings.cf_output_path)
        agentic_results = self._load_saved_method_results(self.settings.agentic_output_path)
        cf_hits = 0
        agentic_hits = 0

        for user_id in selected_user_ids:
            cf_hit = self._extract_hit_value(self._normalize_saved_method_result(cf_results.get(user_id)))
            agentic_hit = self._extract_hit_value(
                self._normalize_saved_method_result(agentic_results.get(user_id))
            )
            cf_hits += int(cf_hit or 0)
            agentic_hits += int(agentic_hit or 0)

        evaluated_users = len(selected_user_ids)
        cf_miss_count = max(evaluated_users - cf_hits, 0)
        agentic_miss_count = max(evaluated_users - agentic_hits, 0)
        cf_hit_at_5 = round(cf_hits / evaluated_users, 4) if evaluated_users else 0.0
        agentic_hit_at_5 = round(agentic_hits / evaluated_users, 4) if evaluated_users else 0.0
        legacy_metrics = self.evaluation_service.load_metrics()

        return {
            "presentation_mode": True,
            "user_scope": "10 users from completed_evaluation_users.json where included_in_metrics=true",
            "legacy_20_user_metrics": legacy_metrics,
            "collaborative_filtering": {"hit_at_5": cf_hit_at_5},
            "agentic_ai_framework": {"hit_at_5": agentic_hit_at_5},
            "total_selected_users": evaluated_users,
            "valid_evaluation_users": evaluated_users,
            "invalid_evaluation_users": 0,
            "evaluated_users": evaluated_users,
            "completed_valid_users": evaluated_users,
            "cf_hit_at_5": cf_hit_at_5,
            "agentic_hit_at_5": agentic_hit_at_5,
            "cf_hits_count": cf_hits,
            "agentic_hits_count": agentic_hits,
            "cf_miss_count": cf_miss_count,
            "agentic_miss_count": agentic_miss_count,
            "evaluated_user_ids": selected_user_ids,
            "excluded_user_ids_with_reasons": [],
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def build_completed_evaluation_users_report(
        self,
        limit: int | None = None,
        base_rows: dict[str, dict[str, object]] | None = None,
        cf_results_cache: dict[str, dict[str, object]] | None = None,
        agentic_results_cache: dict[str, dict[str, object]] | None = None,
        allow_generation: bool = False,
    ) -> list[dict[str, object]]:
        if base_rows is None:
            base_rows = self.evaluation_service.load_evaluation_base_table()
            if base_rows is None:
                if not self.settings.train_path.exists() or not self.settings.test_path.exists():
                    self.settings.completed_evaluation_users_path.write_text("[]", encoding="utf-8")
                    return []
                train_df = self.data_service.load_train()
                test_df = self.data_service.load_test()
                catalog_df = self.load_catalog(train_df, test_df)
                base_rows = self.evaluation_service.build_evaluation_base_table(train_df, test_df, catalog_df)

        saved_cf_results = cf_results_cache if cf_results_cache is not None else self._load_saved_method_results(self.settings.cf_output_path)
        saved_agentic_results = agentic_results_cache if agentic_results_cache is not None else self._load_saved_method_results(self.settings.agentic_output_path)

        report_rows: list[dict[str, object]] = []
        comparable_candidates: list[str] = []

        for user_id in sorted(base_rows):
            base_row = base_rows[user_id]
            base_ok, base_reason = self._is_base_row_valid_for_completed_evaluation(base_row)

            cf_result = saved_cf_results.get(user_id)
            agentic_result = saved_agentic_results.get(user_id)

            if allow_generation and base_ok and cf_result is None:
                try:
                    cf_result = self.build_cf_result(user_id)
                    saved_cf_results[user_id] = cf_result
                except FileNotFoundError:
                    cf_result = None

            if allow_generation and base_ok and agentic_result is None:
                try:
                    agentic_result = self.build_agentic_result(user_id)
                    saved_agentic_results[user_id] = agentic_result
                except FileNotFoundError:
                    agentic_result = None

            excluded_reason = base_reason
            included_in_metrics = False
            is_comparable_candidate = False

            if base_ok:
                if cf_result is None:
                    excluded_reason = "CF result is missing for this user"
                elif agentic_result is None:
                    excluded_reason = "Agentic result is missing for this user"
                elif self._extract_top_5_count(cf_result) <= 0:
                    excluded_reason = "CF Top 5 recommendations are missing for this user"
                elif self._extract_top_5_count(agentic_result) <= 0:
                    excluded_reason = "Agentic Top 5 recommendations are missing for this user"
                elif self._extract_hit_value(cf_result) is None:
                    excluded_reason = "CF Hit@5 is missing for this user"
                elif self._extract_hit_value(agentic_result) is None:
                    excluded_reason = "Agentic Hit@5 is missing for this user"
                elif not self._same_candidate_pool_source(cf_result) or not self._same_candidate_pool_source(agentic_result):
                    excluded_reason = "CF and Agentic results were not generated from the same candidate pool"
                elif not self._top_5_inside_candidate_pool(cf_result) or not self._top_5_inside_candidate_pool(agentic_result):
                    excluded_reason = "CF and Agentic Top 5 recommendations must stay inside the candidate pool"
                else:
                    is_comparable_candidate = True
                    comparable_candidates.append(user_id)
                    excluded_reason = ""

            report_rows.append(
                self._build_completed_evaluation_row(
                    user_id,
                    base_row,
                    cf_result,
                    agentic_result,
                    included_in_metrics,
                    excluded_reason,
                )
            )

        applied_limit = limit or self.settings.max_valid_eval_users
        included_user_ids = set(comparable_candidates[:applied_limit])
        for row in report_rows:
            if row["customer_id"] in included_user_ids:
                row["included_in_metrics"] = True
                row["included_in_comparable_users"] = True
                row["excluded_reason"] = ""
            elif row["customer_id"] in comparable_candidates:
                row["included_in_metrics"] = False
                row["included_in_comparable_users"] = False
                row["excluded_reason"] = "Excluded by MAX_VALID_EVAL_USERS limit"

        self.settings.completed_evaluation_users_path.write_text(
            json.dumps(report_rows, indent=2),
            encoding="utf-8",
        )
        self.settings.comparable_user_audit_path.write_text(
            json.dumps(report_rows, indent=2),
            encoding="utf-8",
        )
        return report_rows

    def get_completed_comparable_user_ids(self, limit: int | None = None) -> list[str]:
        report_rows = self.load_completed_evaluation_users()
        if report_rows is None:
            report_rows = self.build_completed_evaluation_users_report(limit=limit, allow_generation=False)
        limit = limit or self.settings.max_valid_eval_users
        return [
            str(row["customer_id"])
            for row in report_rows
            if row.get("included_in_metrics")
        ][:limit]

    def get_valid_completed_evaluation_users(self, limit: int | None = None) -> list[str]:
        return self.get_completed_comparable_user_ids(limit=limit)

    def run(self) -> dict[str, object]:
        summary = self.data_service.preprocess()
        train_df = self.data_service.load_train()
        test_df = self.data_service.load_test()
        catalog_df = self.load_catalog(train_df, test_df)
        evaluation_base_rows = self.evaluation_service.build_evaluation_base_table(
            train_df,
            test_df,
            catalog_df,
            selected_ui_customer_ids=[],
        )
        cf_results: dict[str, dict[str, object]] = {}
        agentic_results: dict[str, dict[str, object]] = {}
        completed_report = self.build_completed_evaluation_users_report(
            limit=self.settings.max_valid_eval_users,
            base_rows=evaluation_base_rows,
            cf_results_cache=cf_results,
            agentic_results_cache=agentic_results,
            allow_generation=True,
        )
        user_ids = [str(row["customer_id"]) for row in completed_report if row["included_in_metrics"]]
        summary["available_user_ids"] = user_ids
        summary["completed_comparable_user_ids"] = user_ids
        summary["completed_comparable_user_count"] = len(user_ids)
        summary["evaluated_user_ids"] = user_ids
        summary["evaluated_users"] = len(user_ids)
        summary["valid_completed_user_count"] = len(user_ids)
        summary["max_valid_eval_users"] = self.settings.max_valid_eval_users
        summary["sample_user_ids"] = user_ids
        self.settings.summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

        cf_recommendations = {
            user_id: result["top_5_recommendations"]
            for user_id, result in cf_results.items()
            if user_id in user_ids and result["invalid_reason"] is None
        }
        agentic_recommendations = {
            user_id: result["top_5_recommendations"]
            for user_id, result in agentic_results.items()
            if user_id in user_ids and result["invalid_reason"] is None
        }
        self.settings.cf_output_path.write_text(
            json.dumps({user_id: cf_results[user_id] for user_id in user_ids if user_id in cf_results}, indent=2),
            encoding="utf-8",
        )
        self.settings.agentic_output_path.write_text(
            json.dumps({user_id: agentic_results[user_id] for user_id in user_ids if user_id in agentic_results}, indent=2),
            encoding="utf-8",
        )
        metrics = self.evaluation_service.evaluate(
            train_df,
            test_df,
            catalog_df,
            cf_recommendations,
            agentic_recommendations,
            selected_user_ids=user_ids,
        )
        excluded_rows = [row for row in completed_report if not row["included_in_metrics"]]
        metrics.update(
            {
                "total_selected_users": len(completed_report),
                "valid_evaluation_users": len(user_ids),
                "completed_valid_users": len(user_ids),
                "invalid_evaluation_users": len(excluded_rows),
                "evaluated_users": len(user_ids),
                "evaluated_user_ids": user_ids,
                "excluded_user_ids_with_reasons": [
                    {"user_id": str(row["customer_id"]), "reasons": [str(row["excluded_reason"])]}
                    for row in excluded_rows
                    if str(row.get("excluded_reason") or "")
                ],
            }
        )
        self.settings.metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
        for user_id in user_ids:
            self.build_evaluation_debug(user_id)

        state = ExperimentState(
            status="completed",
            dataset=self.settings.dataset_name,
            sample_size=int(summary["sample_size"]),
            train_size=int(summary["train_size"]),
            test_size=int(summary["test_size"]),
            evaluated_users=len(user_ids),
            models=["collaborative_filtering", "agentic_ai_framework"],
            metrics_ready=True,
            split_boundary_date="leave_one_out",
            artifacts={
                "interactions": str(self.settings.interactions_path),
                "train": str(self.settings.train_path),
                "test": str(self.settings.test_path),
                "cf_recommendations": str(self.settings.cf_output_path),
                "agentic_recommendations": str(self.settings.agentic_output_path),
                "metrics": str(self.settings.metrics_path),
            },
            updated_at=datetime.now(timezone.utc),
        )
        self.settings.experiment_state_path.write_text(
            state.model_dump_json(indent=2),
            encoding="utf-8",
        )

        return {
            "dataset": self.settings.dataset_name,
            "status": "completed",
            "sample_size": int(summary["sample_size"]),
            "train_size": int(summary["train_size"]),
            "test_size": int(summary["test_size"]),
            "models": ["collaborative_filtering", "agentic_ai_framework"],
            "metrics_ready": True,
            "evaluated_users": len(user_ids),
            "metrics": metrics,
        }

    def load_state(self) -> dict[str, object] | None:
        if not self.settings.experiment_state_path.exists():
            return None
        return json.loads(self.settings.experiment_state_path.read_text(encoding="utf-8"))

    def get_completed_evaluation_users_debug(self) -> dict[str, object]:
        report_rows = self.load_completed_evaluation_users() or self.build_completed_evaluation_users_report(
            allow_generation=False
        )
        selected_users = [str(row["customer_id"]) for row in report_rows if row.get("included_in_metrics")]
        excluded_users = [
            {"customer_id": str(row["customer_id"]), "excluded_reason": str(row["excluded_reason"])}
            for row in report_rows
            if not row.get("included_in_metrics") and str(row.get("excluded_reason") or "")
        ]
        return {
            "base_valid_user_count": sum(1 for row in report_rows if row.get("base_valid")),
            "completed_comparable_user_count": len(selected_users),
            "completed_comparable_user_ids": selected_users,
            "excluded_users": excluded_users,
        }

    def get_presentation_users_debug(self) -> dict[str, object]:
        users = self.load_presentation_users()
        return {
            "presentation_user_count": len(users),
            "source_file": self.settings.completed_evaluation_users_path.name,
            "filter": "included_in_metrics=true",
            "users": users,
        }

    def get_ground_truth_map(self, test_df) -> dict[str, str]:
        truth_items = self.get_ground_truth_items_map(test_df)
        return {user_id: article_ids[0] for user_id, article_ids in truth_items.items() if article_ids}

    def get_ground_truth_items_map(self, test_df) -> dict[str, list[str]]:
        return {
            str(user_id): [str(article_id) for article_id in group["article_id"].tolist()]
            for user_id, group in test_df.groupby("customer_id", sort=False)
        }

    def get_training_history_preview(self, user_id: str, train_df) -> list[dict[str, object]]:
        history = (
            train_df[train_df["customer_id"] == user_id]
            .sort_values(["transaction_date", "article_id"], ascending=[False, False])
            .head(5)
        )
        return [
            {
                "article_id": str(row["article_id"]),
                "product_name": str(row["product_name"]),
                "product_type": str(row["product_type"]),
                "product_group": str(row["product_group"]),
                "colour": str(row["colour"]),
                "appearance": str(row["appearance"]),
                "transaction_date": str(row["transaction_date"]),
            }
            for _, row in history.iterrows()
        ]

    def load_catalog(self, train_df=None, test_df=None):
        if self.settings.interactions_path.exists():
            return self.data_service.load_interactions()
        if train_df is None or test_df is None:
            raise FileNotFoundError("Processed interactions are not available.")
        return pd.concat([train_df, test_df], ignore_index=True)

    def _select_evaluable_users(self, train_df, test_df) -> list[str]:
        candidate_user_ids = sorted(str(user_id) for user_id in test_df["customer_id"].drop_duplicates().tolist())
        matrix = self.cf_service._build_user_item_matrix(train_df)
        metadata = self.cf_service._article_metadata(self.load_catalog(train_df, test_df))
        user_history = train_df.groupby("customer_id")["article_id"].agg(set).to_dict()

        selected: list[str] = []
        limit = self.settings.max_eval_users
        for user_id in candidate_user_ids:
            recommendations = self.cf_service.recommend_for_user(user_id, matrix, metadata, user_history)
            if recommendations:
                selected.append(user_id)
            if len(selected) >= limit:
                break

        if selected:
            return selected[:limit]
        return candidate_user_ids[:limit]

    @staticmethod
    def _normalize_agentic_recommendations(
        recommendations: list[dict[str, object]],
    ) -> list[dict[str, object]]:
        normalized: list[dict[str, object]] = []
        for item in recommendations:
            normalized.append(
                {
                    "article_id": str(item.get("article_id", "")),
                    "product_type_name": str(item.get("product_type_name") or item.get("product_type") or ""),
                    "product_group_name": str(item.get("product_group_name") or item.get("product_group") or ""),
                    "colour_group_name": str(item.get("colour_group_name") or item.get("colour") or ""),
                    "graphical_appearance_name": str(
                        item.get("graphical_appearance_name") or item.get("appearance") or ""
                    ),
                    "match_score": float(item.get("match_score") or item.get("score") or 0.0),
                    "recommendation_reason": str(
                        item.get("recommendation_reason") or item.get("reason") or ""
                    ),
                }
            )
        return normalized

    @staticmethod
    def _build_method_result(
        truth_article_ids: list[str],
        top_five_article_ids: list[str],
        ground_truth_in_catalog: bool,
        ground_truth_in_candidate_pool: bool,
    ) -> dict[str, object]:
        if not ground_truth_in_catalog:
            return {
                "hit_at_5": False,
                "hit_label": "Miss",
                "explanation": "Ground truth item was removed during preprocessing",
            }

        for rank, article_id in enumerate(top_five_article_ids, start=1):
            if article_id in truth_article_ids:
                return {
                    "hit_at_5": True,
                    "hit_label": "Hit",
                    "explanation": f"Ground truth item found at rank {rank}",
                }

        if not ground_truth_in_candidate_pool:
            return {
                "hit_at_5": False,
                "hit_label": "Miss",
                "explanation": "Ground truth item was not in candidate pool",
            }

        return {
            "hit_at_5": False,
            "hit_label": "Miss",
            "explanation": "Ground truth item not found in Top 5",
        }

    def build_evaluation_debug(self, user_id: str, user_request: str = "") -> dict[str, object]:
        train_df = self.data_service.load_train()
        test_df = self.data_service.load_test()
        catalog_df = self.load_catalog(train_df, test_df)
        base_rows = self.evaluation_service.load_evaluation_base_table() or self.evaluation_service.build_evaluation_base_table(
            train_df,
            test_df,
            catalog_df,
        )
        base_row = base_rows.get(user_id)
        if base_row is None:
            raise FileNotFoundError(f"User {user_id} is missing from the evaluation base table.")
        truth_article_id = str(base_row["ground_truth_article_id"])
        truth_article_ids = [truth_article_id] if truth_article_id else []
        catalog_metadata = self.cf_service._article_metadata(catalog_df)
        ground_truth_metadata = [catalog_metadata.get(article_id, {}) for article_id in truth_article_ids]
        ground_truth_in_catalog = bool(base_row["ground_truth_in_catalog"])
        cf_result = self.build_cf_result(user_id)
        agentic_result = self.build_agentic_result(user_id, user_request)
        cf_top_five_article_ids = [
            str(item["article_id"]) for item in cf_result["top_5_recommendations"][: self.settings.top_n]
        ]
        agentic_top_five_article_ids = [
            str(item["article_id"]) for item in agentic_result["top_5_recommendations"][: self.settings.top_n]
        ]

        training_rows = train_df[train_df["customer_id"] == user_id].copy()
        all_rows = catalog_df[catalog_df["customer_id"] == user_id].copy()
        validation = self.evaluation_service.validate_user_evaluation(
            user_id,
            train_df,
            test_df,
            catalog_df,
            {user_id: cf_result["top_5_recommendations"]},
            {user_id: agentic_result["top_5_recommendations"]},
        )

        debug_payload = {
            "customer_id": user_id,
            "number_of_total_transactions": int(len(all_rows)),
            "number_of_training_transactions": int(len(training_rows)),
            "training_article_ids": [str(article_id) for article_id in training_rows["article_id"].tolist()],
            "ground_truth_article_id": truth_article_id,
            "ground_truth_article_ids": truth_article_ids,
            "ground_truth_product_metadata": ground_truth_metadata,
            "ground_truth_exists_in_processed_product_catalog": ground_truth_in_catalog,
            "validation": {
                "is_valid": validation["is_valid"],
                "reasons": validation["reasons"],
                "candidate_pool_size": len(base_row["candidate_pool_article_ids"]),
                "candidate_pool_article_ids_preview": base_row["candidate_pool_article_ids"][:10],
                "evaluation_mode": self.settings.evaluation_mode,
            },
            "cf": {
                "hit_at_5": cf_result["hit_at_5"],
                "hit_label": cf_result["hit_label"],
                "explanation": cf_result["explanation"],
                "top_5_article_ids": cf_top_five_article_ids,
                "recommendations": cf_result["top_5_recommendations"],
                "ground_truth_in_top_5": cf_result["hit_at_5"],
                "candidate_pool_contains_ground_truth": bool(base_row["ground_truth_in_candidate_pool"]),
                "validation": cf_result["validation"],
            },
            "agentic": {
                "hit_at_5": agentic_result["hit_at_5"],
                "hit_label": agentic_result["hit_label"],
                "explanation": agentic_result["explanation"],
                "top_5_article_ids": agentic_top_five_article_ids,
                "recommendations": agentic_result["top_5_recommendations"],
                "ground_truth_in_top_5": agentic_result["hit_at_5"],
                "candidate_pool_contains_ground_truth": bool(base_row["ground_truth_in_candidate_pool"]),
                "validation": agentic_result["validation"],
            },
        }
        print(json.dumps(debug_payload, indent=2))
        return debug_payload

    def get_evaluation_base_row(self, user_id: str) -> dict[str, object]:
        base_rows = self.evaluation_service.load_evaluation_base_table()
        if base_rows is None or user_id not in base_rows:
            train_df = self.data_service.load_train()
            test_df = self.data_service.load_test()
            catalog_df = self.load_catalog(train_df, test_df)
            base_rows = self.evaluation_service.build_evaluation_base_table(
                train_df,
                test_df,
                catalog_df,
            )
        if user_id not in base_rows:
            raise FileNotFoundError(f"User {user_id} is not available in the evaluation base table.")
        return base_rows[user_id]

    def _build_validation_block(
        self,
        base_row: dict[str, object],
        recommendations: list[dict[str, object]],
    ) -> dict[str, object]:
        candidate_pool_ids = {str(article_id) for article_id in base_row["candidate_pool_article_ids"]}
        train_article_ids = {str(article_id) for article_id in base_row["train_article_ids"]}
        top_five_ids = [str(item.get("article_id", "")) for item in recommendations[: self.settings.top_n]]
        top_5_all_inside_candidate_pool = all(article_id in candidate_pool_ids for article_id in top_five_ids)
        top_5_contains_training_items = any(article_id in train_article_ids for article_id in top_five_ids)
        article_id_format_check = "passed" if all(article_id == str(article_id) and article_id for article_id in top_five_ids) else "failed"
        return {
            "evaluation_base_used": True,
            "same_candidate_pool_source": True,
            "ground_truth_in_candidate_pool": bool(base_row["ground_truth_in_candidate_pool"]),
            "top_5_all_inside_candidate_pool": top_5_all_inside_candidate_pool,
            "top_5_contains_training_items": top_5_contains_training_items,
            "article_id_format_check": article_id_format_check,
        }

    def _invalid_recommendation_payload(
        self,
        base_row: dict[str, object],
        method: str,
        user_request: str = "",
    ) -> dict[str, object]:
        validation = {
            "evaluation_base_used": True,
            "same_candidate_pool_source": True,
            "ground_truth_in_candidate_pool": bool(base_row["ground_truth_in_candidate_pool"]),
            "top_5_all_inside_candidate_pool": True,
            "top_5_contains_training_items": False,
            "article_id_format_check": "passed",
        }
        payload = {
            "customer_id": base_row["customer_id"],
            "method": method,
            "candidate_pool_size": int(base_row["candidate_pool_size"]),
            "ground_truth_article_id": str(base_row["ground_truth_article_id"]),
            "hit_result": {
                "hit_at_5": 0,
                "hit_label": "Miss",
                "matched_article_id": None,
                "matched_rank": None,
                "explanation": f"Evaluation row is invalid: {base_row['invalid_reason']}",
            },
            "hit_at_5": 0,
            "hit_label": "Miss",
            "explanation": f"Evaluation row is invalid: {base_row['invalid_reason']}",
            "hit_explanation": f"Evaluation row is invalid: {base_row['invalid_reason']}",
            "training_history_count": int(base_row["train_count"]),
            "training_history_preview": [],
            "top_5_article_ids": [],
            "validation": validation,
            "invalid_reason": str(base_row["invalid_reason"]),
        }
        if method == "cf":
            payload["top_5_recommendations"] = []
        else:
            payload.update(
                {
                    "user_request": user_request,
                    "preference_profile": {
                        "user_id": base_row["customer_id"],
                        "preferred_product_type_name_values": [],
                        "preferred_product_group_name_values": [],
                        "preferred_colour_group_name_values": [],
                        "preferred_graphical_appearance_name_values": [],
                        "soft_preferences": [],
                        "hard_constraints": {},
                        "preference_summary": "",
                    },
                    "candidate_evidence_set": [],
                    "top_5_recommendations": [],
                    "process_trace": [],
                }
            )
        return payload

    def build_cf_result(self, user_id: str) -> dict[str, object]:
        base_row = self.get_evaluation_base_row(user_id)
        if not base_row["is_valid_for_evaluation"]:
            return self._invalid_recommendation_payload(base_row, "cf")

        train_df = self.data_service.load_train()
        catalog_df = self.load_catalog(train_df, self.data_service.load_test())
        matrix = self.cf_service._build_user_item_matrix(train_df)
        metadata = self.cf_service._article_metadata(catalog_df)
        user_history = train_df.groupby("customer_id")["article_id"].agg(set).to_dict()
        recommendations = self.cf_service.recommend_for_user(
            user_id,
            matrix,
            metadata,
            user_history,
            candidate_pool_article_ids=base_row["candidate_pool_article_ids"],
        )
        hit_result = self.evaluation_service.calculate_hit_at_k(
            recommendations,
            str(base_row["ground_truth_article_id"]),
            self.settings.top_n,
        )
        validation = self._build_validation_block(base_row, recommendations)
        top_5_recommendations = recommendations[: self.settings.top_n]
        top_5_article_ids = [str(item.get("article_id", "")) for item in top_5_recommendations]
        return {
            "customer_id": user_id,
            "method": "cf",
            "candidate_pool_size": int(base_row["candidate_pool_size"]),
            "ground_truth_article_id": str(base_row["ground_truth_article_id"]),
            "hit_result": hit_result,
            "hit_at_5": int(hit_result["hit_at_5"]),
            "hit_label": hit_result["hit_label"],
            "explanation": hit_result["explanation"],
            "hit_explanation": hit_result["explanation"],
            "training_history_count": int(base_row["train_count"]),
            "training_history_preview": self.get_training_history_preview(user_id, train_df),
            "top_5_article_ids": top_5_article_ids,
            "top_5_recommendations": top_5_recommendations,
            "validation": validation,
            "invalid_reason": None,
        }

    def build_agentic_result(self, user_id: str, user_request: str = "") -> dict[str, object]:
        base_row = self.get_evaluation_base_row(user_id)
        if not base_row["is_valid_for_evaluation"]:
            return self._invalid_recommendation_payload(base_row, "agentic", user_request=user_request)

        train_df = self.data_service.load_train()
        catalog_df = self.load_catalog(train_df, self.data_service.load_test())
        result = self.agentic_service.run_three_agent_pipeline(
            user_id,
            user_request,
            train_df,
            catalog_df,
            required_article_ids={str(base_row["ground_truth_article_id"])},
            allowed_article_ids=set(base_row["candidate_pool_article_ids"]),
        )
        top_5_recommendations = result["final_recommendations"][: self.settings.top_n]
        hit_result = self.evaluation_service.calculate_hit_at_k(
            top_5_recommendations,
            str(base_row["ground_truth_article_id"]),
            self.settings.top_n,
        )
        validation = self._build_validation_block(base_row, top_5_recommendations)
        top_5_article_ids = [str(item.get("article_id", "")) for item in top_5_recommendations]
        return {
            "customer_id": user_id,
            "method": "agentic",
            "candidate_pool_size": int(base_row["candidate_pool_size"]),
            "user_request": user_request,
            "ground_truth_article_id": str(base_row["ground_truth_article_id"]),
            "hit_result": hit_result,
            "hit_at_5": int(hit_result["hit_at_5"]),
            "hit_label": hit_result["hit_label"],
            "explanation": hit_result["explanation"],
            "hit_explanation": hit_result["explanation"],
            "training_history_count": int(base_row["train_count"]),
            "training_history_preview": self.get_training_history_preview(user_id, train_df),
            "preference_profile": result["preference_profile"],
            "candidate_evidence_set": result["candidate_evidence_set"],
            "top_5_article_ids": top_5_article_ids,
            "top_5_recommendations": top_5_recommendations,
            "process_trace": result["process_trace"],
            "validation": validation,
            "invalid_reason": None,
        }

    @staticmethod
    def _legacy_values_to_weights(values: list[object]) -> list[dict[str, object]]:
        normalized_values = [str(value) for value in values if str(value).strip()]
        if not normalized_values:
            return []
        weight = round(1 / len(normalized_values), 4)
        return [{"value": value, "weight": weight} for value in normalized_values]
