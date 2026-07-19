from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest


RUNNER_PATH = (
    Path(__file__).resolve().parents[1] / "run_experiment1_frozen_replay.py"
)


def load_runner_module():
    spec = importlib.util.spec_from_file_location("experiment1_frozen_replay_runner", RUNNER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load runner module from {RUNNER_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def sample_rows() -> list[dict[str, object]]:
    return [
        {
            "customer_id": "u1",
            "train_article_ids": ["a1", "a2"],
            "ground_truth_article_id": "g1",
            "candidate_pool_article_ids": ["g1"] + [f"c1_{index:03d}" for index in range(99)],
            "candidate_pool_size": 100,
        },
        {
            "customer_id": "u2",
            "train_article_ids": ["b1", "b2"],
            "ground_truth_article_id": "g2",
            "candidate_pool_article_ids": ["g2"] + [f"c2_{index:03d}" for index in range(99)],
            "candidate_pool_size": 100,
        },
        {
            "customer_id": "u3",
            "train_article_ids": ["d1", "d2"],
            "ground_truth_article_id": "g3",
            "candidate_pool_article_ids": ["g3"] + [f"c3_{index:03d}" for index in range(99)],
            "candidate_pool_size": 100,
        },
        {
            "customer_id": "u4",
            "train_article_ids": ["e1", "e2"],
            "ground_truth_article_id": "g4",
            "candidate_pool_article_ids": ["g4"] + [f"c4_{index:03d}" for index in range(99)],
            "candidate_pool_size": 100,
        },
    ]


def test_validate_frozen_rows_accepts_valid_payload():
    runner = load_runner_module()

    report = runner.validate_frozen_rows(sample_rows(), expected_row_count=4)

    assert report["ok"] is True
    assert report["row_count"] == 4
    assert report["unique_customer_id_count"] == 4
    assert report["rows_with_missing_training_history"] == []
    assert report["rows_with_candidate_pool_size_not_100"] == []


def test_select_replay_rows_for_smoke_keeps_first_three_users_in_order():
    runner = load_runner_module()

    selected = runner.select_replay_rows(sample_rows(), sample_size=3)

    assert [row["customer_id"] for row in selected] == ["u1", "u2", "u3"]
    assert selected[0]["candidate_pool_article_ids"][:3] == ["g1", "c1_000", "c1_001"]
    assert selected[2]["train_article_ids"] == ["d1", "d2"]


def test_validation_explicitly_allows_false_direct_training_leakage_when_saved_flag_missing():
    runner = load_runner_module()

    row_validation = {
        "customer_id_is_string": True,
        "ground_truth_matches_frozen_input": True,
        "recommendation_count_is_10": True,
        "recommendation_article_ids_are_strings": True,
        "no_duplicate_recommendations": True,
        "all_recommendations_inside_frozen_candidate_pool": True,
        "users_match_frozen_input": True,
        "direct_training_item_leakage": False,
        "saved_leakage_flag_present": False,
        "saved_flag_consistent_with_direct_check": False,
    }

    assert runner.recommendation_validation_failed(row_validation) is False


def test_smoke_prefix_must_use_replay_prefix():
    runner = load_runner_module()

    with pytest.raises(runner.SafetyError):
        runner.smoke_config("wrong_prefix")


def test_frozen_input_hash_match_is_case_insensitive():
    runner = load_runner_module()

    assert runner.frozen_hash_matches(
        expected_hash="427DA0D55124107551602B12DAD82EE05B0EAE1E296EE9F612AEA8326080D08E",
        computed_hash="427da0d55124107551602b12dad82ee05b0eae1e296ee9f612aea8326080d08e",
    ) is True


def test_frozen_input_hash_match_still_rejects_different_value():
    runner = load_runner_module()

    assert runner.frozen_hash_matches(
        expected_hash="427DA0D55124107551602B12DAD82EE05B0EAE1E296EE9F612AEA8326080D08E",
        computed_hash="527da0d55124107551602b12dad82ee05b0eae1e296ee9f612aea8326080d08e",
    ) is False


def test_settings_proxy_routes_replay_outputs_without_moving_shared_processed_input():
    runner = load_runner_module()

    class BaseSettingsStub:
        def _apply_artifact_prefix(self, filename: str, artifact_prefix: str | None = None) -> str:
            normalized_prefix = (artifact_prefix or "").strip()
            if not normalized_prefix:
                return filename
            return f"{normalized_prefix}_{filename}"

        def evaluation_base_table_svd_top10_json_path(
            self,
            subset_size: int,
            artifact_prefix: str | None = None,
        ) -> Path:
            return self.processed_data_dir / self._apply_artifact_prefix(
                f"evaluation_base_table_top10_{subset_size}.json",
                artifact_prefix,
            )

    base = BaseSettingsStub()
    base.processed_data_dir = Path("D:/base/processed")
    base.processed_interactions_with_articles_csv_path = Path("D:/base/processed/source.csv")
    base.feedback_state_path = Path("D:/base/processed/feedback_state.json")
    proxy = runner.SettingsProxy(
        base,
        processed_data_dir=Path("D:/replay/output"),
        processed_interactions_with_articles_csv_path=Path("D:/base/processed/source.csv"),
        feedback_state_path=Path("D:/replay/output/replay_feedback.json"),
    )

    assert proxy.processed_data_dir == Path("D:/replay/output")
    assert proxy.explainability_data_dir == Path("D:/replay/output/explainability")
    assert proxy.processed_interactions_with_articles_csv_path == Path("D:/base/processed/source.csv")
    assert proxy.feedback_state_path == Path("D:/replay/output/replay_feedback.json")
    assert proxy.evaluation_base_table_svd_top10_json_path(3, artifact_prefix="smoke2") == Path(
        "D:/replay/output/smoke2_evaluation_base_table_top10_3.json"
    )
