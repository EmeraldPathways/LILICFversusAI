from __future__ import annotations

import pandas as pd

from app.services.data_service import DataService


def test_leave_one_out_split_uses_last_purchase_as_ground_truth(isolated_env, sample_interactions: pd.DataFrame):
    service = DataService(isolated_env)

    train_df, test_df, boundary = service.create_leave_one_out_split(sample_interactions)

    assert boundary == "leave_one_out"
    assert len(train_df) == len(sample_interactions["customer_id"].unique()) * 3
    assert len(test_df) == len(sample_interactions["customer_id"].unique())
    assert test_df.sort_values("customer_id")["article_id"].tolist() == ["a4", "a6", "a1"]
    assert "a4" not in train_df[train_df["customer_id"] == "u1"]["article_id"].tolist()


def test_leave_one_out_split_excludes_users_with_fewer_than_two_purchases(isolated_env):
    service = DataService(isolated_env)
    interactions = pd.DataFrame(
        [
            ["u1", "a1", "Top", "Garment Upper body", "Black", "Solid", "Top 1", "2024-01-01"],
            ["u1", "a2", "Top", "Garment Upper body", "Black", "Solid", "Top 2", "2024-01-02"],
            ["u2", "b1", "Dress", "Garment Full body", "Blue", "Solid", "Dress 1", "2024-01-03"],
        ],
        columns=[
            "customer_id",
            "article_id",
            "product_type",
            "product_group",
            "colour",
            "appearance",
            "product_name",
            "transaction_date",
        ],
    )

    train_df, test_df, _ = service.create_leave_one_out_split(interactions)

    assert set(train_df["customer_id"]) == {"u1"}
    assert set(test_df["customer_id"]) == {"u1"}
