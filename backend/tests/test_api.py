from __future__ import annotations

import json

import pandas as pd

from tests.conftest import write_processed_artifacts


def test_setup_endpoint(client, isolated_env, sample_interactions: pd.DataFrame):
    write_processed_artifacts(isolated_env, sample_interactions)

    response = client.get("/experiment/setup")

    assert response.status_code == 200
    payload = response.json()
    assert payload["dataset"] == isolated_env.dataset_name
    assert payload["summary"]["sample_size"] == len(sample_interactions)


def test_metrics_endpoint(client, isolated_env):
    isolated_env.metrics_path.write_text(
        json.dumps(
            {
                "collaborative_filtering": {
                    "hit_rate_at_10": 0.1,
                    "preference_alignment": 0.5,
                    "diversity": 0.4,
                    "explanation_quality": None,
                    "feedback_adaptability": None,
                },
                "agentic_ai_framework": {
                    "hit_rate_at_10": 0.2,
                    "preference_alignment": 0.6,
                    "diversity": 0.5,
                    "explanation_quality": 0.8,
                    "feedback_adaptability": 0.75,
                },
                "business_mapping": {
                    "hit_rate_at_10": "Potential CTR improvement",
                    "preference_alignment": "Potential CVR improvement",
                    "diversity": "Potential engagement depth improvement",
                },
                "evaluated_users": 1,
                "generated_at": "2026-01-01T00:00:00+00:00",
            }
        ),
        encoding="utf-8",
    )

    response = client.get("/metrics")

    assert response.status_code == 200
    assert response.json()["agentic_ai_framework"]["diversity"] == 0.5
