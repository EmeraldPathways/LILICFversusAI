from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass
from datetime import datetime, timezone

import pandas as pd

from app.config import Settings


@dataclass
class EvaluationService:
    settings: Settings

    @staticmethod
    def calculate_hit_at_k(
        recommendations: list[dict[str, object]],
        ground_truth_article_id: str,
        k: int = 5,
    ) -> dict[str, object]:
        top_k_article_ids = [str(item.get("article_id", "")) for item in recommendations[:k]]
        for rank, article_id in enumerate(top_k_article_ids, start=1):
            if article_id == str(ground_truth_article_id):
                return {
                    "hit_at_5": 1,
                    "hit_label": "Hit",
                    "matched_article_id": article_id,
                    "matched_rank": rank,
                    "explanation": f"Ground truth item found at rank {rank}",
                }
        return {
            "hit_at_5": 0,
            "hit_label": "Miss",
            "matched_article_id": None,
            "matched_rank": None,
            "explanation": "Ground truth item not found in Top 5",
        }

    def build_candidate_pool(
        self,
        customer_id: str,
        train_article_ids: list[str],
        ground_truth_article_id: str,
        catalog_article_ids: set[str],
    ) -> list[str]:
        train_history = set(train_article_ids)
        negatives = sorted(
            article_id
            for article_id in catalog_article_ids
            if article_id not in train_history and article_id != ground_truth_article_id
        )
        negative_limit = max(self.settings.candidate_pool_size - 1, 0)
        if self.settings.evaluation_mode == "deterministic":
            selected_negatives = negatives[:negative_limit]
        else:
            seed_material = f"{self.settings.evaluation_seed}:{customer_id}".encode("utf-8")
            seed = int(hashlib.sha256(seed_material).hexdigest()[:16], 16)
            rng = random.Random(seed)
            selected_negatives = (
                rng.sample(negatives, k=negative_limit)
                if len(negatives) > negative_limit
                else list(negatives)
            )
        candidate_pool = [ground_truth_article_id] if ground_truth_article_id in catalog_article_ids else []
        candidate_pool.extend(selected_negatives)
        return list(dict.fromkeys(candidate_pool))

    def build_evaluation_base_table(
        self,
        train_df: pd.DataFrame,
        test_df: pd.DataFrame,
        catalog_df: pd.DataFrame,
        selected_ui_customer_ids: list[str] | None = None,
    ) -> dict[str, dict[str, object]]:
        catalog_article_ids = {str(article_id) for article_id in catalog_df["article_id"].astype(str).tolist()}
        train_lookup = {
            str(customer_id): group.copy()
            for customer_id, group in train_df.groupby("customer_id", sort=False)
        }
        test_lookup = {
            str(customer_id): group.copy()
            for customer_id, group in test_df.groupby("customer_id", sort=False)
        }
        customer_ids = sorted(set(train_lookup) | set(test_lookup))
        base_rows: dict[str, dict[str, object]] = {}
        invalid_reason_counts: dict[str, int] = {}

        for customer_id in customer_ids:
            train_rows = train_lookup.get(customer_id, pd.DataFrame(columns=train_df.columns))
            test_rows = test_lookup.get(customer_id, pd.DataFrame(columns=test_df.columns))
            total_transaction_count = int(len(train_rows) + len(test_rows))
            train_article_ids = [str(article_id) for article_id in train_rows["article_id"].astype(str).tolist()]
            train_transaction_dates = [str(value) for value in train_rows["transaction_date"].tolist()]
            ground_truth_article_id = (
                str(test_rows.iloc[-1]["article_id"])
                if not test_rows.empty
                else ""
            )
            ground_truth_transaction_date = (
                str(test_rows.iloc[-1]["transaction_date"])
                if not test_rows.empty
                else ""
            )
            ground_truth_row = test_rows.iloc[-1] if not test_rows.empty else None
            ground_truth_in_catalog = ground_truth_article_id in catalog_article_ids if ground_truth_article_id else False
            candidate_pool_article_ids = self.build_candidate_pool(
                customer_id,
                train_article_ids,
                ground_truth_article_id,
                catalog_article_ids,
            )
            ground_truth_in_candidate_pool = ground_truth_article_id in candidate_pool_article_ids

            reasons: list[str] = []
            if total_transaction_count < self.settings.min_user_interactions:
                reasons.append("fewer_than_min_user_interactions")
            if len(train_article_ids) < 1:
                reasons.append("train_count_below_one")
            if not ground_truth_article_id:
                reasons.append("missing_ground_truth")
            if ground_truth_article_id and not ground_truth_in_catalog:
                reasons.append("ground_truth_missing_from_catalog")
            if ground_truth_article_id and not ground_truth_in_candidate_pool:
                reasons.append("ground_truth_not_in_candidate_pool")

            invalid_reason = ",".join(reasons)
            for reason in reasons:
                invalid_reason_counts[reason] = invalid_reason_counts.get(reason, 0) + 1

            base_rows[customer_id] = {
                "customer_id": customer_id,
                "total_transaction_count": total_transaction_count,
                "train_count": int(len(train_article_ids)),
                "train_article_ids": train_article_ids,
                "train_transaction_dates": train_transaction_dates,
                "ground_truth_article_id": ground_truth_article_id,
                "ground_truth_transaction_date": ground_truth_transaction_date,
                "ground_truth_product_type": str(ground_truth_row["product_type"]) if ground_truth_row is not None else "",
                "ground_truth_product_group": str(ground_truth_row["product_group"]) if ground_truth_row is not None else "",
                "ground_truth_colour": str(ground_truth_row["colour"]) if ground_truth_row is not None else "",
                "ground_truth_appearance": str(ground_truth_row["appearance"]) if ground_truth_row is not None else "",
                "ground_truth_in_catalog": ground_truth_in_catalog,
                "candidate_pool_article_ids": candidate_pool_article_ids,
                "candidate_pool_size": len(candidate_pool_article_ids),
                "ground_truth_in_candidate_pool": ground_truth_in_candidate_pool,
                "is_valid_for_evaluation": not reasons,
                "invalid_reason": invalid_reason,
            }

        row_list = list(base_rows.values())
        pd.DataFrame(row_list).to_csv(self.settings.evaluation_base_table_path, index=False)
        self.settings.evaluation_base_table_json_path.write_text(
            json.dumps(row_list, indent=2),
            encoding="utf-8",
        )

        selected_ui_customer_ids = selected_ui_customer_ids or []
        validation_report = {
            "total_customers_raw": len(customer_ids),
            "eligible_customers_before_validation": sum(
                1 for row in row_list if row["total_transaction_count"] >= self.settings.min_user_interactions
            ),
            "valid_evaluation_customers": sum(1 for row in row_list if row["is_valid_for_evaluation"]),
            "invalid_evaluation_customers": sum(1 for row in row_list if not row["is_valid_for_evaluation"]),
            "invalid_reason_counts": invalid_reason_counts,
            "selected_ui_customer_ids": selected_ui_customer_ids,
            "selected_ui_customers": [
                {
                    "customer_id": customer_id,
                    "is_valid_for_evaluation": base_rows[customer_id]["is_valid_for_evaluation"],
                    "invalid_reason": base_rows[customer_id]["invalid_reason"],
                    "train_count": base_rows[customer_id]["train_count"],
                    "ground_truth_article_id": base_rows[customer_id]["ground_truth_article_id"],
                    "ground_truth_in_catalog": base_rows[customer_id]["ground_truth_in_catalog"],
                    "ground_truth_in_candidate_pool": base_rows[customer_id]["ground_truth_in_candidate_pool"],
                    "candidate_pool_size": base_rows[customer_id]["candidate_pool_size"],
                }
                for customer_id in selected_ui_customer_ids
                if customer_id in base_rows
            ],
        }
        self.settings.evaluation_validation_report_path.write_text(
            json.dumps(validation_report, indent=2),
            encoding="utf-8",
        )
        return base_rows

    def load_evaluation_base_table(self) -> dict[str, dict[str, object]] | None:
        if not self.settings.evaluation_base_table_json_path.exists():
            return None
        rows = json.loads(self.settings.evaluation_base_table_json_path.read_text(encoding="utf-8"))
        return {str(row["customer_id"]): row for row in rows}

    def load_validation_report(self) -> dict[str, object] | None:
        if not self.settings.evaluation_validation_report_path.exists():
            return None
        return json.loads(self.settings.evaluation_validation_report_path.read_text(encoding="utf-8"))

    def validate_user_evaluation(
        self,
        user_id: str,
        train_df: pd.DataFrame,
        test_df: pd.DataFrame,
        catalog_df: pd.DataFrame,
        cf_recommendations: dict[str, list[dict[str, object]]],
        agentic_recommendations: dict[str, list[dict[str, object]]],
    ) -> dict[str, object]:
        base_rows = self.load_evaluation_base_table() or self.build_evaluation_base_table(
            train_df,
            test_df,
            catalog_df,
        )
        base_row = base_rows.get(user_id)
        if base_row is None:
            return {
                "user_id": user_id,
                "is_valid": False,
                "reasons": ["missing_evaluation_base_row"],
                "ground_truth_article_ids": [],
                "candidate_pool_article_ids": [],
                "base_row": None,
            }

        reasons = [reason for reason in str(base_row["invalid_reason"]).split(",") if reason]
        if not cf_recommendations.get(user_id):
            reasons.append("missing_cf_recommendations")
        if not agentic_recommendations.get(user_id):
            reasons.append("missing_agentic_recommendations")

        return {
            "user_id": user_id,
            "is_valid": not reasons,
            "reasons": reasons,
            "ground_truth_article_ids": [str(base_row["ground_truth_article_id"])] if base_row["ground_truth_article_id"] else [],
            "candidate_pool_article_ids": [str(article_id) for article_id in base_row["candidate_pool_article_ids"]],
            "base_row": base_row,
        }

    def evaluate(
        self,
        train_df: pd.DataFrame,
        test_df: pd.DataFrame,
        catalog_df: pd.DataFrame,
        cf_recommendations: dict[str, list[dict[str, object]]],
        agentic_recommendations: dict[str, list[dict[str, object]]],
        selected_user_ids: list[str] | None = None,
    ) -> dict[str, object]:
        selected_user_ids = selected_user_ids or sorted(
            set(test_df["customer_id"].astype(str).tolist())
            | set(cf_recommendations)
            | set(agentic_recommendations)
        )
        base_rows = self.build_evaluation_base_table(
            train_df,
            test_df,
            catalog_df,
            selected_ui_customer_ids=selected_user_ids,
        )

        cf_hits = 0
        agentic_hits = 0
        valid_user_ids: list[str] = []
        excluded_users: list[dict[str, object]] = []

        for user_id in selected_user_ids:
            validation = self.validate_user_evaluation(
                user_id,
                train_df,
                test_df,
                catalog_df,
                cf_recommendations,
                agentic_recommendations,
            )
            if not validation["is_valid"]:
                excluded_users.append({"user_id": user_id, "reasons": validation["reasons"]})
                continue

            ground_truth_items = [str(base_rows[user_id]["ground_truth_article_id"])]
            valid_user_ids.append(user_id)
            cf_hits += int(
                self.calculate_hit_at_k(
                    cf_recommendations.get(user_id, []),
                    ground_truth_items[0],
                    self.settings.top_n,
                )["hit_at_5"]
            )
            agentic_hits += int(
                self.calculate_hit_at_k(
                    agentic_recommendations.get(user_id, []),
                    ground_truth_items[0],
                    self.settings.top_n,
                )["hit_at_5"]
            )

        valid_count = len(valid_user_ids)
        cf_hit_at_5 = round(cf_hits / valid_count, 4) if valid_count else 0.0
        agentic_hit_at_5 = round(agentic_hits / valid_count, 4) if valid_count else 0.0
        metrics = {
            "collaborative_filtering": {"hit_at_5": cf_hit_at_5},
            "agentic_ai_framework": {"hit_at_5": agentic_hit_at_5},
            "total_selected_users": len(selected_user_ids),
            "valid_evaluation_users": valid_count,
            "invalid_evaluation_users": len(excluded_users),
            "evaluated_users": valid_count,
            "cf_hit_at_5": cf_hit_at_5,
            "agentic_hit_at_5": agentic_hit_at_5,
            "cf_hits_count": cf_hits,
            "agentic_hits_count": agentic_hits,
            "evaluated_user_ids": valid_user_ids,
            "excluded_user_ids_with_reasons": excluded_users,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        self.settings.metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
        self.settings.invalid_evaluation_users_path.write_text(
            json.dumps(excluded_users, indent=2),
            encoding="utf-8",
        )
        return metrics

    def load_metrics(self) -> dict[str, object] | None:
        if not self.settings.metrics_path.exists():
            return None
        return json.loads(self.settings.metrics_path.read_text(encoding="utf-8"))
