from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.experiment import get_experiment_service
from app.services.experiment_service import ExperimentService

router = APIRouter(prefix="/debug", tags=["debug"])


@router.get("/evaluation/{user_id}")
def get_evaluation_debug(
    user_id: str,
    service: ExperimentService = Depends(get_experiment_service),
) -> dict[str, object]:
    return service.build_evaluation_debug(user_id)


@router.get("/evaluation-base/{user_id}")
def get_evaluation_base_debug(
    user_id: str,
    service: ExperimentService = Depends(get_experiment_service),
) -> dict[str, object]:
    return service.get_evaluation_base_row(user_id)


@router.get("/completed-evaluation-users")
def get_completed_evaluation_users_debug(
    service: ExperimentService = Depends(get_experiment_service),
) -> dict[str, object]:
    return service.get_completed_evaluation_users_debug()


@router.get("/comparable-users")
def get_comparable_users_debug(
    service: ExperimentService = Depends(get_experiment_service),
) -> dict[str, object]:
    return service.get_completed_evaluation_users_debug()
