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
    agentic_trace = service.agentic_service.load_traces()

    train_df = service.data_service.load_train()

    if user_id not in cf_payload:
        matrix = service.cf_service._build_user_item_matrix(train_df)
        metadata = service.cf_service._article_metadata(train_df)
        user_history = train_df.groupby("customer_id")["article_id"].agg(set).to_dict()
        cf_payload[user_id] = service.cf_service.recommend_for_user(user_id, matrix, metadata, user_history)
        service.settings.cf_output_path.write_text(json.dumps(cf_payload, indent=2), encoding="utf-8")

    if user_id not in agentic_payload or user_id not in agentic_trace:
        recommendations, trace = service.agentic_service.generate_for_user(user_id, train_df)
        agentic_payload[user_id] = recommendations
        agentic_trace[user_id] = trace
        service.settings.agentic_output_path.write_text(
            json.dumps(agentic_payload, indent=2),
            encoding="utf-8",
        )
        service.settings.agentic_trace_path.write_text(
            json.dumps(agentic_trace, indent=2),
            encoding="utf-8",
        )

    return {
        "user_id": user_id,
        "cf_recommendations": cf_payload.get(user_id, []),
        "agentic_recommendations": agentic_payload.get(user_id, []),
        "agentic_process": agentic_trace.get(user_id, []),
    }
