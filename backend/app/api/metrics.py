from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.experiment import get_experiment_service
from app.models.schemas import MetricsResponse
from app.services.experiment_service import ExperimentService

router = APIRouter(tags=["metrics"])


@router.get("/metrics", response_model=MetricsResponse)
def get_metrics(service: ExperimentService = Depends(get_experiment_service)) -> dict[str, object]:
    return service.build_presentation_metrics()
