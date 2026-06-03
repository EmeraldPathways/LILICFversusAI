from __future__ import annotations

import json

import pandas as pd

from tests.conftest import write_processed_artifacts


def test_setup_endpoint(client, isolated_env, sample_interactions: pd.DataFrame):
    write_processed_artifacts(isolated_env, sample_interactions)

    response = client.get("/experiment/setup")

    assert response.status_code == 200
    payload = response.json()
    assert payload["split_method"] == "Leave-one-out next-item evaluation"
    assert payload["evaluation_metrics"] == ["Hit@5"]
    assert payload["summary"]["evaluated_user_ids"] == ["u1"]


def test_metrics_endpoint(client, isolated_env):
    isolated_env.metrics_path.write_text(
        json.dumps(
            {
                "collaborative_filtering": {"hit_at_5": 0.1},
                "agentic_ai_framework": {"hit_at_5": 0.2},
                "evaluated_users": 1,
                "generated_at": "2026-01-01T00:00:00+00:00",
            }
        ),
        encoding="utf-8",
    )

    response = client.get("/metrics")

    assert response.status_code == 200
    assert response.json()["agentic_ai_framework"]["hit_at_5"] == 0.2


def test_cf_recommendation_endpoint_returns_ground_truth_and_hit_at_5(client, isolated_env, sample_interactions: pd.DataFrame):
    write_processed_artifacts(isolated_env, sample_interactions)

    response = client.get("/recommendations/cf/u1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ground_truth_article_id"] == "a4"
    assert payload["training_history_count"] == 3
    assert "recommendations" in payload
    assert "hit_at_5" in payload


def test_agentic_run_endpoint_returns_three_agent_outputs(client, isolated_env, sample_interactions: pd.DataFrame):
    write_processed_artifacts(isolated_env, sample_interactions)

    response = client.post(
        "/recommendations/agentic/run",
        json={"user_id": "u1", "user_request": "I only want black dresses"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ground_truth_article_id"] == "a4"
    assert payload["preference_profile"]["hard_constraints"]["colour_group_name"] == "Black"
    assert "candidate_evidence_set" in payload
    assert "final_recommendations" in payload
    assert "hit_at_5" in payload


def test_comparison_endpoint_returns_both_model_outputs(client, isolated_env, sample_interactions: pd.DataFrame):
    write_processed_artifacts(isolated_env, sample_interactions)

    response = client.get("/comparison/u1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ground_truth_article_id"] == "a4"
    assert "cf" in payload
    assert "agentic" in payload
    assert "hit_at_5" in payload["cf"]
    assert "hit_at_5" in payload["agentic"]
