from __future__ import annotations

import json

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
    train_df = service.data_service.load_train()
    test_df = service.data_service.load_test()
    truth_map = service.get_ground_truth_map(test_df)
    if user_id not in truth_map:
        raise FileNotFoundError(f"User {user_id} is not available in the leave-one-out evaluation set.")

    cf_payload = (
        json.loads(service.settings.cf_output_path.read_text(encoding="utf-8"))
        if service.settings.cf_output_path.exists()
        else {}
    )
    if user_id not in cf_payload:
        matrix = service.cf_service._build_user_item_matrix(train_df)
        metadata = service.cf_service._article_metadata(train_df)
        user_history = train_df.groupby("customer_id")["article_id"].agg(set).to_dict()
        cf_payload[user_id] = service.cf_service.recommend_for_user(user_id, matrix, metadata, user_history)
        service.settings.cf_output_path.write_text(json.dumps(cf_payload, indent=2), encoding="utf-8")

    return {
        "user_id": user_id,
        "ground_truth_article_id": truth_map[user_id],
        "hit_at_5": truth_map[user_id] in [item["article_id"] for item in cf_payload.get(user_id, [])[:5]],
        "training_history_count": int((train_df["customer_id"] == user_id).sum()),
        "training_history_preview": service.get_training_history_preview(user_id, train_df),
        "recommendations": cf_payload.get(user_id, [])[:5],
    }


@router.post("/agentic/run", response_model=AgenticRunResponse)
def run_agentic_recommendations(
    payload: RecommendationRunRequest,
    service: ExperimentService = Depends(get_experiment_service),
) -> dict[str, object]:
    train_df = service.data_service.load_train()
    test_df = service.data_service.load_test()
    truth_map = service.get_ground_truth_map(test_df)
    if payload.user_id not in truth_map:
        raise FileNotFoundError(
            f"User {payload.user_id} is not available in the leave-one-out evaluation set."
        )

    result = service.agentic_service.run_three_agent_pipeline(
        payload.user_id,
        payload.user_request,
        train_df,
    )
    final_recommendations = result["final_recommendations"][:5]
    return {
        "user_id": payload.user_id,
        "user_request": payload.user_request,
        "ground_truth_article_id": truth_map[payload.user_id],
        "hit_at_5": truth_map[payload.user_id]
        in [item["article_id"] for item in final_recommendations],
        "training_history_count": int((train_df["customer_id"] == payload.user_id).sum()),
        "training_history_preview": service.get_training_history_preview(payload.user_id, train_df),
        "preference_profile": result["preference_profile"],
        "candidate_evidence_set": result["candidate_evidence_set"],
        "final_recommendations": final_recommendations,
        "process_trace": result["process_trace"],
    }
