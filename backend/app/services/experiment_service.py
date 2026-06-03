from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone

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
        user_ids = self._select_evaluable_users(test_df)
        summary["evaluated_user_ids"] = user_ids
        summary["evaluated_users"] = len(user_ids)
        self.settings.summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

        cf_recommendations = self.cf_service.generate_all(train_df, user_ids)
        agentic_recommendations = self.agentic_service.generate_all(train_df, user_ids)
        metrics = self.evaluation_service.evaluate(test_df, cf_recommendations, agentic_recommendations)

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
        return {
            str(row["customer_id"]): str(row["article_id"])
            for _, row in test_df.iterrows()
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

    def _select_evaluable_users(self, test_df) -> list[str]:
        user_ids = sorted(str(user_id) for user_id in test_df["customer_id"].drop_duplicates().tolist())
        return user_ids[: self.settings.max_eval_users]
