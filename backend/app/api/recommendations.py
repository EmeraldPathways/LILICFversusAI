from __future__ import annotations

import json

from fastapi import APIRouter, Depends

from app.api.experiment import get_experiment_service
from app.models.schemas import RecommendationComparisonResponse
from app.services.experiment_service import ExperimentService

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("/compare/{user_id}", response_model=RecommendationComparisonResponse)
def compare_recommendations(
    user_id: str,
    service: ExperimentService = Depends(get_experiment_service),
) -> dict[str, object]:
    if not service.settings.cf_output_path.exists() or not service.settings.agentic_output_path.exists():
        raise FileNotFoundError("Run the experiment first to generate recommendation outputs.")

    cf_payload = json.loads(service.settings.cf_output_path.read_text(encoding="utf-8"))
    agentic_payload = json.loads(service.settings.agentic_output_path.read_text(encoding="utf-8"))
    return {
        "user_id": user_id,
        "cf_recommendations": cf_payload.get(user_id, []),
        "agentic_recommendations": agentic_payload.get(user_id, []),
    }

