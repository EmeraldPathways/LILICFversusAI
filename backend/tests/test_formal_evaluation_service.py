from __future__ import annotations

import pandas as pd

from app.services.evaluation_service import EvaluationService


def test_formal_top10_metrics_include_hit_rate_ndcg_and_intra_list_diversity(
    isolated_env, sample_interactions: pd.DataFrame
):
    train_df = sample_interactions.iloc[:9].copy()
    test_df = sample_interactions.iloc[9:].copy()
    svd_recommendations = {
        "u1": [
            {
                "article_id": "a4",
                "product_name": "Oxford Shirt",
                "product_type": "Shirt",
                "product_group": "Garment Upper body",
                "colour": "Blue",
                "appearance": "Solid",
                "score": 0.92,
                "model": "svd_matrix_factorization",
            },
            {
                "article_id": "a5",
                "product_name": "Jersey Top",
                "product_type": "Top",
                "product_group": "Garment Upper body",
                "colour": "White",
                "appearance": "Patterned",
                "score": 0.64,
                "model": "svd_matrix_factorization",
            },
        ]
    }
    agentic_recommendations = {
        "u1": [
            {
                "article_id": "a5",
                "product_name": "Jersey Top",
                "product_type": "Top",
                "product_group": "Garment Upper body",
                "colour": "White",
                "appearance": "Patterned",
                "score": 0.95,
                "model": "agentic_ai_framework",
                "reason": "Recommended because the patterned top extends the user's upper-body wardrobe.",
            },
            {
                "article_id": "a4",
                "product_name": "Oxford Shirt",
                "product_type": "Shirt",
                "product_group": "Garment Upper body",
                "colour": "Blue",
                "appearance": "Solid",
                "score": 0.76,
                "model": "agentic_ai_framework",
                "reason": "Recommended because the blue shirt matches the user's solid upper-body preferences.",
            },
        ]
    }

    metrics = EvaluationService(isolated_env).evaluate_top10_experiment(
        train_df, test_df, svd_recommendations, agentic_recommendations
    )

    assert metrics["svd_matrix_factorization"]["hit_rate_at_10"] == 1.0
    assert metrics["svd_matrix_factorization"]["ndcg_at_10"] == 1.0
    assert metrics["agentic_ai_framework"]["intra_list_diversity_at_10"] > 0.0
