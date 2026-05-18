from __future__ import annotations

import pandas as pd

from app.services.agentic_service import AgenticRecommendationService


def test_agentic_scoring_uses_expected_fields(isolated_env, sample_interactions: pd.DataFrame):
    train_df = sample_interactions.iloc[:9].copy()
    service = AgenticRecommendationService(isolated_env)
    user_profile = {
        "user_id": "u1",
        "inferred_intent": "casual daily clothing",
        "preferred_categories": ["Garment Upper body"],
        "preferred_product_types": ["Shirt", "Top"],
        "preferred_colours": ["White", "Beige", "Blue"],
        "preferred_appearance": ["Solid", "Plain"],
        "shopping_context": "daily wear",
    }
    candidates = service.retrieve_candidate_products(user_profile, train_df)

    scored = service.score_candidates(user_profile, candidates, train_df)

    assert scored
    assert {"intent_match", "preference_alignment", "product_relevance", "diversity", "behavioural_signal"} <= set(scored[0])
    assert scored[0]["model"] == "agentic_ai_framework"


def test_feedback_updates_weights(isolated_env):
    service = AgenticRecommendationService(isolated_env)
    weights = service.adapt_from_feedback("u1", "a1", "add_to_cart")

    assert weights["product_type_weight"] > 1.0
    assert weights["appearance_weight"] > 1.0

