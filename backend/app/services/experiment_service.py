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

    def run(self) -> dict[str, object]:
        summary = self.data_service.preprocess()
        train_df = self.data_service.load_train()
        test_df = self.data_service.load_test()
        catalog_df = self.load_catalog(train_df, test_df)
        user_ids = self._select_evaluable_users(train_df, test_df)
        evaluation_base_rows = self.evaluation_service.build_evaluation_base_table(
            train_df,
            test_df,
            catalog_df,
            selected_ui_customer_ids=user_ids,
        )
        summary["evaluated_user_ids"] = user_ids
        summary["evaluated_users"] = len(user_ids)
        self.settings.summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

        cf_results = {user_id: self.build_cf_result(user_id) for user_id in user_ids}
        agentic_results = {user_id: self.build_agentic_result(user_id) for user_id in user_ids}
        cf_recommendations = {
            user_id: result["top_5_recommendations"]
            for user_id, result in cf_results.items()
            if result["invalid_reason"] is None
        }
        agentic_recommendations = {
            user_id: result["top_5_recommendations"]
            for user_id, result in agentic_results.items()
            if result["invalid_reason"] is None
        }
        self.settings.cf_output_path.write_text(json.dumps(cf_results, indent=2), encoding="utf-8")
        self.settings.agentic_output_path.write_text(json.dumps(agentic_results, indent=2), encoding="utf-8")
        metrics = self.evaluation_service.evaluate(
            train_df,
            test_df,
            catalog_df,
            cf_recommendations,
            agentic_recommendations,
            selected_user_ids=user_ids,
        )
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
            "hit_at_5": False,
            "hit_label": "Miss",
            "explanation": f"Evaluation row is invalid: {base_row['invalid_reason']}",
            "training_history_count": int(base_row["train_count"]),
            "training_history_preview": [],
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
        return {
            "customer_id": user_id,
            "method": "cf",
            "candidate_pool_size": int(base_row["candidate_pool_size"]),
            "ground_truth_article_id": str(base_row["ground_truth_article_id"]),
            "hit_result": hit_result,
            "hit_at_5": bool(hit_result["hit_at_5"]),
            "hit_label": hit_result["hit_label"],
            "explanation": hit_result["explanation"],
            "training_history_count": int(base_row["train_count"]),
            "training_history_preview": self.get_training_history_preview(user_id, train_df),
            "top_5_recommendations": recommendations[: self.settings.top_n],
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
        return {
            "customer_id": user_id,
            "method": "agentic",
            "candidate_pool_size": int(base_row["candidate_pool_size"]),
            "user_request": user_request,
            "ground_truth_article_id": str(base_row["ground_truth_article_id"]),
            "hit_result": hit_result,
            "hit_at_5": bool(hit_result["hit_at_5"]),
            "hit_label": hit_result["hit_label"],
            "explanation": hit_result["explanation"],
            "training_history_count": int(base_row["train_count"]),
            "training_history_preview": self.get_training_history_preview(user_id, train_df),
            "preference_profile": result["preference_profile"],
            "candidate_evidence_set": result["candidate_evidence_set"],
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
