from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app


@pytest.fixture(autouse=True)
def isolated_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "OPENAI_API_KEY=test-key",
                "OPENAI_MODEL=test-model",
                "FRONTEND_ORIGIN=http://localhost:3000",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("BACKEND_ENV_FILE", str(env_file))
    get_settings.cache_clear()
    settings = get_settings()
    settings.interactions_path.parent.mkdir(parents=True, exist_ok=True)
    yield settings
    get_settings.cache_clear()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def sample_interactions() -> pd.DataFrame:
    return pd.DataFrame(
        [
            ["u1", "a1", "Shirt", "Garment Upper body", "White", "Solid", "Cotton Shirt", "2024-01-01"],
            ["u1", "a2", "Top", "Garment Upper body", "Beige", "Solid", "Linen Top", "2024-01-03"],
            ["u1", "a3", "Trousers", "Garment Lower body", "Black", "Plain", "Relaxed Trousers", "2024-01-06"],
            ["u2", "a1", "Shirt", "Garment Upper body", "White", "Solid", "Cotton Shirt", "2024-01-02"],
            ["u2", "a4", "Shirt", "Garment Upper body", "Blue", "Solid", "Oxford Shirt", "2024-01-04"],
            ["u2", "a5", "Top", "Garment Upper body", "White", "Patterned", "Jersey Top", "2024-01-07"],
            ["u3", "a2", "Top", "Garment Upper body", "Beige", "Solid", "Linen Top", "2024-01-05"],
            ["u3", "a4", "Shirt", "Garment Upper body", "Blue", "Solid", "Oxford Shirt", "2024-01-08"],
            ["u3", "a6", "Dress", "Garment Full body", "Red", "Patterned", "Summer Dress", "2024-01-10"],
            ["u1", "a4", "Shirt", "Garment Upper body", "Blue", "Solid", "Oxford Shirt", "2024-01-11"],
            ["u2", "a6", "Dress", "Garment Full body", "Red", "Patterned", "Summer Dress", "2024-01-12"],
            ["u3", "a1", "Shirt", "Garment Upper body", "White", "Solid", "Cotton Shirt", "2024-01-13"],
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


def write_processed_artifacts(settings, interactions: pd.DataFrame) -> None:
    interactions.to_csv(settings.interactions_path, index=False)
    split_index = int(len(interactions) * 0.8)
    train_df = interactions.iloc[:split_index].copy()
    test_df = interactions.iloc[split_index:].copy()
    train_df.to_csv(settings.train_path, index=False)
    test_df.to_csv(settings.test_path, index=False)
    settings.summary_path.write_text(
        json.dumps(
            {
                "dataset": settings.dataset_name,
                "sample_size": len(interactions),
                "distinct_users": interactions["customer_id"].nunique(),
                "distinct_products": interactions["article_id"].nunique(),
                "top_product_groups": [{"label": "Garment Upper body", "value": 8}],
                "top_colours": [{"label": "White", "value": 4}],
                "top_appearances": [{"label": "Solid", "value": 8}],
                "train_size": len(train_df),
                "test_size": len(test_df),
                "split_boundary_date": str(train_df["transaction_date"].iloc[-1]),
                "sample_user_ids": ["u1", "u2", "u3"],
            }
        ),
        encoding="utf-8",
    )
