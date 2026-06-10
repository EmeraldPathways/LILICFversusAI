from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from fastapi import Query

from app.api.experiment import get_experiment_service
from app.config import Settings
from app.models.schemas import MetricsResponse
from app.services.experiment_service import ExperimentService

router = APIRouter(tags=["metrics"])


@router.get("/metrics", response_model=MetricsResponse)
def get_metrics(
    mode: str = Query(default=Settings.LEGACY_DEBUG_EXPERIMENT_MODE),
    service: ExperimentService = Depends(get_experiment_service),
) -> dict[str, object]:
    metrics = service.evaluation_service.load_metrics()
    if mode == service.settings.SVD_TOP10_EXPERIMENT_MODE:
        formal_metrics_path = service.settings.experiment_artifact_path(mode, "metrics")
        if formal_metrics_path.exists():
            return json.loads(formal_metrics_path.read_text(encoding="utf-8"))

        summary_path = service.settings.metric_summary_top10_100_json_path
        if summary_path.exists():
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            return {
                "svd_matrix_factorization": summary["svd"],
                "agentic_ai_framework": summary["agentic"],
                "business_mapping": {
                    "hit_rate_at_10": "Potential CTR improvement",
                    "ndcg_at_10": "Ranking quality for held-out purchases",
                    "intra_list_diversity_at_10": "Assortment breadth within the top-10 list",
                },
                "evaluated_users": summary["evaluation_scope"]["valid_evaluated_users"],
                "generated_at": None,
            }
    if metrics is None:
        raise FileNotFoundError("Run the experiment first to generate evaluation metrics.")
    return metrics
