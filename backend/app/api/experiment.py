from __future__ import annotations

from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
from app.models.schemas import ExperimentSetupResponse, RunExperimentResponse
from app.services.agentic_service import AgenticRecommendationService
from app.services.cf_service import CollaborativeFilteringService
from app.services.data_service import DataService
from app.services.evaluation_service import EvaluationService
from app.services.experiment_service import ExperimentService

router = APIRouter(prefix="/experiment", tags=["experiment"])


def get_experiment_service(settings: Settings = Depends(get_settings)) -> ExperimentService:
    data_service = DataService(settings)
    return ExperimentService(
        settings=settings,
        data_service=data_service,
        cf_service=CollaborativeFilteringService(settings),
        agentic_service=AgenticRecommendationService(settings),
        evaluation_service=EvaluationService(settings),
    )


@router.post("/run", response_model=RunExperimentResponse)
def run_experiment(service: ExperimentService = Depends(get_experiment_service)) -> dict[str, object]:
    payload = service.run()
    return {
        "dataset": payload["dataset"],
        "status": payload["status"],
        "sample_size": payload["sample_size"],
        "train_size": payload["train_size"],
        "test_size": payload["test_size"],
        "models": payload["models"],
        "metrics_ready": payload["metrics_ready"],
        "evaluated_users": payload["evaluated_users"],
    }


@router.get("/setup", response_model=ExperimentSetupResponse)
def get_setup(
    settings: Settings = Depends(get_settings),
    service: ExperimentService = Depends(get_experiment_service),
) -> dict[str, object]:
    summary = DataService(settings).load_summary()
    presentation_users = service.load_presentation_users()
    curated_user_ids = [str(row["customer_id"]) for row in presentation_users]
    if summary:
        summary = {
            **summary,
            "sample_user_ids": curated_user_ids,
            "evaluated_user_ids": curated_user_ids,
            "evaluated_users": len(curated_user_ids),
            "available_user_ids": curated_user_ids,
            "completed_comparable_user_ids": curated_user_ids,
            "completed_comparable_user_count": len(curated_user_ids),
            "valid_completed_user_count": len(curated_user_ids),
            "selected_user_ids": curated_user_ids,
            "presentation_user_count": len(curated_user_ids),
            "presentation_mode": True,
            "user_selection_method": "completed_evaluation_users_included_in_metrics",
            "max_valid_eval_users": settings.max_valid_eval_users,
        }
    sample_size = int(summary["sample_size"]) if summary else settings.sample_size
    return {
        "presentation_mode": True,
        "user_selection_method": "completed_evaluation_users_included_in_metrics",
        "selected_user_ids": curated_user_ids,
        "dataset": settings.dataset_name,
        "sample_size": sample_size,
        "split_method": "Leave-one-out next-item evaluation",
        "benchmark": "Collaborative Filtering",
        "proposed_framework": "3-Agent Agentic AI Recommendation Framework",
        "evaluation_metrics": ["Hit@5"],
        "available_user_ids": curated_user_ids,
        "completed_comparable_user_ids": curated_user_ids,
        "valid_completed_user_count": len(curated_user_ids),
        "completed_comparable_user_count": len(curated_user_ids),
        "presentation_user_count": len(curated_user_ids),
        "valid_evaluation_users": presentation_users,
        "max_valid_eval_users": settings.max_valid_eval_users,
        "summary": summary,
    }
