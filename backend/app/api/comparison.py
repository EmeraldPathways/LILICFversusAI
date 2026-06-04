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
    completed_rows = service.load_completed_evaluation_users() or service.build_completed_evaluation_users_report()
    completed_row = next((row for row in completed_rows if row["customer_id"] == user_id), None)
    if completed_row is not None and not completed_row["included_in_metrics"]:
        return {
            "customer_id": user_id,
            "user_id": user_id,
            "is_comparable": False,
            "reason": completed_row["excluded_reason"] or "This user is not part of the completed evaluation set.",
        }

    train_df = service.data_service.load_train()
    evaluation_base = service.get_evaluation_base_row(user_id)
    cf_result = service.build_cf_result(user_id)
    agentic_result = service.build_agentic_result(user_id)

    return {
        "customer_id": user_id,
        "user_id": user_id,
        "is_comparable": True,
        "reason": None,
        "ground_truth_article_id": evaluation_base["ground_truth_article_id"],
        "training_history_count": int((train_df["customer_id"] == user_id).sum()),
        "training_history_preview": service.get_training_history_preview(user_id, train_df),
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
