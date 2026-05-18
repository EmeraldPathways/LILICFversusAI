from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.experiment import get_experiment_service
from app.models.schemas import FeedbackRequest, FeedbackResponse, UserIntentResponse
from app.services.agentic_service import AgenticServiceError
from app.services.data_service import DataValidationError
from app.services.experiment_service import ExperimentService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/{user_id}/intent", response_model=UserIntentResponse)
def get_user_intent(
    user_id: str,
    service: ExperimentService = Depends(get_experiment_service),
) -> dict[str, object]:
    try:
        train_df = service.data_service.load_train()
        return service.agentic_service.infer_user_intent(user_id, train_df)
    except FileNotFoundError as exc:
        raise DataValidationError("Run the experiment first to generate training data.") from exc


@router.post("/{user_id}/feedback", response_model=FeedbackResponse)
def submit_feedback(
    user_id: str,
    payload: FeedbackRequest,
    service: ExperimentService = Depends(get_experiment_service),
) -> dict[str, object]:
    updated_weights = service.agentic_service.adapt_from_feedback(
        user_id=user_id,
        article_id=payload.article_id,
        feedback_type=payload.feedback_type,
    )
    return {
        "status": "updated",
        "message": f"User preference weights updated based on {payload.feedback_type} feedback.",
        "user_id": user_id,
        "article_id": payload.article_id,
        "feedback_type": payload.feedback_type,
        "updated_weights": updated_weights,
    }

