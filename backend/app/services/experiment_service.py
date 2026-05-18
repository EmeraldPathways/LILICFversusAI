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
        user_ids = self._select_evaluable_users(train_df, test_df)

        cf_recommendations = self.cf_service.generate_all(train_df, user_ids)
        agentic_recommendations = self.agentic_service.generate_all(train_df, user_ids)
        metrics = self.evaluation_service.evaluate(
            train_df, test_df, cf_recommendations, agentic_recommendations
        )

        state = ExperimentState(
            status="completed",
            dataset=self.settings.dataset_name,
            sample_size=int(summary["sample_size"]),
            train_size=int(summary["train_size"]),
            test_size=int(summary["test_size"]),
            evaluated_users=len(user_ids),
            models=["collaborative_filtering", "agentic_ai_framework"],
            metrics_ready=True,
            split_boundary_date=str(summary["split_boundary_date"]),
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

    def _select_evaluable_users(self, train_df, test_df) -> list[str]:
        train_users = set(train_df["customer_id"].astype(str))
        test_users = set(test_df["customer_id"].astype(str))
        common = sorted(train_users & test_users)
        return common[: self.settings.max_eval_users]

