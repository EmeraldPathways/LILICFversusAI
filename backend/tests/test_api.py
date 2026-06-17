from __future__ import annotations

import json

import pandas as pd

from tests.test_explainability_service import _write_explainability_source_artifacts
from tests.conftest import write_processed_artifacts


def test_setup_endpoint(client, isolated_env, sample_interactions: pd.DataFrame):
    write_processed_artifacts(isolated_env, sample_interactions)

    response = client.get("/experiment/setup")

    assert response.status_code == 200
    payload = response.json()
    assert payload["dataset"] == isolated_env.dataset_name
    assert payload["summary"]["sample_size"] == len(sample_interactions)
    assert payload["summary"]["evaluated_user_ids"] == ["u1"]


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


def test_metrics_endpoint_reads_formal_svd_summary_when_requested(client, isolated_env):
    isolated_env.metric_summary_top10_100_json_path.write_text(
        json.dumps(
            {
                "evaluation_scope": {
                    "valid_evaluated_users": 100,
                    "candidate_pool_size": 100,
                    "top_k": 10,
                    "split_strategy": "leave_one_out",
                    "baseline": "SVD Matrix Factorisation",
                    "comparison_method": "3-Agent Agentic AI",
                },
                "svd": {
                    "hit_rate_at_10": 0.35,
                    "hits_count": 35,
                    "miss_count": 65,
                    "ndcg_at_10": 0.187798,
                    "intra_list_diversity_at_10": 0.75,
                },
                "agentic": {
                    "hit_rate_at_10": 0.38,
                    "hits_count": 38,
                    "miss_count": 62,
                    "ndcg_at_10": 0.196679,
                    "intra_list_diversity_at_10": 0.549185,
                },
            }
        ),
        encoding="utf-8",
    )

    response = client.get("/metrics?mode=svd_top10_experiment")

    assert response.status_code == 200
    payload = response.json()
    assert payload["svd_matrix_factorization"]["ndcg_at_10"] == 0.187798
    assert payload["agentic_ai_framework"]["intra_list_diversity_at_10"] == 0.549185
    assert payload["evaluated_users"] == 100


def test_formal_user_intent_endpoint_reads_saved_preference_profile(client, isolated_env):
    isolated_env.agentic_recommendations_top10_100_json_path.write_text(
        json.dumps(
            [
                {
                    "customer_id": "u1",
                    "preference_profile": {
                        "user_id": "u1",
                        "inferred_intent": "casual tops",
                        "preferred_categories": ["Garment Upper body"],
                        "preferred_product_types": ["Top"],
                        "preferred_colours": ["White"],
                        "preferred_appearance": ["Solid"],
                        "shopping_context": "offline historical preference evaluation",
                    },
                    "top_10_recommendations": [],
                }
            ]
        ),
        encoding="utf-8",
    )

    response = client.get("/users/u1/intent?mode=svd_top10_experiment")

    assert response.status_code == 200
    payload = response.json()
    assert payload["user_id"] == "u1"
    assert payload["inferred_intent"] == "casual tops"


def test_formal_recommendation_comparison_reads_saved_top10_artifacts(client, isolated_env):
    isolated_env.svd_recommendations_top10_100_json_path.write_text(
        json.dumps(
            [
                {
                    "customer_id": "u1",
                    "top_10_recommendations": [
                        {
                            "article_id": "a1",
                            "score": 0.42,
                            "product_type_name": "Top",
                            "product_group_name": "Garment Upper body",
                            "colour_group_name": "White",
                            "graphical_appearance_name": "Solid",
                        }
                    ],
                }
            ]
        ),
        encoding="utf-8",
    )
    isolated_env.agentic_recommendations_top10_100_json_path.write_text(
        json.dumps(
            [
                {
                    "customer_id": "u1",
                    "top_10_recommendations": [
                        {
                            "article_id": "a2",
                            "score": 0.91,
                            "product_type_name": "Blouse",
                            "product_group_name": "Garment Upper body",
                            "colour_group_name": "Blue",
                            "graphical_appearance_name": "Patterned",
                            "recommendation_reason": "Matches the user's saved preference profile.",
                        }
                    ],
                }
            ]
        ),
        encoding="utf-8",
    )

    response = client.get("/recommendations/compare/u1?mode=svd_top10_experiment")

    assert response.status_code == 200
    payload = response.json()
    assert payload["cf_recommendations"][0]["article_id"] == "a1"
    assert payload["cf_recommendations"][0]["product_type"] == "Top"
    assert payload["agentic_recommendations"][0]["article_id"] == "a2"
    assert payload["agentic_recommendations"][0]["reason"] == "Matches the user's saved preference profile."
    assert payload["agentic_process"] == []


def test_recommendation_comparison_includes_agent_process(client, isolated_env, sample_interactions: pd.DataFrame):
    write_processed_artifacts(isolated_env, sample_interactions)

    response = client.get("/recommendations/compare/u1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["agentic_recommendations"][0]["article_id"] == "a5"
    assert payload["agentic_process"][0]["agent"] == "Agent 1"


def test_explainability_endpoint_returns_generated_payload(client, isolated_env):
    _write_explainability_source_artifacts(isolated_env)
    from app.services.explainability_service import ExplainabilityService

    ExplainabilityService(isolated_env).generate_explainability_artifacts(
        artifact_prefix="seed99_robustness",
        output_prefix="seed99",
        sample_size=2,
    )

    response = client.get(
        "/metrics/explainability?mode=svd_top10_experiment&artifact_prefix=seed99_robustness&output_prefix=seed99"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["summary_metrics"]["evidence_coverage_rate"] >= 0
    assert len(payload["examples"]) == 4
    assert payload["case_study"]["customer_id"] == "u1"
    assert payload["limitations"][0].startswith("This explainability audit is offline")


def test_explainability_endpoint_returns_controlled_missing_artifact_message(client, isolated_env):
    response = client.get(
        "/metrics/explainability?mode=svd_top10_experiment&artifact_prefix=seed99_robustness&output_prefix=seed99"
    )

    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "Explainability artifacts not found. Run python -m backend.scripts.run_explainability_audit "
        "--artifact-prefix seed99_robustness --sample-size 100 --output-prefix seed99 first."
    )
