from __future__ import annotations

import pandas as pd

from app.services.cf_service import CollaborativeFilteringService


def test_cf_excludes_user_history_and_returns_top_n(isolated_env, sample_interactions: pd.DataFrame):
    train_df = sample_interactions.iloc[:9].copy()
    service = CollaborativeFilteringService(isolated_env)
    matrix = service._build_user_item_matrix(train_df)
    metadata = service._article_metadata(train_df)
    user_history = train_df.groupby("customer_id")["article_id"].agg(set).to_dict()

    results = service.recommend_for_user("u1", matrix, metadata, user_history)

    assert results
    assert all(item["article_id"] not in {"a1", "a2", "a3"} for item in results)
    assert results[0]["model"] == "collaborative_filtering"

