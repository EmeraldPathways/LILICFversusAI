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


class OutputSettingsStub:
    def __init__(self, processed_data_dir: Path) -> None:
        self.processed_data_dir = processed_data_dir

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

    def evaluation_base_table_svd_top10_csv_path(
        self,
        subset_size: int,
        artifact_prefix: str | None = None,
    ) -> Path:
        return self.processed_data_dir / self._apply_artifact_prefix(
            f"evaluation_base_table_top10_{subset_size}.csv",
            artifact_prefix,
        )

    def candidate_pool_validation_report_svd_top10_path(
        self,
        subset_size: int,
        artifact_prefix: str | None = None,
    ) -> Path:
        return self.processed_data_dir / self._apply_artifact_prefix(
            f"candidate_pools_top10_{subset_size}.json",
            artifact_prefix,
        )

    def svd_recommendations_top10_json_path(
        self,
        subset_size: int,
        artifact_prefix: str | None = None,
    ) -> Path:
        return self.processed_data_dir / self._apply_artifact_prefix(
            f"svd_recommendations_top10_{subset_size}.json",
            artifact_prefix,
        )

    def svd_recommendations_top10_csv_path(
        self,
        subset_size: int,
        artifact_prefix: str | None = None,
    ) -> Path:
        return self.processed_data_dir / self._apply_artifact_prefix(
            f"svd_recommendations_top10_{subset_size}.csv",
            artifact_prefix,
        )

    def svd_baseline_validation_report_top10_path(
        self,
        subset_size: int,
        artifact_prefix: str | None = None,
    ) -> Path:
        return self.processed_data_dir / self._apply_artifact_prefix(
            f"svd_baseline_validation_report_top10_{subset_size}.json",
            artifact_prefix,
        )

    def agentic_recommendations_top10_json_path(
        self,
        subset_size: int,
        artifact_prefix: str | None = None,
    ) -> Path:
        return self.processed_data_dir / self._apply_artifact_prefix(
            f"agentic_recommendations_top10_{subset_size}.json",
            artifact_prefix,
        )

    def agentic_recommendations_top10_csv_path(
        self,
        subset_size: int,
        artifact_prefix: str | None = None,
    ) -> Path:
        return self.processed_data_dir / self._apply_artifact_prefix(
            f"agentic_recommendations_top10_{subset_size}.csv",
            artifact_prefix,
        )

    def agentic_top10_validation_report_path(
        self,
        subset_size: int,
        artifact_prefix: str | None = None,
    ) -> Path:
        return self.processed_data_dir / self._apply_artifact_prefix(
            f"agentic_top10_validation_report_{subset_size}.json",
            artifact_prefix,
        )

    def hybrid_svd_agentic_recommendations_top10_json_path(
        self,
        subset_size: int,
        artifact_prefix: str | None = None,
    ) -> Path:
        return self.processed_data_dir / self._apply_artifact_prefix(
            f"hybrid_svd_agentic_recommendations_top10_{subset_size}.json",
            artifact_prefix,
        )

    def hybrid_svd_agentic_recommendations_top10_csv_path(
        self,
        subset_size: int,
        artifact_prefix: str | None = None,
    ) -> Path:
        return self.processed_data_dir / self._apply_artifact_prefix(
            f"hybrid_svd_agentic_recommendations_top10_{subset_size}.csv",
            artifact_prefix,
        )

    def hybrid_svd_agentic_validation_report_top10_path(
        self,
        subset_size: int,
        artifact_prefix: str | None = None,
    ) -> Path:
        return self.processed_data_dir / self._apply_artifact_prefix(
            f"hybrid_svd_agentic_validation_report_top10_{subset_size}.json",
            artifact_prefix,
        )

    def per_user_metrics_top10_three_methods_json_path(
        self,
        subset_size: int,
        artifact_prefix: str | None = None,
    ) -> Path:
        return self.processed_data_dir / self._apply_artifact_prefix(
            f"per_user_metrics_top10_{subset_size}_three_methods.json",
            artifact_prefix,
        )

    def per_user_metrics_top10_three_methods_csv_path(
        self,
        subset_size: int,
        artifact_prefix: str | None = None,
    ) -> Path:
        return self.processed_data_dir / self._apply_artifact_prefix(
            f"per_user_metrics_top10_{subset_size}_three_methods.csv",
            artifact_prefix,
        )

    def metric_summary_top10_three_methods_json_path(
        self,
        subset_size: int,
        artifact_prefix: str | None = None,
    ) -> Path:
        return self.processed_data_dir / self._apply_artifact_prefix(
            f"metric_summary_top10_{subset_size}_three_methods.json",
            artifact_prefix,
        )

    def metric_summary_top10_three_methods_csv_path(
        self,
        subset_size: int,
        artifact_prefix: str | None = None,
    ) -> Path:
        return self.processed_data_dir / self._apply_artifact_prefix(
            f"metric_summary_top10_{subset_size}_three_methods.csv",
            artifact_prefix,
        )

    def validation_report_top10_three_methods_json_path(
        self,
        subset_size: int,
        artifact_prefix: str | None = None,
    ) -> Path:
        return self.processed_data_dir / self._apply_artifact_prefix(
            f"validation_report_top10_{subset_size}_three_methods.json",
            artifact_prefix,
        )

    def bootstrap_ci_report_top10_three_methods_json_path(
        self,
        subset_size: int,
        artifact_prefix: str | None = None,
    ) -> Path:
        return self.processed_data_dir / self._apply_artifact_prefix(
            f"bootstrap_ci_report_top10_{subset_size}_three_methods.json",
            artifact_prefix,
        )

    def hybrid_svd_agentic_audit_report_top10_path(
        self,
        subset_size: int,
        artifact_prefix: str | None = None,
    ) -> Path:
        return self.processed_data_dir / self._apply_artifact_prefix(
            f"experiment_report_top10_{subset_size}.md",
            artifact_prefix,
        )


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


def test_full_config_uses_all_1000_rows_and_expected_prefix():
    runner = load_runner_module()

    config = runner.full_config("experiment1_deterministic_replay_full1")

    assert config.mode == "full"
    assert config.prefix == "experiment1_deterministic_replay_full1"
    assert config.sample_size == 1000
    assert config.candidate_pool_size == 100
    assert config.top_k == 10
    assert config.svd_random_state == 42
    assert config.hybrid_random_state == 42
    assert config.bootstrap_seed == 42
    assert config.bootstrap_samples == 1000
    assert config.allow_overwrite is False


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


def test_full_mode_requires_confirmation_and_exits_before_execution(monkeypatch, capsys):
    runner = load_runner_module()
    observed = {"run_called": False, "import_called": False}

    def fail_run(_config):
        observed["run_called"] = True
        raise AssertionError("execution function should not be called")

    def fail_import():
        observed["import_called"] = True
        raise AssertionError("project imports should not happen")

    monkeypatch.setattr(runner, "run_smoke", fail_run)
    monkeypatch.setattr(runner, "import_project_modules", fail_import)

    with pytest.raises(SystemExit, match="confirm-frozen-full-replay") as exc_info:
        runner.main(["--mode", "full", "--full-prefix", "experiment1_deterministic_replay_full1"])

    assert observed == {"run_called": False, "import_called": False}
    assert "confirm-frozen-full-replay" in str(exc_info.value)


def test_main_routes_smoke_and_full_through_same_execution_function(monkeypatch):
    runner = load_runner_module()
    seen: list[tuple[str, int, str]] = []

    def fake_run(config):
        seen.append((config.mode, config.sample_size, config.prefix))
        return 0

    monkeypatch.setattr(runner, "run_smoke", fake_run)

    assert runner.main(["--mode", "smoke", "--smoke-prefix", "experiment1_deterministic_replay_smoke9"]) == 0
    assert runner.main(
        [
            "--mode",
            "full",
            "--full-prefix",
            "experiment1_deterministic_replay_full1",
            "--confirm-frozen-full-replay",
        ]
    ) == 0

    assert seen == [
        ("smoke", 3, "experiment1_deterministic_replay_smoke9"),
        ("full", 1000, "experiment1_deterministic_replay_full1"),
    ]


def test_select_replay_rows_for_full_keeps_first_thousand_users_in_order():
    runner = load_runner_module()
    rows = []
    for index in range(1002):
        rows.append(
            {
                "customer_id": f"user_{index:04d}",
                "train_article_ids": [f"t{index}_1", f"t{index}_2"],
                "ground_truth_article_id": f"g{index}",
                "candidate_pool_article_ids": [f"g{index}"] + [f"c{index}_{candidate:03d}" for candidate in range(99)],
            }
        )

    selected = runner.select_replay_rows(rows, sample_size=1000)

    assert len(selected) == 1000
    assert selected[0]["customer_id"] == "user_0000"
    assert selected[-1]["customer_id"] == "user_0999"
    assert [row["customer_id"] for row in selected[:3]] == ["user_0000", "user_0001", "user_0002"]


def test_full_output_paths_use_1000_naming_and_replay_owned_roots():
    runner = load_runner_module()
    settings = OutputSettingsStub(runner.RUNNER_DIR / "experiment1_deterministic_replay_full1_processed_data")
    config = runner.full_config("experiment1_deterministic_replay_full1")

    processed_paths = runner.processed_output_paths(settings, config)
    runner_paths = runner.runner_output_paths(config)

    for path in processed_paths.values():
        resolved = path.resolve()
        assert runner.is_relative_to(resolved, runner.RUNNER_DIR)
        assert not runner.is_relative_to(resolved, runner.REPO_ROOT / "backend/app/data/processed")
        assert "1000" in path.name
        assert path.name.startswith("experiment1_deterministic_replay_full1")

    assert "top10_1000" in runner_paths["pairwise_ci_json"].name
    for path in runner_paths.values():
        assert runner.is_relative_to(path.resolve(), runner.RUNNER_DIR)


def test_validate_allowlist_rejects_preexisting_full_prefix_targets(tmp_path):
    runner = load_runner_module()
    settings = OutputSettingsStub(tmp_path / "experiment1_deterministic_replay_full1_processed_data")
    config = runner.full_config("experiment1_deterministic_replay_full1")
    allowlist = runner.declared_allowlist(settings, config)
    existing_path = next(iter(sorted(allowlist)))
    existing_path.parent.mkdir(parents=True, exist_ok=True)
    existing_path.write_text("preexisting", encoding="utf-8")

    with pytest.raises(runner.SafetyError, match="Expected output already exists before run"):
        runner.validate_allowlist(settings, config, allowlist)


def test_smoke_configuration_remains_three_users():
    runner = load_runner_module()

    config = runner.smoke_config("experiment1_deterministic_replay_smoke11")

    assert config.mode == "smoke"
    assert config.sample_size == 3
