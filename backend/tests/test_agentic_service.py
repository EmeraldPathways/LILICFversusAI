from __future__ import annotations

import pandas as pd

from app.services.agentic_service import AgenticRecommendationService


def test_three_agent_pipeline_returns_profile_candidates_and_ranked_output(
    isolated_env, sample_interactions: pd.DataFrame
):
    train_df = sample_interactions.groupby("customer_id", group_keys=False).apply(lambda group: group.iloc[:-1]).reset_index(drop=True)
    catalog_df = sample_interactions.copy()
    service = AgenticRecommendationService(isolated_env)

    result = service.run_three_agent_pipeline("u1", "I only want black dresses", train_df, catalog_df)

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


def test_agentic_candidate_pool_keeps_required_ground_truth_from_full_catalog(isolated_env):
    train_df = pd.DataFrame(
        [
            ["u1", "a1", "Top", "Garment Upper body", "Black", "Solid", "Top A", "Top desc", "img1"],
            ["u1", "a2", "Dress", "Garment Full body", "Blue", "Solid", "Dress A", "Dress desc", "img2"],
        ],
        columns=[
            "customer_id",
            "article_id",
            "product_type",
            "product_group",
            "colour",
            "appearance",
            "product_name",
            "product_description",
            "image_url",
        ],
    )
    catalog_df = pd.concat(
        [
            train_df,
            pd.DataFrame(
                [
                    ["u2", "0000000009", "Boots", "Shoes", "Red", "Patterned", "Boot A", "Boot desc", "img9"],
                ],
                columns=train_df.columns,
            ),
        ],
        ignore_index=True,
    )
    user_profile = {
        "user_id": "u1",
        "preferred_product_type_name_values": [{"value": "Top", "weight": 1.0}],
        "preferred_product_group_name_values": [{"value": "Garment Upper body", "weight": 1.0}],
        "preferred_colour_group_name_values": [{"value": "Black", "weight": 1.0}],
        "preferred_graphical_appearance_name_values": [{"value": "Solid", "weight": 1.0}],
        "soft_preferences": [],
        "hard_constraints": {},
        "preference_summary": "",
    }
    service = AgenticRecommendationService(isolated_env)

    candidates = service.retrieve_candidate_products(
        user_profile,
        train_df,
        catalog_df,
        required_article_ids={"0000000009"},
    )

    assert any(candidate["article_id"] == "0000000009" for candidate in candidates)
