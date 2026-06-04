from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.experiment import get_experiment_service
from app.models.schemas import ComparisonResponse
from app.services.experiment_service import ExperimentService

router = APIRouter(tags=["comparison"])


@router.get("/comparison/{user_id}", response_model=ComparisonResponse)
def get_comparison(
    user_id: str,
    service: ExperimentService = Depends(get_experiment_service),
) -> dict[str, object]:
    allowed_user_ids = service.get_presentation_user_ids()
    if user_id not in allowed_user_ids:
        return {
            "customer_id": user_id,
            "user_id": user_id,
            "is_comparable": False,
            "reason": "This user is not part of the locked 10-user presentation set.",
            "error": "This user is not part of the locked 10-user presentation set.",
            "allowed_user_ids": allowed_user_ids,
        }

    evaluation_base = service.get_evaluation_base_row(user_id)
    cf_result = service._normalize_saved_method_result(
        service._load_saved_method_result(service.settings.cf_output_path, user_id)
    )
    agentic_result = service._normalize_saved_method_result(
        service._load_saved_method_result(service.settings.agentic_output_path, user_id)
    )
    if cf_result is None:
        return {
            "customer_id": user_id,
            "user_id": user_id,
            "is_comparable": False,
            "reason": "CF result is missing for this user",
            "error": "CF result is missing for this user",
            "allowed_user_ids": allowed_user_ids,
        }
    if agentic_result is None:
        return {
            "customer_id": user_id,
            "user_id": user_id,
            "is_comparable": False,
            "reason": "Agentic result is missing for this user",
            "error": "Agentic result is missing for this user",
            "allowed_user_ids": allowed_user_ids,
        }

    return {
        "customer_id": user_id,
        "user_id": user_id,
        "is_comparable": True,
        "reason": None,
        "error": None,
        "allowed_user_ids": allowed_user_ids,
        "ground_truth_article_id": evaluation_base["ground_truth_article_id"],
        "training_history_count": int(evaluation_base["train_count"]),
        "training_history_preview": [],
        "evaluation_base": evaluation_base,
        "cf": {
            "customer_id": cf_result["customer_id"],
            "method": cf_result["method"],
            "candidate_pool_size": cf_result["candidate_pool_size"],
            "ground_truth_article_id": cf_result["ground_truth_article_id"],
            "hit_result": cf_result["hit_result"],
            "hit_at_5": cf_result["hit_at_5"],
            "hit_label": cf_result["hit_label"],
            "explanation": cf_result["explanation"],
            "hit_explanation": cf_result["hit_explanation"],
            "top_5_article_ids": cf_result["top_5_article_ids"],
            "top_5_recommendations": cf_result["top_5_recommendations"],
            "recommendations": cf_result["top_5_recommendations"],
            "validation": cf_result["validation"],
            "invalid_reason": cf_result["invalid_reason"],
        },
        "agentic": {
            "customer_id": agentic_result["customer_id"],
            "method": agentic_result["method"],
            "candidate_pool_size": agentic_result["candidate_pool_size"],
            "ground_truth_article_id": agentic_result["ground_truth_article_id"],
            "hit_result": agentic_result["hit_result"],
            "hit_at_5": agentic_result["hit_at_5"],
            "hit_label": agentic_result["hit_label"],
            "explanation": agentic_result["explanation"],
            "hit_explanation": agentic_result["hit_explanation"],
            "top_5_article_ids": agentic_result["top_5_article_ids"],
            "top_5_recommendations": agentic_result["top_5_recommendations"],
            "recommendations": agentic_result["top_5_recommendations"],
            "validation": agentic_result["validation"],
            "invalid_reason": agentic_result["invalid_reason"],
        },
    }
