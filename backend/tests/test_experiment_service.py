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


def test_get_completed_comparable_user_ids_filters_for_complete_comparable_rows(
    isolated_env,
    monkeypatch,
):
    service = ExperimentService(
        settings=isolated_env,
        data_service=DataService(isolated_env),
        cf_service=CollaborativeFilteringService(isolated_env),
        agentic_service=AgenticRecommendationService(isolated_env),
        evaluation_service=EvaluationService(isolated_env),
    )
    base_rows = {
        "u1": {
            "customer_id": "u1",
            "is_valid_for_evaluation": True,
            "ground_truth_in_candidate_pool": True,
            "candidate_pool_size": 6,
            "train_article_ids": ["a1"],
            "ground_truth_article_id": "a9",
        },
        "u2": {
            "customer_id": "u2",
            "is_valid_for_evaluation": True,
            "ground_truth_in_candidate_pool": True,
            "candidate_pool_size": 6,
            "train_article_ids": ["a2"],
            "ground_truth_article_id": "a8",
        },
        "u3": {
            "customer_id": "u3",
            "is_valid_for_evaluation": True,
            "ground_truth_in_candidate_pool": True,
            "candidate_pool_size": 5,
            "train_article_ids": ["a3"],
            "ground_truth_article_id": "a7",
        },
    }
    monkeypatch.setattr(service, "load_state", lambda: {"status": "completed"})
    monkeypatch.setattr(service, "get_evaluation_base_row", lambda user_id: base_rows[user_id])
    monkeypatch.setattr(
        service.evaluation_service,
        "load_evaluation_base_table",
        lambda: base_rows,
    )
    monkeypatch.setattr(
        service,
        "build_cf_result",
        lambda user_id: {
            "customer_id": user_id,
            "validation": {
                "same_candidate_pool_source": True,
                "top_5_all_inside_candidate_pool": True,
            },
            "hit_at_5": 1 if user_id == "u1" else 0,
            "top_5_recommendations": [{"article_id": "a1"}] if user_id != "u2" else [],
        },
    )
    monkeypatch.setattr(
        service,
        "build_agentic_result",
        lambda user_id, user_request="": {
            "customer_id": user_id,
            "validation": {
                "same_candidate_pool_source": True,
                "top_5_all_inside_candidate_pool": True,
            },
            "hit_at_5": 1,
            "top_5_recommendations": [{"article_id": "a1"}],
        },
    )

    service.build_completed_evaluation_users_report(
        limit=10,
        base_rows=base_rows,
        allow_generation=True,
    )
    user_ids = service.get_completed_comparable_user_ids(limit=10)

    assert user_ids == ["u1"]
