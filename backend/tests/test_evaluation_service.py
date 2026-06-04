from __future__ import annotations

import json

import pandas as pd

from app.services.evaluation_service import EvaluationService


def test_evaluation_metrics_from_fixture(isolated_env, sample_interactions: pd.DataFrame):
    train_df = sample_interactions.groupby("customer_id", group_keys=False).apply(lambda group: group.iloc[:-1]).reset_index(drop=True)
    test_df = sample_interactions.groupby("customer_id", group_keys=False).tail(1).reset_index(drop=True)
    catalog_df = sample_interactions.copy()
    cf_recommendations = {
        "u1": [
            {
                "article_id": "a4",
                "product_name": "Oxford Shirt",
                "product_type": "Shirt",
                "product_group": "Garment Upper body",
                "colour": "Blue",
                "appearance": "Solid",
                "score": 0.8,
                "model": "collaborative_filtering",
            }
        ]
    }
    agentic_recommendations = {
        "u1": [
            {
                "article_id": "a4",
                "product_name": "Oxford Shirt",
                "product_type": "Shirt",
                "product_group": "Garment Upper body",
                "colour": "Blue",
                "appearance": "Solid",
                "score": 0.91,
                "model": "agentic_ai_framework",
                "reason": "Recommended because the blue shirt fits the user's upper-body preference and solid casual style.",
            }
        ]
    }

    metrics = EvaluationService(isolated_env).evaluate(
        train_df,
        test_df,
        catalog_df,
        cf_recommendations,
        agentic_recommendations,
        selected_user_ids=["u1"],
    )

    assert metrics["collaborative_filtering"]["hit_at_5"] == 1.0
    assert metrics["agentic_ai_framework"]["hit_at_5"] == 1.0
    assert metrics["total_selected_users"] == 1
    assert metrics["valid_evaluation_users"] == 1
    assert metrics["invalid_evaluation_users"] == 0
    assert metrics["cf_hits_count"] == 1
    assert metrics["agentic_hits_count"] == 1
    assert metrics["cf_miss_count"] == 0
    assert metrics["agentic_miss_count"] == 0
    assert metrics["evaluated_user_ids"] == ["u1"]


def test_evaluation_metrics_exclude_invalid_users_and_write_invalid_user_artifact(
    isolated_env,
    sample_interactions: pd.DataFrame,
):
    train_df = sample_interactions.groupby("customer_id", group_keys=False).apply(lambda group: group.iloc[:-1]).reset_index(drop=True)
    test_df = sample_interactions.groupby("customer_id", group_keys=False).tail(1).reset_index(drop=True)
    catalog_df = sample_interactions[sample_interactions["article_id"] != "a1"].copy()
    cf_recommendations = {
        "u1": [{"article_id": "a4"}],
        "u3": [{"article_id": "a1"}],
    }
    agentic_recommendations = {
        "u1": [{"article_id": "a4"}],
        "u3": [{"article_id": "a1"}],
    }

    metrics = EvaluationService(isolated_env).evaluate(
        train_df,
        test_df,
        catalog_df,
        cf_recommendations,
        agentic_recommendations,
        selected_user_ids=["u1", "u3"],
    )

    assert metrics["total_selected_users"] == 2
    assert metrics["valid_evaluation_users"] == 1
    assert metrics["invalid_evaluation_users"] == 1
    assert metrics["collaborative_filtering"]["hit_at_5"] == 1.0
    assert metrics["agentic_ai_framework"]["hit_at_5"] == 1.0
    assert metrics["cf_miss_count"] == 0
    assert metrics["agentic_miss_count"] == 0
    assert metrics["excluded_user_ids_with_reasons"] == [
        {
            "user_id": "u3",
            "reasons": ["ground_truth_missing_from_catalog", "ground_truth_not_in_candidate_pool"],
        }
    ]

    invalid_users = json.loads(isolated_env.invalid_evaluation_users_path.read_text(encoding="utf-8"))
    assert invalid_users == [
        {
            "user_id": "u3",
            "reasons": ["ground_truth_missing_from_catalog", "ground_truth_not_in_candidate_pool"],
        }
    ]


def test_build_evaluation_base_table_generates_shared_candidate_pool_and_validation_report(
    isolated_env,
    sample_interactions: pd.DataFrame,
):
    train_df = sample_interactions.groupby("customer_id", group_keys=False).apply(lambda group: group.iloc[:-1]).reset_index(drop=True)
    test_df = sample_interactions.groupby("customer_id", group_keys=False).tail(1).reset_index(drop=True)
    catalog_df = sample_interactions.copy()

    service = EvaluationService(isolated_env)
    base_rows = service.build_evaluation_base_table(
        train_df=train_df,
        test_df=test_df,
        catalog_df=catalog_df,
        selected_ui_customer_ids=["u1", "u2"],
    )

    assert isolated_env.evaluation_base_table_path.exists()
    assert isolated_env.evaluation_base_table_json_path.exists()
    assert isolated_env.evaluation_validation_report_path.exists()
    assert base_rows["u1"]["ground_truth_article_id"] == "a4"
    assert base_rows["u1"]["ground_truth_in_candidate_pool"] is True
    assert base_rows["u1"]["is_valid_for_evaluation"] is True
    assert base_rows["u1"]["candidate_pool_article_ids"]


def test_load_metrics_normalizes_legacy_metrics_payload(isolated_env):
    legacy_metrics = {
        "collaborative_filtering": {"hit_at_5": 0.0},
        "agentic_ai_framework": {"hit_at_5": 0.15},
        "total_selected_users": 20,
        "valid_evaluation_users": 20,
        "invalid_evaluation_users": 0,
        "evaluated_users": 20,
        "cf_hit_at_5": 0.0,
        "agentic_hit_at_5": 0.15,
        "cf_hits_count": 0,
        "agentic_hits_count": 3,
        "evaluated_user_ids": ["u1", "u2"],
        "excluded_user_ids_with_reasons": [],
        "generated_at": "2026-06-04T00:00:00+00:00",
    }
    isolated_env.metrics_path.write_text(json.dumps(legacy_metrics, indent=2), encoding="utf-8")

    metrics = EvaluationService(isolated_env).load_metrics()

    assert metrics["completed_valid_users"] == 20
    assert metrics["cf_miss_count"] == 20
    assert metrics["agentic_miss_count"] == 17
