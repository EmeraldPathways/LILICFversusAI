from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.experiment import get_experiment_service
from app.models.schemas import AgenticRunResponse, CFRecommendationResponse, RecommendationRunRequest
from app.services.experiment_service import ExperimentService

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("/cf/{user_id}", response_model=CFRecommendationResponse)
def get_cf_recommendations(
    user_id: str,
    service: ExperimentService = Depends(get_experiment_service),
) -> dict[str, object]:
    return service.build_cf_result(user_id)


@router.post("/agentic/run", response_model=AgenticRunResponse)
def run_agentic_recommendations(
    payload: RecommendationRunRequest,
    service: ExperimentService = Depends(get_experiment_service),
) -> dict[str, object]:
    return service.build_agentic_result(payload.user_id, payload.user_request)
