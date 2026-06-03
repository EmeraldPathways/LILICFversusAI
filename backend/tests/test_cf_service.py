from __future__ import annotations

import pandas as pd

from app.services.cf_service import CollaborativeFilteringService


def test_cf_excludes_user_history_and_returns_top_n(isolated_env, sample_interactions: pd.DataFrame):
    train_df = sample_interactions.iloc[:9].copy()
    catalog_df = sample_interactions.copy()
    service = CollaborativeFilteringService(isolated_env)
    matrix = service._build_user_item_matrix(train_df)
    metadata = service._article_metadata(catalog_df)
    user_history = train_df.groupby("customer_id")["article_id"].agg(set).to_dict()

    results = service.recommend_for_user("u1", matrix, metadata, user_history)

    assert results
    assert all(item["article_id"] not in {"a1", "a2", "a3"} for item in results)
    assert results[0]["model"] == "collaborative_filtering"


def test_cf_candidate_space_can_include_catalog_items_missing_from_train(isolated_env):
    train_df = pd.DataFrame(
        [
            ["u1", "a1", "Top", "Garment Upper body", "Black", "Solid", "Top A"],
            ["u1", "a2", "Dress", "Garment Full body", "Blue", "Solid", "Dress A"],
            ["u2", "a1", "Top", "Garment Upper body", "Black", "Solid", "Top A"],
            ["u2", "a3", "Skirt", "Garment Lower body", "Blue", "Solid", "Skirt A"],
        ],
        columns=[
            "customer_id",
            "article_id",
            "product_type",
            "product_group",
            "colour",
            "appearance",
            "product_name",
        ],
    )
    catalog_df = pd.concat(
        [
            train_df,
            pd.DataFrame(
                [
                    ["u3", "0000000004", "Boots", "Shoes", "Black", "Solid", "Boot A"],
                ],
                columns=train_df.columns,
            ),
        ],
        ignore_index=True,
    )
    service = CollaborativeFilteringService(isolated_env)
    matrix = service._build_user_item_matrix(train_df)
    metadata = service._article_metadata(catalog_df)
    user_history = train_df.groupby("customer_id")["article_id"].agg(set).to_dict()

    results = service.recommend_for_user("u1", matrix, metadata, user_history)

    assert any(item["article_id"] == "0000000004" for item in results)
