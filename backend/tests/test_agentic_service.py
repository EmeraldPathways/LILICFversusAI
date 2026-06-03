from __future__ import annotations

import pandas as pd

from app.services.agentic_service import AgenticRecommendationService


def test_three_agent_pipeline_returns_profile_candidates_and_ranked_output(
    isolated_env, sample_interactions: pd.DataFrame
):
    train_df = sample_interactions.groupby("customer_id", group_keys=False).apply(lambda group: group.iloc[:-1]).reset_index(drop=True)
    service = AgenticRecommendationService(isolated_env)

    result = service.run_three_agent_pipeline("u1", "I only want black dresses", train_df)

    assert result["preference_profile"]["hard_constraints"]["colour_group_name"] == "Black"
    assert result["preference_profile"]["hard_constraints"]["product_type_name"] == "Dress"
    assert result["candidate_evidence_set"]
    assert len(result["final_recommendations"]) <= 5
    assert result["process_trace"][0]["agent"] == "Preference Agent"


def test_feedback_updates_weights(isolated_env):
    service = AgenticRecommendationService(isolated_env)
    weights = service.adapt_from_feedback("u1", "a1", "add_to_cart")

    assert weights["product_type_weight"] > 1.0
    assert weights["appearance_weight"] > 1.0
