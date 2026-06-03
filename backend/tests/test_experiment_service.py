from __future__ import annotations

import pandas as pd

from app.services.agentic_service import AgenticRecommendationService
from app.services.cf_service import CollaborativeFilteringService
from app.services.data_service import DataService
from app.services.evaluation_service import EvaluationService
from app.services.experiment_service import ExperimentService
from tests.conftest import write_processed_artifacts


def test_select_evaluable_users_prefers_users_with_cf_recommendations(isolated_env):
    train_df = pd.DataFrame(
        [
            ["u1", "a1", "Top", "Garment Upper body", "Black", "Solid", "Top A", "desc", "img", "2024-01-01"],
            ["u1", "a2", "Dress", "Garment Full body", "Black", "Solid", "Dress A", "desc", "img", "2024-01-02"],
            ["u2", "a1", "Top", "Garment Upper body", "Black", "Solid", "Top A", "desc", "img", "2024-01-01"],
            ["u2", "a3", "Skirt", "Garment Lower body", "Blue", "Solid", "Skirt A", "desc", "img", "2024-01-02"],
            ["u3", "a4", "Trousers", "Garment Lower body", "Grey", "Solid", "Trouser A", "desc", "img", "2024-01-01"],
            ["u3", "a5", "Blouse", "Garment Upper body", "White", "Solid", "Blouse A", "desc", "img", "2024-01-02"],
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
            "transaction_date",
        ],
    )
    test_df = pd.DataFrame(
        [
            ["u1", "a3"],
            ["u2", "a2"],
            ["u3", "a6"],
        ],
        columns=["customer_id", "article_id"],
    )
    service = ExperimentService(
        settings=isolated_env,
        data_service=DataService(isolated_env),
        cf_service=CollaborativeFilteringService(isolated_env),
        agentic_service=AgenticRecommendationService(isolated_env),
        evaluation_service=EvaluationService(isolated_env),
    )

    user_ids = service._select_evaluable_users(train_df, test_df)

    assert user_ids == ["u1", "u2", "u3"]


def test_run_generates_evaluation_base_table_and_validation_report(
    isolated_env,
    monkeypatch,
    sample_interactions: pd.DataFrame,
):
    service = ExperimentService(
        settings=isolated_env,
        data_service=DataService(isolated_env),
        cf_service=CollaborativeFilteringService(isolated_env),
        agentic_service=AgenticRecommendationService(isolated_env),
        evaluation_service=EvaluationService(isolated_env),
    )

    def fake_preprocess():
        write_processed_artifacts(isolated_env, sample_interactions)
        return service.data_service.load_summary() or {}

    monkeypatch.setattr(service.data_service, "preprocess", fake_preprocess)

    service.run()

    base_table = pd.read_csv(isolated_env.evaluation_base_table_path)
    report = service.evaluation_service.load_validation_report()

    assert "candidate_pool_article_ids" in base_table.columns
    assert "ground_truth_in_candidate_pool" in base_table.columns
    assert "is_valid_for_evaluation" in base_table.columns
    assert "invalid_reason" in base_table.columns
    assert report["valid_evaluation_customers"] >= 1
    assert report["selected_ui_customer_ids"]
