from __future__ import annotations

import pandas as pd

from app.services.data_service import DataService


def test_time_based_split_preserves_order(isolated_env, sample_interactions: pd.DataFrame):
    service = DataService(isolated_env)
    train_df, test_df, boundary_date = service.create_time_based_split(sample_interactions)

    assert len(train_df) == 9
    assert len(test_df) == 3
    assert boundary_date == "2024-01-10"
    assert train_df.iloc[0]["transaction_date"] == "2024-01-01"
    assert test_df.iloc[0]["transaction_date"] == "2024-01-11"


def test_dense_user_sampling_prefers_repeated_histories(isolated_env):
    service = DataService(isolated_env)
    interactions = pd.DataFrame(
        [
            ["u_dense_1", "a1", "Top", "Garment Upper body", "Black", "Solid", "Top 1", "2024-01-01"],
            ["u_dense_1", "a2", "Top", "Garment Upper body", "Black", "Solid", "Top 2", "2024-01-02"],
            ["u_dense_1", "a3", "Top", "Garment Upper body", "Black", "Solid", "Top 3", "2024-01-03"],
            ["u_dense_1", "a4", "Top", "Garment Upper body", "Black", "Solid", "Top 4", "2024-01-04"],
            ["u_dense_2", "b1", "Dress", "Garment Full body", "Blue", "Solid", "Dress 1", "2024-01-05"],
            ["u_dense_2", "b2", "Dress", "Garment Full body", "Blue", "Solid", "Dress 2", "2024-01-06"],
            ["u_dense_2", "b3", "Dress", "Garment Full body", "Blue", "Solid", "Dress 3", "2024-01-07"],
            ["u_sparse_1", "c1", "Skirt", "Garment Lower body", "White", "Stripe", "Skirt 1", "2024-01-08"],
            ["u_sparse_2", "d1", "Skirt", "Garment Lower body", "White", "Stripe", "Skirt 2", "2024-01-09"],
            ["u_sparse_3", "e1", "Skirt", "Garment Lower body", "White", "Stripe", "Skirt 3", "2024-01-10"],
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
    isolated_env.sample_size = 7

    sampled = service._sample_dense_user_histories(interactions)

    assert len(sampled) == 7
    assert set(sampled["customer_id"]) == {"u_dense_1", "u_dense_2"}
    assert sampled["customer_id"].value_counts().to_dict() == {"u_dense_1": 4, "u_dense_2": 3}


def test_dense_user_sampling_caps_single_user_domination(isolated_env):
    service = DataService(isolated_env)
    rows = []
    for index in range(12):
        rows.append(
            [
                "u_heavy",
                f"a{index}",
                "Top",
                "Garment Upper body",
                "Black",
                "Solid",
                f"Heavy {index}",
                f"2024-01-{index + 1:02d}",
            ]
        )
    for user_number in range(1, 5):
        for interaction_number in range(3):
            rows.append(
                [
                    f"u_repeat_{user_number}",
                    f"r{user_number}{interaction_number}",
                    "Dress",
                    "Garment Full body",
                    "Blue",
                    "Solid",
                    f"Repeat {user_number}-{interaction_number}",
                    f"2024-02-{len(rows) + 1:02d}",
                ]
            )
        columns = [
            "customer_id",
            "article_id",
            "product_type",
            "product_group",
            "colour",
            "appearance",
            "product_name",
            "transaction_date",
        ]
    interactions = pd.DataFrame(rows, columns=columns)
    isolated_env.sample_size = 12
    isolated_env.max_eval_users = 2

    sampled = service._sample_dense_user_histories(interactions)

    assert len(sampled) == 12
    assert sampled["customer_id"].nunique() > 1
    assert sampled["customer_id"].value_counts()["u_heavy"] < 12
