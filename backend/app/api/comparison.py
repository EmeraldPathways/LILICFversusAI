from __future__ import annotations

import json

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

    agentic_result = service.agentic_service.run_three_agent_pipeline(user_id, "", train_df)
    truth = truth_map[user_id]
    cf_recommendations = cf_payload.get(user_id, [])[:5]
    agentic_recommendations = agentic_result["final_recommendations"][:5]

    return {
        "user_id": user_id,
        "ground_truth_article_id": truth,
        "training_history_count": int((train_df["customer_id"] == user_id).sum()),
        "training_history_preview": service.get_training_history_preview(user_id, train_df),
        "cf": {
            "hit_at_5": truth in [item["article_id"] for item in cf_recommendations],
            "recommendations": cf_recommendations,
        },
        "agentic": {
            "hit_at_5": truth in [item["article_id"] for item in agentic_recommendations],
            "recommendations": agentic_recommendations,
        },
    }
