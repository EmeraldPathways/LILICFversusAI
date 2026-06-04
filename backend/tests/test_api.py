from __future__ import annotations

import json

import pandas as pd

from tests.conftest import write_processed_artifacts


def test_setup_endpoint(client, isolated_env, sample_interactions: pd.DataFrame):
    write_processed_artifacts(isolated_env, sample_interactions)

    response = client.get("/experiment/setup")

    assert response.status_code == 200
    payload = response.json()
    assert payload["presentation_mode"] is True
    assert payload["user_selection_method"] == "completed_evaluation_users_included_in_metrics"
    assert payload["selected_user_ids"] == ["u1"]
    assert payload["split_method"] == "Leave-one-out next-item evaluation"
    assert payload["evaluation_metrics"] == ["Hit@5"]
    assert payload["completed_comparable_user_ids"] == ["u1"]
    assert payload["completed_comparable_user_count"] == 1
    assert payload["available_user_ids"] == ["u1"]
    assert payload["valid_completed_user_count"] == 1
    assert payload["presentation_user_count"] == 1
    assert payload["valid_evaluation_users"][0]["customer_id"] == "u1"
    assert payload["max_valid_eval_users"] == 10
    assert payload["summary"]["sample_user_ids"] == ["u1"]
    assert payload["summary"]["evaluated_user_ids"] == ["u1"]


def test_metrics_endpoint(client, isolated_env, sample_interactions: pd.DataFrame):
    write_processed_artifacts(isolated_env, sample_interactions)
    isolated_env.metrics_path.write_text(
        json.dumps(
            {
                "collaborative_filtering": {"hit_at_5": 0.1},
                "agentic_ai_framework": {"hit_at_5": 0.2},
                "total_selected_users": 3,
                "valid_evaluation_users": 1,
                "invalid_evaluation_users": 2,
                "evaluated_users": 1,
                "completed_valid_users": 1,
                "cf_hit_at_5": 0.1,
                "agentic_hit_at_5": 0.2,
                "cf_hits_count": 1,
                "agentic_hits_count": 1,
                "cf_miss_count": 0,
                "agentic_miss_count": 0,
                "evaluated_user_ids": ["u1"],
                "excluded_user_ids_with_reasons": [
                    {"user_id": "u2", "reasons": ["missing_cf_recommendations"]},
                    {"user_id": "u3", "reasons": ["ground_truth_not_in_candidate_pool"]},
                ],
                "generated_at": "2026-01-01T00:00:00+00:00",
            }
        ),
        encoding="utf-8",
    )

    response = client.get("/metrics")

    assert response.status_code == 200
    payload = response.json()
    assert payload["presentation_mode"] is True
    assert payload["user_scope"] == "10 users from completed_evaluation_users.json where included_in_metrics=true"
    assert payload["agentic_ai_framework"]["hit_at_5"] == 0.0
    assert payload["total_selected_users"] == 1
    assert payload["invalid_evaluation_users"] == 0
    assert payload["completed_valid_users"] == 1
    assert payload["cf_miss_count"] == 0
    assert payload["agentic_miss_count"] == 1
    assert payload["legacy_20_user_metrics"]["agentic_ai_framework"]["hit_at_5"] == 0.2


def test_cf_recommendation_endpoint_returns_ground_truth_and_hit_at_5(client, isolated_env, sample_interactions: pd.DataFrame):
    write_processed_artifacts(isolated_env, sample_interactions)

    response = client.get("/recommendations/cf/u1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["customer_id"] == "u1"
    assert payload["method"] == "cf"
    assert payload["ground_truth_article_id"] == "a4"
    assert payload["training_history_count"] == 3
    assert "top_5_recommendations" in payload
    assert "hit_at_5" in payload
    assert payload["hit_at_5"] == 1
    assert payload["hit_label"] == "Hit"
    assert payload["hit_explanation"] == "Ground truth item found at rank 1"
    assert payload["top_5_article_ids"][0] == "a4"
    assert payload["hit_result"]["hit_label"] == "Hit"
    assert payload["validation"]["evaluation_base_used"] is True


def test_agentic_run_endpoint_returns_three_agent_outputs(client, isolated_env, sample_interactions: pd.DataFrame):
    write_processed_artifacts(isolated_env, sample_interactions)

    response = client.post(
        "/recommendations/agentic/run",
        json={"user_id": "u1", "user_request": "I only want black dresses"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["customer_id"] == "u1"
    assert payload["method"] == "agentic"
    assert payload["ground_truth_article_id"] == "a4"
    assert payload["preference_profile"]["hard_constraints"]["colour_group_name"] == "Black"
    assert "candidate_evidence_set" in payload
    assert "top_5_recommendations" in payload
    assert "hit_at_5" in payload
    assert isinstance(payload["hit_at_5"], int)
    assert payload["hit_label"] in {"Hit", "Miss"}
    assert isinstance(payload["hit_explanation"], str)
    assert len(payload["top_5_article_ids"]) <= 5
    assert payload["hit_result"]["hit_label"] in {"Hit", "Miss"}
    assert payload["validation"]["evaluation_base_used"] is True


def test_comparison_endpoint_returns_both_model_outputs(client, isolated_env, sample_interactions: pd.DataFrame):
    write_processed_artifacts(isolated_env, sample_interactions)

    response = client.get("/comparison/u1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["customer_id"] == "u1"
    assert payload["ground_truth_article_id"] == "a4"
    assert payload["evaluation_base"]["customer_id"] == "u1"
    assert payload["evaluation_base"]["ground_truth_in_candidate_pool"] is True
    assert payload["allowed_user_ids"] == ["u1"]
    assert "cf" in payload
    assert "agentic" in payload
    assert payload["cf"]["hit_at_5"] == 1
    assert payload["cf"]["hit_label"] == "Hit"
    assert payload["cf"]["hit_explanation"] == "Ground truth item found at rank 1"
    assert payload["cf"]["top_5_article_ids"][0] == "a4"
    assert payload["agentic"]["hit_at_5"] == 0
    assert payload["agentic"]["hit_label"] == "Miss"
    assert payload["agentic"]["hit_explanation"] == "Ground truth item not found in Top 5"
    assert payload["cf"]["validation"]["same_candidate_pool_source"] is True
    assert payload["agentic"]["validation"]["same_candidate_pool_source"] is True


def test_comparison_endpoint_returns_agentic_validation_block(
    client,
    isolated_env,
    sample_interactions: pd.DataFrame,
):
    write_processed_artifacts(isolated_env, sample_interactions)

    response = client.get("/comparison/u1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["agentic"]["customer_id"] == "u1"
    assert payload["agentic"]["validation"]["evaluation_base_used"] is True
    assert payload["agentic"]["validation"]["same_candidate_pool_source"] is True


def test_comparison_endpoint_returns_non_comparable_payload_for_excluded_user(
    client,
    isolated_env,
    sample_interactions: pd.DataFrame,
):
    write_processed_artifacts(isolated_env, sample_interactions)

    response = client.get("/comparison/u2")

    assert response.status_code == 200
    payload = response.json()
    assert payload["customer_id"] == "u2"
    assert payload["is_comparable"] is False
    assert payload["reason"] == "This user is not part of the locked 10-user presentation set."
    assert payload["error"] == "This user is not part of the locked 10-user presentation set."
    assert payload["allowed_user_ids"] == ["u1"]


def test_completed_evaluation_users_debug_endpoint_returns_counts(
    client,
    isolated_env,
    sample_interactions: pd.DataFrame,
):
    write_processed_artifacts(isolated_env, sample_interactions)

    response = client.get("/debug/comparable-users")

    assert response.status_code == 200
    payload = response.json()
    assert payload["base_valid_user_count"] == 2
    assert payload["completed_comparable_user_count"] == 1
    assert payload["completed_comparable_user_ids"] == ["u1"]
    assert payload["excluded_users"] == [
        {"customer_id": "u2", "excluded_reason": "CF result is missing for this user"}
    ]


def test_presentation_users_debug_endpoint_returns_locked_subset(
    client,
    isolated_env,
    sample_interactions: pd.DataFrame,
):
    write_processed_artifacts(isolated_env, sample_interactions)

    response = client.get("/debug/presentation-users")

    assert response.status_code == 200
    payload = response.json()
    assert payload["presentation_user_count"] == 1
    assert payload["source_file"] == "completed_evaluation_users.json"
    assert payload["filter"] == "included_in_metrics=true"
    assert payload["users"][0]["customer_id"] == "u1"


def test_debug_evaluation_endpoint_returns_full_trace(client, isolated_env, sample_interactions: pd.DataFrame):
    write_processed_artifacts(isolated_env, sample_interactions)

    response = client.get("/debug/evaluation/u1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["customer_id"] == "u1"
    assert payload["ground_truth_article_ids"] == ["a4"]
    assert payload["cf"]["top_5_article_ids"][0] == "a4"
    assert payload["cf"]["hit_label"] == "Hit"
    assert payload["agentic"]["candidate_pool_contains_ground_truth"] is True
    assert payload["validation"]["is_valid"] is True
    assert payload["validation"]["reasons"] == []


def test_evaluation_base_debug_endpoint_returns_canonical_base_row(
    client,
    isolated_env,
    sample_interactions: pd.DataFrame,
):
    write_processed_artifacts(isolated_env, sample_interactions)

    response = client.get("/debug/evaluation-base/u1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["customer_id"] == "u1"
    assert payload["train_count"] == 3
    assert payload["ground_truth_article_id"] == "a4"
    assert payload["ground_truth_in_candidate_pool"] is True
    assert "candidate_pool_article_ids" in payload
