from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone

import pandas as pd

from app.config import Settings


@dataclass
class EvaluationService:
    settings: Settings

    def evaluate(
        self,
        test_df: pd.DataFrame,
        cf_recommendations: dict[str, list[dict[str, object]]],
        agentic_recommendations: dict[str, list[dict[str, object]]],
    ) -> dict[str, object]:
        truth_map = {
            str(row["customer_id"]): str(row["article_id"])
            for _, row in test_df.iterrows()
        }
        evaluated_users = sorted(
            set(truth_map)
            & set(cf_recommendations)
            & set(agentic_recommendations)
        )

        if not evaluated_users:
            metrics = {
                "collaborative_filtering": {"hit_at_5": 0.0},
                "agentic_ai_framework": {"hit_at_5": 0.0},
                "evaluated_users": 0,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }
            self.settings.metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
            return metrics

        cf_hits = 0
        agentic_hits = 0
        for user_id in evaluated_users:
            truth = truth_map[user_id]
            cf_top_five = [str(item.get("article_id")) for item in cf_recommendations.get(user_id, [])[:5]]
            agentic_top_five = [
                str(item.get("article_id")) for item in agentic_recommendations.get(user_id, [])[:5]
            ]
            cf_hits += int(truth in cf_top_five)
            agentic_hits += int(truth in agentic_top_five)

        metrics = {
            "collaborative_filtering": {"hit_at_5": round(cf_hits / len(evaluated_users), 4)},
            "agentic_ai_framework": {"hit_at_5": round(agentic_hits / len(evaluated_users), 4)},
            "evaluated_users": len(evaluated_users),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        self.settings.metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
        return metrics

    def load_metrics(self) -> dict[str, object] | None:
        if not self.settings.metrics_path.exists():
            return None
        return json.loads(self.settings.metrics_path.read_text(encoding="utf-8"))
