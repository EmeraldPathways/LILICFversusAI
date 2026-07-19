from __future__ import annotations

import argparse
import builtins
import csv
import hashlib
import importlib.metadata
import json
import os
import platform
import sys
import time
import traceback
from copy import deepcopy
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from unittest.mock import patch

import httpx

sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNNER_DIR = Path(__file__).resolve().parent
BACKEND_DIR = REPO_ROOT / "backend"

FROZEN_INPUT_RELATIVE_PATH = (
    "experiments/experiment1_deterministic_replay/input/"
    "experiment1_original_frozen_input_1000.json"
)
FROZEN_INPUT_SIZE_BYTES = 5_621_254
FROZEN_INPUT_SHA256 = "427DA0D55124107551602B12DAD82EE05B0EAE1E296EE9F612AEA8326080D08E"

REQUIRED_SUPPORTING_INPUTS = (
    "backend/app/data/processed/processed_interactions_with_articles.csv",
)

PROTECTED_HISTORICAL_RELATIVE_PATHS = (
    "backend/app/data/processed/evaluation_base_table_svd_top10_1000.json",
    "backend/app/data/processed/evaluation_base_table_svd_top10_1000.csv",
    "backend/app/data/processed/candidate_pool_validation_report_svd_top10_1000.json",
    "backend/app/data/processed/svd_recommendations_top10_1000.json",
    "backend/app/data/processed/svd_recommendations_top10_1000.csv",
    "backend/app/data/processed/svd_baseline_validation_report_top10_1000.json",
    "backend/app/data/processed/agentic_recommendations_top10_1000.json",
    "backend/app/data/processed/agentic_recommendations_top10_1000.csv",
    "backend/app/data/processed/agentic_top10_validation_report_1000.json",
    "backend/app/data/processed/hybrid_svd_agentic_recommendations_top10_1000.json",
    "backend/app/data/processed/hybrid_svd_agentic_recommendations_top10_1000.csv",
    "backend/app/data/processed/hybrid_svd_agentic_validation_report_top10_1000.json",
    "backend/app/data/processed/per_user_metrics_top10_1000_three_methods.json",
    "backend/app/data/processed/per_user_metrics_top10_1000_three_methods.csv",
    "backend/app/data/processed/metric_summary_top10_1000_three_methods.json",
    "backend/app/data/processed/metric_summary_top10_1000_three_methods.csv",
    "backend/app/data/processed/bootstrap_ci_report_top10_1000_three_methods.json",
    "backend/app/data/processed/hybrid_svd_agentic_audit_report_top10_1000.md",
    "backend/app/data/processed/final_experiment_report_svd_agentic_hybrid.md",
    "backend/app/data/processed/final_two_run_comparison_report.md",
    "backend/app/data/processed/diagnostic_report_svd_vs_agentic_1000.md",
)

BLOCKED_AGENTIC_METHODS = (
    "infer_user_intent",
    "generate_explanation",
    "generate_for_user",
    "build_candidate_pools",
    "_request_structured_completion",
)

SMOKE_PREFIX_DEFAULT = "experiment1_deterministic_replay_smoke1"
SMOKE_PREFIX_REQUIRED = "experiment1_deterministic_replay_smoke"
FULL_PREFIX_RESERVED = "experiment1_deterministic_replay"

PLANNED_SERVICE_SEQUENCE = (
    "Validate frozen replay input file and hashes",
    "Write replay-prefixed evaluation-base working copy from the frozen input rows",
    "CollaborativeFilteringService.build_svd_top10_baseline(subset_size=<sample_size>, random_state=42, artifact_prefix=<prefix>, allow_overwrite=False)",
    "AgenticRecommendationService._build_top10_formal_experiment(subset_size=<sample_size>, artifact_prefix=<prefix>, allow_overwrite=False)",
    "HybridRecommendationService.build_hybrid_svd_agentic_reranker(subset_size=<sample_size>, random_state=42, artifact_prefix=<prefix>, allow_overwrite=False)",
    "EvaluationService.compute_three_method_top10_metrics_from_saved_artifacts(subset_size=<sample_size>, bootstrap_samples=1000, random_seed=42, artifact_prefix=<prefix>, allow_overwrite=False)",
)

FULL_REPLAY_DISABLED_CONFIG = {
    "enabled": False,
    "reason": "Full 1,000-user replay is reserved for future approval and intentionally disabled.",
    "prefix": FULL_PREFIX_RESERVED,
    "sample_size": 1000,
    "candidate_pool_size": 100,
    "top_k": 10,
    "svd_random_state": 42,
    "hybrid_random_state": 42,
    "bootstrap_seed": 42,
    "bootstrap_samples": 1000,
    "hybrid_weights": {"svd": 0.70, "agentic": 0.25, "diversity": 0.05},
}

RUNNER_START_TIME = time.perf_counter()


class SafetyError(RuntimeError):
    pass


class OpenAICallBlocked(SafetyError):
    pass


@dataclass(frozen=True)
class RunConfig:
    mode: str
    prefix: str
    sample_size: int
    candidate_pool_size: int
    top_k: int
    svd_random_state: int
    hybrid_random_state: int
    bootstrap_seed: int
    bootstrap_samples: int
    allow_overwrite: bool


def print_stage(message: str) -> None:
    print(f"[stage] {message}", flush=True)


def print_observability_stage(stage_name: str, event: str) -> None:
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    elapsed = time.perf_counter() - RUNNER_START_TIME
    print(
        f"{timestamp} | elapsed={elapsed:.3f}s | pid={os.getpid()} | stage={stage_name} | event={event}",
        flush=True,
    )


def import_project_modules() -> dict[str, Any]:
    if str(BACKEND_DIR) not in sys.path:
        sys.path.insert(0, str(BACKEND_DIR))

    from app.config import Settings
    from app.services.agentic_service import AgenticRecommendationService
    from app.services.cf_service import CollaborativeFilteringService
    from app.services.evaluation_service import EvaluationService
    from app.services.hybrid_service import HybridRecommendationService

    return {
        "Settings": Settings,
        "AgenticRecommendationService": AgenticRecommendationService,
        "CollaborativeFilteringService": CollaborativeFilteringService,
        "EvaluationService": EvaluationService,
        "HybridRecommendationService": HybridRecommendationService,
    }


class SettingsProxy:
    def __init__(
        self,
        base: Any,
        *,
        processed_data_dir: Path,
        processed_interactions_with_articles_csv_path: Path,
        feedback_state_path: Path,
    ) -> None:
        self._base = base
        self._processed_data_dir = processed_data_dir
        self._processed_interactions_with_articles_csv_path = processed_interactions_with_articles_csv_path
        self._feedback_state_path = feedback_state_path

    def __getattr__(self, name: str) -> Any:
        value = getattr(self._base, name)
        if callable(value) and getattr(value, "__self__", None) is self._base and hasattr(value, "__func__"):
            return value.__func__.__get__(self, type(self))
        return value

    @property
    def processed_data_dir(self) -> Path:
        return self._processed_data_dir

    @property
    def explainability_data_dir(self) -> Path:
        return self._processed_data_dir / "explainability"

    @property
    def processed_interactions_with_articles_csv_path(self) -> Path:
        return self._processed_interactions_with_articles_csv_path

    @property
    def feedback_state_path(self) -> Path:
        return self._feedback_state_path

    @property
    def openai_api_key(self) -> None:
        return None


def relative_to_repo(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def frozen_hash_matches(*, expected_hash: str, computed_hash: str) -> bool:
    return computed_hash.casefold() == expected_hash.casefold()


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_csv_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    key: json.dumps(value, ensure_ascii=True)
                    if isinstance(value, (list, dict))
                    else value
                    for key, value in row.items()
                }
            )


def file_snapshot(path: Path) -> dict[str, Any]:
    return {
        "relative_path": relative_to_repo(path),
        "exists": path.exists(),
        "size_bytes": path.stat().st_size if path.exists() else None,
        "sha256": sha256_file(path) if path.exists() else None,
    }


def snapshot_tree(root: Path) -> dict[str, dict[str, Any]]:
    if not root.exists():
        return {}
    return {
        relative_to_repo(path): file_snapshot(path)
        for path in sorted(candidate for candidate in root.rglob("*") if candidate.is_file())
    }


def combined_inventory_snapshot() -> dict[str, dict[str, Any]]:
    inventory: dict[str, dict[str, Any]] = {}
    for root in (
        REPO_ROOT / "backend/app/data/processed",
        REPO_ROOT / "backend/app/data/processed/explainability",
        RUNNER_DIR,
    ):
        inventory.update(snapshot_tree(root))
    return inventory


def protected_paths() -> list[Path]:
    paths: list[Path] = []

    for rel in REQUIRED_SUPPORTING_INPUTS:
        path = REPO_ROOT / rel
        if not path.exists():
            raise SafetyError(f"Required supporting input missing: {path}")
        paths.append(path)

    frozen_path = REPO_ROOT / FROZEN_INPUT_RELATIVE_PATH
    if not frozen_path.exists():
        raise SafetyError(f"Frozen input file missing: {frozen_path}")
    paths.append(frozen_path)

    for rel in PROTECTED_HISTORICAL_RELATIVE_PATHS:
        path = REPO_ROOT / rel
        if path.exists():
            paths.append(path)

    for rel_path in combined_inventory_snapshot():
        name = Path(rel_path).name
        if name.startswith("seed99_"):
            paths.append(REPO_ROOT / rel_path)

    shared_feedback = REPO_ROOT / "backend/app/data/processed/feedback_state.json"
    if shared_feedback.exists():
        paths.append(shared_feedback)

    deduped: dict[Path, None] = {}
    for path in paths:
        deduped[path.resolve()] = None
    return sorted(deduped.keys())


def protected_snapshot() -> dict[str, dict[str, Any]]:
    return {relative_to_repo(path): file_snapshot(path) for path in protected_paths()}


def scrub_openai_env() -> dict[str, Any]:
    existed_before = "OPENAI_API_KEY" in os.environ
    os.environ.pop("OPENAI_API_KEY", None)
    existed_during = "OPENAI_API_KEY" in os.environ
    return {
        "openai_api_key_existed_before_removal": existed_before,
        "openai_api_key_exists_during_execution": existed_during,
    }


def smoke_config(prefix: str) -> RunConfig:
    if not prefix.startswith(SMOKE_PREFIX_REQUIRED):
        raise SafetyError(
            f"Smoke prefix must begin with '{SMOKE_PREFIX_REQUIRED}'. Received: {prefix}"
        )
    return RunConfig(
        mode="smoke",
        prefix=prefix,
        sample_size=3,
        candidate_pool_size=100,
        top_k=10,
        svd_random_state=42,
        hybrid_random_state=42,
        bootstrap_seed=42,
        bootstrap_samples=1000,
        allow_overwrite=False,
    )


def feedback_override_path(config: RunConfig) -> Path:
    return RUNNER_DIR / f"{config.prefix}_feedback_state.json"


def replay_processed_data_dir(config: RunConfig) -> Path:
    return RUNNER_DIR / f"{config.prefix}_processed_data"


def verify_feedback_fallback(config: RunConfig) -> dict[str, Any]:
    override_path = feedback_override_path(config)
    if override_path.exists():
        raise SafetyError(f"Replay feedback override path must not already exist: {override_path}")
    return {
        "override_path": relative_to_repo(override_path),
        "override_path_exists_before_run": False,
        "shared_feedback_path_used_for_writes": False,
        "expected_base_weights": {
            "category_weight": 1.0,
            "colour_weight": 1.0,
            "product_type_weight": 1.0,
            "appearance_weight": 1.0,
            "diversity_penalty": 1.0,
        },
    }


def processed_output_paths(settings: Any, config: RunConfig) -> dict[str, Path]:
    return {
        "evaluation_json": settings.evaluation_base_table_svd_top10_json_path(
            config.sample_size,
            artifact_prefix=config.prefix,
        ),
        "evaluation_csv": settings.evaluation_base_table_svd_top10_csv_path(
            config.sample_size,
            artifact_prefix=config.prefix,
        ),
        "candidate_pools_json": settings.candidate_pool_validation_report_svd_top10_path(
            config.sample_size,
            artifact_prefix=config.prefix,
        ),
        "svd_json": settings.svd_recommendations_top10_json_path(
            config.sample_size,
            artifact_prefix=config.prefix,
        ),
        "svd_csv": settings.svd_recommendations_top10_csv_path(
            config.sample_size,
            artifact_prefix=config.prefix,
        ),
        "svd_validation_json": settings.svd_baseline_validation_report_top10_path(
            config.sample_size,
            artifact_prefix=config.prefix,
        ),
        "agentic_json": settings.agentic_recommendations_top10_json_path(
            config.sample_size,
            artifact_prefix=config.prefix,
        ),
        "agentic_csv": settings.agentic_recommendations_top10_csv_path(
            config.sample_size,
            artifact_prefix=config.prefix,
        ),
        "agentic_validation_json": settings.agentic_top10_validation_report_path(
            config.sample_size,
            artifact_prefix=config.prefix,
        ),
        "hybrid_json": settings.hybrid_svd_agentic_recommendations_top10_json_path(
            config.sample_size,
            artifact_prefix=config.prefix,
        ),
        "hybrid_csv": settings.hybrid_svd_agentic_recommendations_top10_csv_path(
            config.sample_size,
            artifact_prefix=config.prefix,
        ),
        "hybrid_validation_json": settings.hybrid_svd_agentic_validation_report_top10_path(
            config.sample_size,
            artifact_prefix=config.prefix,
        ),
        "per_user_json": settings.per_user_metrics_top10_three_methods_json_path(
            config.sample_size,
            artifact_prefix=config.prefix,
        ),
        "per_user_csv": settings.per_user_metrics_top10_three_methods_csv_path(
            config.sample_size,
            artifact_prefix=config.prefix,
        ),
        "metric_summary_json": settings.metric_summary_top10_three_methods_json_path(
            config.sample_size,
            artifact_prefix=config.prefix,
        ),
        "metric_summary_csv": settings.metric_summary_top10_three_methods_csv_path(
            config.sample_size,
            artifact_prefix=config.prefix,
        ),
        "validation_json": settings.validation_report_top10_three_methods_json_path(
            config.sample_size,
            artifact_prefix=config.prefix,
        ),
        "bootstrap_json": settings.bootstrap_ci_report_top10_three_methods_json_path(
            config.sample_size,
            artifact_prefix=config.prefix,
        ),
        "experiment_report_md": settings.hybrid_svd_agentic_audit_report_top10_path(
            config.sample_size,
            artifact_prefix=config.prefix,
        ),
    }


def runner_output_paths(config: RunConfig) -> dict[str, Path]:
    return {
        "run_configuration_json": RUNNER_DIR / f"{config.prefix}_run_configuration.json",
        "provenance_json": RUNNER_DIR / f"{config.prefix}_provenance.json",
        "openai_call_provenance_json": RUNNER_DIR / f"{config.prefix}_openai_call_provenance.json",
        "created_files_json": RUNNER_DIR / f"{config.prefix}_created_files.json",
        "pairwise_ci_json": RUNNER_DIR / f"{config.prefix}_pairwise_ci_report_top10_{config.sample_size}_three_methods.json",
    }


def declared_allowlist(settings: Any, config: RunConfig) -> set[Path]:
    return set(processed_output_paths(settings, config).values()) | set(
        runner_output_paths(config).values()
    )


def is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def validate_allowlist(settings: Any, config: RunConfig, allowlist: set[Path]) -> None:
    approved_roots = (settings.processed_data_dir.resolve(), RUNNER_DIR.resolve())
    blocked_name_prefixes = (
        "seed99_",
        "evaluation_base_table_svd_top10_",
        "svd_recommendations_top10_",
        "agentic_recommendations_top10_",
        "hybrid_svd_agentic_recommendations_top10_",
    )

    for path in sorted(allowlist):
        resolved = path.resolve()
        if not any(is_relative_to(resolved, root) for root in approved_roots):
            raise SafetyError(f"Output path outside approved roots: {resolved}")
        if path.exists():
            raise SafetyError(f"Expected output already exists before run: {resolved}")
        name = path.name
        if not name.startswith(config.prefix):
            raise SafetyError(f"Incorrect output prefix: {resolved}")
        if any(name.startswith(prefix) for prefix in blocked_name_prefixes):
            raise SafetyError(f"Historical output naming blocked: {resolved}")


class WriteGuard:
    def __init__(self, allowlist: Iterable[Path], existing_before: Iterable[Path]) -> None:
        self.allowlist = {path.resolve() for path in allowlist}
        self.existing_before = {path.resolve() for path in existing_before}
        self.created_allowlisted_paths: list[Path] = []
        self._patches: list[Any] = []

    def _validate_write_target(self, candidate: Any, mode: str) -> None:
        if not any(flag in mode for flag in ("w", "a", "x", "+")):
            return

        path = Path(candidate).resolve()
        if path in self.existing_before:
            raise SafetyError(f"Write blocked to pre-existing path: {path}")
        if path not in self.allowlist:
            raise SafetyError(f"Unexpected write target blocked: {path}")
        if path not in self.created_allowlisted_paths:
            self.created_allowlisted_paths.append(path)

    def __enter__(self) -> "WriteGuard":
        original_builtin_open = builtins.open
        original_path_open = Path.open

        def guarded_builtin_open(file: Any, mode: str = "r", *args: Any, **kwargs: Any):
            self._validate_write_target(file, mode)
            return original_builtin_open(file, mode, *args, **kwargs)

        def guarded_path_open(path_obj: Path, mode: str = "r", *args: Any, **kwargs: Any):
            self._validate_write_target(path_obj, mode)
            return original_path_open(path_obj, mode, *args, **kwargs)

        def blocked_delete(*args: Any, **kwargs: Any):
            raise SafetyError("Deletion is blocked during replay execution.")

        def blocked_rename(*args: Any, **kwargs: Any):
            raise SafetyError("Rename/replace is blocked during replay execution.")

        self._patches = [
            patch("builtins.open", guarded_builtin_open),
            patch.object(Path, "open", guarded_path_open),
            patch.object(Path, "unlink", blocked_delete),
            patch.object(Path, "rename", blocked_rename),
            patch.object(Path, "replace", blocked_rename),
            patch("os.remove", blocked_delete),
            patch("os.unlink", blocked_delete),
            patch("os.rename", blocked_rename),
            patch("os.replace", blocked_rename),
        ]
        for active in self._patches:
            active.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        while self._patches:
            self._patches.pop().stop()


class OpenAIGuard:
    def __init__(self, agentic_cls: Any) -> None:
        self.agentic_cls = agentic_cls
        self.attempted_call_count = 0
        self.completed_call_count = 0
        self.blocked_methods: list[str] = []
        self._patches: list[Any] = []

    def __enter__(self) -> "OpenAIGuard":
        def blocked_method(name: str):
            def _blocked(*args: Any, **kwargs: Any):
                self.attempted_call_count += 1
                self.blocked_methods.append(name)
                raise OpenAICallBlocked(f"Blocked OpenAI-backed method: {name}")

            return _blocked

        def blocked_httpx(name: str):
            def _blocked(*args: Any, **kwargs: Any):
                self.attempted_call_count += 1
                self.blocked_methods.append(name)
                raise OpenAICallBlocked(f"Blocked outbound OpenAI/httpx path: {name}")

            return _blocked

        self._patches = [
            patch.object(self.agentic_cls, "infer_user_intent", blocked_method("infer_user_intent")),
            patch.object(self.agentic_cls, "generate_explanation", blocked_method("generate_explanation")),
            patch.object(self.agentic_cls, "generate_for_user", blocked_method("generate_for_user")),
            patch.object(self.agentic_cls, "build_candidate_pools", blocked_method("build_candidate_pools")),
            patch.object(
                self.agentic_cls,
                "_request_structured_completion",
                blocked_method("_request_structured_completion"),
            ),
            patch("httpx.post", blocked_httpx("httpx.post")),
            patch("httpx.request", blocked_httpx("httpx.request")),
            patch.object(httpx.Client, "post", blocked_httpx("httpx.Client.post")),
            patch.object(httpx.Client, "request", blocked_httpx("httpx.Client.request")),
            patch.object(httpx.Client, "send", blocked_httpx("httpx.Client.send")),
        ]
        for active in self._patches:
            active.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        while self._patches:
            self._patches.pop().stop()


def load_json_rows(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise SafetyError(f"Expected JSON list at {path}")
    return payload


def validate_frozen_rows(
    rows: list[dict[str, Any]],
    *,
    expected_row_count: int = 1000,
) -> dict[str, Any]:
    customer_ids = [row.get("customer_id") for row in rows]
    unique_customer_ids = {
        customer_id for customer_id in customer_ids if isinstance(customer_id, str) and customer_id
    }
    rows_with_non_string_customer_id = [
        index for index, row in enumerate(rows) if not isinstance(row.get("customer_id"), str)
    ]
    rows_with_missing_training_history = [
        row.get("customer_id")
        for row in rows
        if not isinstance(row.get("train_article_ids"), list) or len(row.get("train_article_ids", [])) == 0
    ]
    rows_with_non_string_training_ids = [
        row.get("customer_id")
        for row in rows
        if any(not isinstance(article_id, str) for article_id in row.get("train_article_ids", []))
    ]
    rows_with_missing_ground_truth = [
        row.get("customer_id")
        for row in rows
        if not isinstance(row.get("ground_truth_article_id"), str)
        or not str(row.get("ground_truth_article_id")).strip()
    ]
    rows_with_missing_candidate_pool = [
        row.get("customer_id")
        for row in rows
        if not isinstance(row.get("candidate_pool_article_ids"), list)
    ]
    rows_with_candidate_pool_size_not_100 = [
        row.get("customer_id")
        for row in rows
        if not isinstance(row.get("candidate_pool_article_ids"), list)
        or len(row.get("candidate_pool_article_ids", [])) != 100
    ]
    rows_with_duplicate_candidate_pool_items = [
        row.get("customer_id")
        for row in rows
        if isinstance(row.get("candidate_pool_article_ids"), list)
        and len(row.get("candidate_pool_article_ids", [])) != len(set(row.get("candidate_pool_article_ids", [])))
    ]
    rows_with_non_string_candidate_pool_ids = [
        row.get("customer_id")
        for row in rows
        if any(not isinstance(article_id, str) for article_id in row.get("candidate_pool_article_ids", []))
    ]
    rows_with_ground_truth_missing_from_candidate_pool = [
        row.get("customer_id")
        for row in rows
        if row.get("ground_truth_article_id") not in row.get("candidate_pool_article_ids", [])
    ]

    return {
        "row_count": len(rows),
        "expected_row_count": expected_row_count,
        "unique_customer_id_count": len(unique_customer_ids),
        "rows_with_non_string_customer_id": rows_with_non_string_customer_id,
        "rows_with_missing_training_history": rows_with_missing_training_history,
        "rows_with_non_string_training_ids": rows_with_non_string_training_ids,
        "rows_with_missing_ground_truth": rows_with_missing_ground_truth,
        "rows_with_missing_candidate_pool": rows_with_missing_candidate_pool,
        "rows_with_candidate_pool_size_not_100": rows_with_candidate_pool_size_not_100,
        "rows_with_duplicate_candidate_pool_items": rows_with_duplicate_candidate_pool_items,
        "rows_with_non_string_candidate_pool_ids": rows_with_non_string_candidate_pool_ids,
        "rows_with_ground_truth_missing_from_candidate_pool": rows_with_ground_truth_missing_from_candidate_pool,
        "ok": (
            len(rows) == expected_row_count
            and len(unique_customer_ids) == expected_row_count
            and not rows_with_non_string_customer_id
            and not rows_with_missing_training_history
            and not rows_with_non_string_training_ids
            and not rows_with_missing_ground_truth
            and not rows_with_missing_candidate_pool
            and not rows_with_candidate_pool_size_not_100
            and not rows_with_duplicate_candidate_pool_items
            and not rows_with_non_string_candidate_pool_ids
            and not rows_with_ground_truth_missing_from_candidate_pool
        ),
    }


def frozen_input_path() -> Path:
    return REPO_ROOT / FROZEN_INPUT_RELATIVE_PATH


def load_and_validate_frozen_input() -> dict[str, Any]:
    path = frozen_input_path()
    if not path.exists():
        raise SafetyError(f"Frozen input file missing: {path}")
    size_bytes = path.stat().st_size
    if size_bytes != FROZEN_INPUT_SIZE_BYTES:
        raise SafetyError(
            f"Frozen input size mismatch. Expected {FROZEN_INPUT_SIZE_BYTES}, received {size_bytes}."
        )
    sha256 = sha256_file(path)
    if not frozen_hash_matches(expected_hash=FROZEN_INPUT_SHA256, computed_hash=sha256):
        raise SafetyError(
            f"Frozen input SHA-256 mismatch. Expected {FROZEN_INPUT_SHA256}, received {sha256}."
        )
    rows = load_json_rows(path)
    validation = validate_frozen_rows(rows)
    if not validation["ok"]:
        raise SafetyError("Frozen input structural validation failed.")
    return {
        "path": path,
        "relative_path": relative_to_repo(path),
        "size_bytes": size_bytes,
        "sha256": sha256,
        "rows": rows,
        "validation": validation,
        "ordered_customer_id_hash": ordered_customer_id_hash(rows),
        "training_history_mapping_hash": training_history_mapping_hash(rows),
        "ground_truth_mapping_hash": ground_truth_mapping_hash(rows),
        "candidate_pool_mapping_hash": candidate_pool_mapping_hash(rows),
    }


def select_replay_rows(rows: list[dict[str, Any]], sample_size: int) -> list[dict[str, Any]]:
    if sample_size <= 0:
        raise SafetyError(f"Replay sample size must be positive. Received {sample_size}.")
    if len(rows) < sample_size:
        raise SafetyError(f"Frozen input contains only {len(rows)} rows, cannot select {sample_size}.")
    return deepcopy(rows[:sample_size])


def ordered_customer_id_hash(rows: list[dict[str, Any]]) -> str:
    ordered_ids = [row["customer_id"] for row in rows]
    return sha256_text(canonical_json(ordered_ids))


def training_history_mapping_hash(rows: list[dict[str, Any]]) -> str:
    payload = [
        {"customer_id": row["customer_id"], "train_article_ids": row["train_article_ids"]}
        for row in rows
    ]
    return sha256_text(canonical_json(payload))


def ground_truth_mapping_hash(rows: list[dict[str, Any]]) -> str:
    payload = [
        {"customer_id": row["customer_id"], "ground_truth_article_id": row["ground_truth_article_id"]}
        for row in rows
    ]
    return sha256_text(canonical_json(payload))


def candidate_pool_mapping_hash(rows: list[dict[str, Any]]) -> str:
    payload = [
        {"customer_id": row["customer_id"], "candidate_pool_article_ids": row["candidate_pool_article_ids"]}
        for row in rows
    ]
    return sha256_text(canonical_json(payload))


def build_replay_candidate_pool_report(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "selected_user_count": len(rows),
        "actual_selected_subset_size": len(rows),
        "candidate_pool_target_size": 100,
        "ground_truth_in_candidate_pool_count": sum(
            1 for row in rows if row["ground_truth_article_id"] in row["candidate_pool_article_ids"]
        ),
        "duplicate_candidate_pool_count": sum(
            1
            for row in rows
            if len(row["candidate_pool_article_ids"]) != len(set(row["candidate_pool_article_ids"]))
        ),
        "selected_customer_ids": [row["customer_id"] for row in rows],
        "selection_method": (
            "first_n_rows_from_frozen_input_preserving_customer_order,"
            " training_history, ground_truth, candidate_pool, and candidate_pool_order"
        ),
    }


def build_replay_evaluation_csv_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    csv_rows: list[dict[str, Any]] = []
    for row in rows:
        csv_rows.append(
            {
                **row,
                "train_article_ids": row["train_article_ids"],
                "train_transaction_dates": row.get("train_transaction_dates", []),
                "candidate_pool_article_ids": row["candidate_pool_article_ids"],
            }
        )
    return csv_rows


def dependency_versions() -> dict[str, str]:
    versions: dict[str, str] = {}
    for package_name in (
        "httpx",
        "numpy",
        "pandas",
        "pydantic",
        "pydantic-settings",
        "scikit-learn",
        "scipy",
    ):
        try:
            versions[package_name] = importlib.metadata.version(package_name)
        except importlib.metadata.PackageNotFoundError:
            versions[package_name] = "not-installed"
    return versions


def source_code_hashes() -> dict[str, str]:
    paths = (
        Path(__file__),
        REPO_ROOT / "backend/app/config.py",
        REPO_ROOT / "backend/app/services/cf_service.py",
        REPO_ROOT / "backend/app/services/agentic_service.py",
        REPO_ROOT / "backend/app/services/hybrid_service.py",
        REPO_ROOT / "backend/app/services/evaluation_service.py",
    )
    return {relative_to_repo(path): sha256_file(path) for path in paths}


def validate_candidate_pool_rows(
    evaluation_rows: list[dict[str, Any]],
    candidate_pool_size: int,
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for row in evaluation_rows:
        customer_id = row.get("customer_id")
        candidate_pool = row.get("candidate_pool_article_ids", [])
        ground_truth = row.get("ground_truth_article_id")
        findings.append(
            {
                "customer_id": customer_id,
                "customer_id_is_string": isinstance(customer_id, str),
                "candidate_pool_size_is_100": len(candidate_pool) == candidate_pool_size,
                "candidate_pool_ids_are_strings": all(isinstance(article_id, str) for article_id in candidate_pool),
                "candidate_pool_has_unique_ids": len(candidate_pool) == len(set(candidate_pool)),
                "ground_truth_matches_frozen_input": isinstance(ground_truth, str),
                "ground_truth_inside_candidate_pool": ground_truth in candidate_pool,
            }
        )
    return findings


def validate_recommendation_rows(
    method_name: str,
    recommendation_rows: list[dict[str, Any]],
    evaluation_rows_by_user: dict[str, dict[str, Any]],
    expected_users: list[str],
    top_k: int,
) -> list[dict[str, Any]]:
    recommendation_lookup = {row["customer_id"]: row for row in recommendation_rows}
    same_users = list(recommendation_lookup.keys()) == expected_users
    findings: list[dict[str, Any]] = []
    for customer_id in expected_users:
        authoritative_row = evaluation_rows_by_user[customer_id]
        authoritative_ground_truth = authoritative_row["ground_truth_article_id"]
        authoritative_pool = authoritative_row["candidate_pool_article_ids"]
        authoritative_training = set(authoritative_row["train_article_ids"])
        row = recommendation_lookup.get(customer_id, {"top_10_recommendations": [], "ground_truth_article_id": None})
        recs = row.get("top_10_recommendations", [])
        rec_ids = [item.get("article_id") for item in recs]
        direct_intersection = sorted(set(rec_ids) & authoritative_training)
        direct_leakage = bool(direct_intersection)
        saved_flag_present = "top_10_contains_training_items" in row
        saved_flag_value = row.get("top_10_contains_training_items")
        saved_flag_consistent = (
            None
            if not saved_flag_present
            else bool(saved_flag_value) == direct_leakage
        )
        findings.append(
            {
                "method": method_name,
                "customer_id": customer_id,
                "customer_id_is_string": isinstance(customer_id, str),
                "ground_truth_matches_frozen_input": row.get("ground_truth_article_id") == authoritative_ground_truth,
                "recommendation_count_is_10": len(rec_ids) == top_k,
                "recommendation_article_ids_are_strings": all(isinstance(article_id, str) for article_id in rec_ids),
                "no_duplicate_recommendations": len(rec_ids) == len(set(rec_ids)),
                "all_recommendations_inside_frozen_candidate_pool": all(
                    article_id in authoritative_pool for article_id in rec_ids
                ),
                "users_match_frozen_input": same_users,
                "direct_training_item_intersection": direct_intersection,
                "direct_training_item_leakage": direct_leakage,
                "saved_leakage_flag_present": saved_flag_present,
                "saved_flag_consistent_with_direct_check": saved_flag_consistent,
            }
        )
    return findings


def recommendation_validation_failed(row_validation: dict[str, Any]) -> bool:
    required_true_keys = (
        "customer_id_is_string",
        "ground_truth_matches_frozen_input",
        "recommendation_count_is_10",
        "recommendation_article_ids_are_strings",
        "no_duplicate_recommendations",
        "all_recommendations_inside_frozen_candidate_pool",
        "users_match_frozen_input",
    )
    if any(row_validation.get(key) is not True for key in required_true_keys):
        return True
    if row_validation.get("direct_training_item_leakage") is not False:
        return True
    if row_validation.get("saved_leakage_flag_present") and row_validation.get(
        "saved_flag_consistent_with_direct_check"
    ) is False:
        return True
    return False


def validate_replay_outputs(
    config: RunConfig,
    processed_paths: dict[str, Path],
    replay_subset_report: dict[str, Any],
    evaluation_result: dict[str, Any],
) -> dict[str, Any]:
    evaluation_rows = load_json_rows(processed_paths["evaluation_json"])
    svd_rows = load_json_rows(processed_paths["svd_json"])
    agentic_rows = load_json_rows(processed_paths["agentic_json"])
    hybrid_rows = load_json_rows(processed_paths["hybrid_json"])

    expected_users = [row["customer_id"] for row in evaluation_rows]
    evaluation_rows_by_user = {row["customer_id"]: row for row in evaluation_rows}

    evaluation_findings = validate_candidate_pool_rows(
        evaluation_rows,
        config.candidate_pool_size,
    )
    svd_findings = validate_recommendation_rows(
        "svd", svd_rows, evaluation_rows_by_user, expected_users, config.top_k
    )
    agentic_findings = validate_recommendation_rows(
        "agentic", agentic_rows, evaluation_rows_by_user, expected_users, config.top_k
    )
    hybrid_findings = validate_recommendation_rows(
        "hybrid", hybrid_rows, evaluation_rows_by_user, expected_users, config.top_k
    )

    failures: list[dict[str, Any]] = []

    for item in evaluation_findings:
        required_true_keys = (
            "customer_id_is_string",
            "candidate_pool_size_is_100",
            "candidate_pool_ids_are_strings",
            "candidate_pool_has_unique_ids",
            "ground_truth_matches_frozen_input",
            "ground_truth_inside_candidate_pool",
        )
        if any(item.get(key) is not True for key in required_true_keys):
            failures.append(item)

    for item in svd_findings + agentic_findings + hybrid_findings:
        if recommendation_validation_failed(item):
            failures.append(item)

    summary_validation = evaluation_result["validation"]
    summary_expected = {
        "users_evaluated": config.sample_size,
        "users_with_svd_metrics": config.sample_size,
        "users_with_agentic_metrics": config.sample_size,
        "users_with_hybrid_metrics": config.sample_size,
        "svd_top_10_count_check": config.sample_size,
        "agentic_top_10_count_check": config.sample_size,
        "hybrid_top_10_count_check": config.sample_size,
        "svd_recommendations_inside_candidate_pool_check": config.sample_size,
        "agentic_recommendations_inside_candidate_pool_check": config.sample_size,
        "hybrid_recommendations_inside_candidate_pool_check": config.sample_size,
    }
    for key, expected in summary_expected.items():
        if summary_validation.get(key) != expected:
            failures.append(
                {
                    "summary_validation_check": key,
                    "expected": expected,
                    "actual": summary_validation.get(key),
                }
            )

    if replay_subset_report["actual_selected_subset_size"] != config.sample_size:
        failures.append({"subset_size_mismatch": replay_subset_report["actual_selected_subset_size"]})
    if replay_subset_report["candidate_pool_target_size"] != config.candidate_pool_size:
        failures.append(
            {"candidate_pool_target_size_mismatch": replay_subset_report["candidate_pool_target_size"]}
        )
    if replay_subset_report["ground_truth_in_candidate_pool_count"] != config.sample_size:
        failures.append(
            {
                "ground_truth_in_candidate_pool_count_mismatch": replay_subset_report[
                    "ground_truth_in_candidate_pool_count"
                ]
            }
        )
    if replay_subset_report["duplicate_candidate_pool_count"] != 0:
        failures.append(
            {"duplicate_candidate_pool_count": replay_subset_report["duplicate_candidate_pool_count"]}
        )

    return {
        "evaluation_rows": evaluation_findings,
        "svd_rows": svd_findings,
        "agentic_rows": agentic_findings,
        "hybrid_rows": hybrid_findings,
        "summary_validation": summary_validation,
        "failures": failures,
        "ok": not failures,
    }


def inventory_diff(
    *,
    before: dict[str, dict[str, Any]],
    after: dict[str, dict[str, Any]],
    approved_allowlist: set[str],
) -> dict[str, Any]:
    created = sorted(rel_path for rel_path in after if rel_path not in before)
    modified = sorted(
        rel_path
        for rel_path in before
        if rel_path in after
        and (
            before[rel_path]["size_bytes"] != after[rel_path]["size_bytes"]
            or before[rel_path]["sha256"] != after[rel_path]["sha256"]
        )
    )
    deleted = sorted(rel_path for rel_path in before if rel_path not in after)
    unauthorized_created = sorted(rel_path for rel_path in created if rel_path not in approved_allowlist)
    return {
        "created": created,
        "modified": modified,
        "deleted": deleted,
        "unauthorized_created": unauthorized_created,
        "ok": not modified and not deleted and not unauthorized_created,
    }


def frozen_input_hashes(snapshot: dict[str, Any]) -> dict[str, Any]:
    return {
        "frozen_source_path": snapshot["relative_path"],
        "frozen_source_size_bytes": snapshot["size_bytes"],
        "frozen_source_sha256": snapshot["sha256"],
        "ordered_customer_id_hash": snapshot["ordered_customer_id_hash"],
        "training_history_mapping_hash": snapshot["training_history_mapping_hash"],
        "ground_truth_mapping_hash": snapshot["ground_truth_mapping_hash"],
        "candidate_pool_mapping_hash": snapshot["candidate_pool_mapping_hash"],
    }


def dry_run_payload(config: RunConfig) -> dict[str, Any]:
    before_inventory = combined_inventory_snapshot()
    env_status = scrub_openai_env()

    print_observability_stage("project module import", "started")
    modules = import_project_modules()
    print_observability_stage("project module import", "completed")
    Settings = modules["Settings"]

    print_observability_stage("frozen-input loading and validation", "started")
    frozen = load_and_validate_frozen_input()
    selected_rows = select_replay_rows(frozen["rows"], config.sample_size)
    print_observability_stage("frozen-input loading and validation", "completed")
    print_observability_stage("replay configuration/settings creation", "started")
    base_settings = Settings()
    settings = SettingsProxy(
        base_settings,
        processed_data_dir=replay_processed_data_dir(config),
        processed_interactions_with_articles_csv_path=base_settings.processed_interactions_with_articles_csv_path,
        feedback_state_path=feedback_override_path(config),
    )
    print_observability_stage("replay configuration/settings creation", "completed")
    allowlist = declared_allowlist(settings, config)
    validate_allowlist(settings, config, allowlist)

    processed_paths = processed_output_paths(settings, config)
    after_inventory = combined_inventory_snapshot()
    inventory_unchanged = before_inventory == after_inventory

    return {
        "verdict": "SAFE_TO_SMOKE_TEST" if inventory_unchanged else "UNSAFE_TO_SMOKE_TEST",
        "mode": "dry-run",
        "config": asdict(config),
        "formal_sequence": [
            step.replace("<prefix>", config.prefix).replace("<sample_size>", str(config.sample_size))
            for step in PLANNED_SERVICE_SEQUENCE
        ],
        "frozen_input": frozen_input_hashes(frozen),
        "selected_user_ids": [row["customer_id"] for row in selected_rows],
        "selected_ordered_customer_id_hash": ordered_customer_id_hash(selected_rows),
        "selected_training_history_mapping_hash": training_history_mapping_hash(selected_rows),
        "selected_ground_truth_mapping_hash": ground_truth_mapping_hash(selected_rows),
        "selected_candidate_pool_mapping_hash": candidate_pool_mapping_hash(selected_rows),
        "write_allowlist": [relative_to_repo(path) for path in sorted(allowlist)],
        "planned_output_paths": {key: relative_to_repo(path) for key, path in processed_paths.items()},
        "runner_output_paths": {
            key: relative_to_repo(path) for key, path in runner_output_paths(config).items()
        },
        "write_behavior": "no writes in dry-run",
        "openai_environment": {**env_status, "openai_api_key_required": False},
        "feedback_state_isolation": verify_feedback_fallback(config),
        "full_mode_status": FULL_REPLAY_DISABLED_CONFIG,
        "directory_inventories_identical": inventory_unchanged,
    }


def run_smoke(config: RunConfig) -> int:
    before_inventory = combined_inventory_snapshot()
    env_status = scrub_openai_env()

    print_observability_stage("project module import", "started")
    modules = import_project_modules()
    print_observability_stage("project module import", "completed")
    Settings = modules["Settings"]
    CollaborativeFilteringService = modules["CollaborativeFilteringService"]
    AgenticRecommendationService = modules["AgenticRecommendationService"]
    HybridRecommendationService = modules["HybridRecommendationService"]
    EvaluationService = modules["EvaluationService"]

    print_observability_stage("frozen-input loading and validation", "started")
    frozen = load_and_validate_frozen_input()
    selected_rows = select_replay_rows(frozen["rows"], config.sample_size)
    print_observability_stage("frozen-input loading and validation", "completed")
    print_observability_stage("replay configuration/settings creation", "started")
    base_settings = Settings()
    settings = SettingsProxy(
        base_settings,
        processed_data_dir=replay_processed_data_dir(config),
        processed_interactions_with_articles_csv_path=base_settings.processed_interactions_with_articles_csv_path,
        feedback_state_path=feedback_override_path(config),
    )
    print_observability_stage("replay configuration/settings creation", "completed")
    allowlist = declared_allowlist(settings, config)
    validate_allowlist(settings, config, allowlist)

    processed_paths = processed_output_paths(settings, config)
    replay_subset_report = build_replay_candidate_pool_report(selected_rows)
    print_observability_stage("protected_snapshot() before-run", "started")
    protected_before = protected_snapshot()
    print_observability_stage("protected_snapshot() before-run", "completed")
    feedback_info = verify_feedback_fallback(config)
    existing_before_paths = {REPO_ROOT / rel_path for rel_path in before_inventory.keys()}
    approved_allowlist_rel = {relative_to_repo(path) for path in allowlist}

    try:
        with OpenAIGuard(AgenticRecommendationService) as openai_guard, WriteGuard(
            allowlist,
            existing_before_paths,
        ) as write_guard:
            cf_service = CollaborativeFilteringService(settings)
            agentic_service = AgenticRecommendationService(settings)
            hybrid_service = HybridRecommendationService(settings, cf_service, agentic_service)
            evaluation_service = EvaluationService(settings)
            runner_paths = runner_output_paths(config)

            print_stage("writing replay configuration")
            write_json(
                runner_paths["run_configuration_json"],
                {
                    "config": asdict(config),
                    "formal_sequence": [
                        step.replace("<prefix>", config.prefix).replace(
                            "<sample_size>",
                            str(config.sample_size),
                        )
                        for step in PLANNED_SERVICE_SEQUENCE
                    ],
                    "frozen_input": frozen_input_hashes(frozen),
                    "selected_user_ids": [row["customer_id"] for row in selected_rows],
                    "write_allowlist": sorted(approved_allowlist_rel),
                },
            )

            print_stage("writing replay evaluation-base working copy")
            print_observability_stage("replay working evaluation-base write", "started")
            write_json(processed_paths["evaluation_json"], selected_rows)
            write_csv_rows(
                processed_paths["evaluation_csv"],
                build_replay_evaluation_csv_rows(selected_rows),
            )
            write_json(processed_paths["candidate_pools_json"], replay_subset_report)
            print_observability_stage("replay working evaluation-base write", "completed")

            print_stage("running SVD baseline")
            print_observability_stage("SVD", "started")
            cf_service.build_svd_top10_baseline(
                subset_size=config.sample_size,
                random_state=config.svd_random_state,
                artifact_prefix=config.prefix,
                allow_overwrite=False,
            )
            print_observability_stage("SVD", "completed")

            print_stage("running deterministic standalone 3-agent")
            print_observability_stage("deterministic Standalone 3-Agent", "started")
            agentic_service._build_top10_formal_experiment(
                subset_size=config.sample_size,
                artifact_prefix=config.prefix,
                allow_overwrite=False,
            )
            print_observability_stage("deterministic Standalone 3-Agent", "completed")

            print_stage("running hybrid reranker")
            print_observability_stage("Hybrid", "started")
            hybrid_service.build_hybrid_svd_agentic_reranker(
                subset_size=config.sample_size,
                random_state=config.hybrid_random_state,
                artifact_prefix=config.prefix,
                allow_overwrite=False,
            )
            print_observability_stage("Hybrid", "completed")

            print_stage("running three-method evaluation")
            print_observability_stage("metric calculation", "started")
            evaluation_result = evaluation_service.compute_three_method_top10_metrics_from_saved_artifacts(
                subset_size=config.sample_size,
                bootstrap_samples=config.bootstrap_samples,
                random_seed=config.bootstrap_seed,
                artifact_prefix=config.prefix,
                allow_overwrite=False,
            )
            print_observability_stage("metric calculation", "completed")

            print_observability_stage("bootstrap confidence intervals", "started")
            pairwise_only = {
                key: value
                for key, value in evaluation_result["bootstrap"]["confidence_intervals"].items()
                if key.startswith("difference_")
            }
            write_json(
                runner_paths["pairwise_ci_json"],
                {
                    "bootstrap_samples": config.bootstrap_samples,
                    "random_seed": config.bootstrap_seed,
                    "pairwise_confidence_intervals": pairwise_only,
                },
            )
            print_observability_stage("bootstrap confidence intervals", "completed")

            print_observability_stage("provenance and zero-OpenAI evidence write", "started")
            write_json(
                runner_paths["openai_call_provenance_json"],
                {
                    **env_status,
                    "blocked_method_names": list(BLOCKED_AGENTIC_METHODS),
                    "attempted_openai_call_count": openai_guard.attempted_call_count,
                    "completed_openai_call_count": openai_guard.completed_call_count,
                    "openai_api_key_required": False,
                    "primary_proof": "Only deterministic downstream formal methods were invoked.",
                },
            )

            print_stage("validating replay outputs")
            print_observability_stage("recommendation validation", "started")
            validation_result = validate_replay_outputs(
                config=config,
                processed_paths=processed_paths,
                replay_subset_report=replay_subset_report,
                evaluation_result=evaluation_result,
            )
            if not validation_result["ok"]:
                raise SafetyError("Replay output validation failed.")
            print_observability_stage("recommendation validation", "completed")

            inventory_pre_provenance = combined_inventory_snapshot()
            print_observability_stage("protected_snapshot() after-run", "started")
            protected_after_pre_provenance = protected_snapshot()
            print_observability_stage("protected_snapshot() after-run", "completed")
            protected_changed_pre_provenance = [
                rel_path
                for rel_path in protected_before
                if rel_path not in protected_after_pre_provenance
                or protected_before[rel_path]["size_bytes"] != protected_after_pre_provenance[rel_path]["size_bytes"]
                or protected_before[rel_path]["sha256"] != protected_after_pre_provenance[rel_path]["sha256"]
            ]
            if protected_changed_pre_provenance:
                raise SafetyError("Historical file snapshot changed before provenance creation.")

            print_stage("writing provenance")
            write_json(
                runner_paths["provenance_json"],
                {
                    "project_root": str(REPO_ROOT),
                    "runner_path": relative_to_repo(Path(__file__)),
                    "platform": platform.platform(),
                    "python_executable": sys.executable,
                    "python_version": sys.version,
                    "dependency_versions": dependency_versions(),
                    "runner_sha256": sha256_file(Path(__file__)),
                    "source_code_hashes": source_code_hashes(),
                    "frozen_input": frozen_input_hashes(frozen),
                    "selected_user_ids": [row["customer_id"] for row in selected_rows],
                    "selected_ordered_customer_id_hash": ordered_customer_id_hash(selected_rows),
                    "selected_training_history_mapping_hash": training_history_mapping_hash(selected_rows),
                    "selected_ground_truth_mapping_hash": ground_truth_mapping_hash(selected_rows),
                    "selected_candidate_pool_mapping_hash": candidate_pool_mapping_hash(selected_rows),
                    "run_configuration": asdict(config),
                    "hybrid_weights": {"svd": 0.70, "agentic": 0.25, "diversity": 0.05},
                    "directory_inventory_before": before_inventory,
                    "directory_inventory_pre_provenance": inventory_pre_provenance,
                    "protected_files_before": protected_before,
                    "protected_files_pre_provenance": protected_after_pre_provenance,
                    "protected_files_changed_pre_provenance": protected_changed_pre_provenance,
                    "feedback_state_isolation": feedback_info,
                    "openai_guard_result": {
                        **env_status,
                        "blocked_method_names": list(BLOCKED_AGENTIC_METHODS),
                        "attempted_openai_call_count": openai_guard.attempted_call_count,
                        "completed_openai_call_count": openai_guard.completed_call_count,
                    },
                    "validation_result": validation_result,
                    "processed_output_paths": {
                        key: relative_to_repo(path) for key, path in processed_paths.items()
                    },
                    "runner_output_paths": {
                        key: relative_to_repo(path) for key, path in runner_paths.items()
                    },
                },
            )
            print_observability_stage("provenance and zero-OpenAI evidence write", "completed")

            inventory_pre_manifest = combined_inventory_snapshot()
            manifest_existing_set = {
                rel_path for rel_path in inventory_pre_manifest.keys() if rel_path in approved_allowlist_rel
            }
            manifest_existing_set.add(relative_to_repo(runner_paths["created_files_json"]))

            write_json(
                runner_paths["created_files_json"],
                {
                    "expected_files": sorted(approved_allowlist_rel),
                    "confirmed_existing_when_manifest_written": sorted(manifest_existing_set),
                    "missing_expected_files_at_manifest_write": sorted(
                        approved_allowlist_rel - manifest_existing_set
                    ),
                    "unexpected_files_at_manifest_write": sorted(
                        manifest_existing_set - approved_allowlist_rel
                    ),
                },
            )

            print_observability_stage("final integrity validation", "started")
            final_inventory = combined_inventory_snapshot()
            final_actual_output_set = {
                rel_path for rel_path in final_inventory.keys() if rel_path not in before_inventory
            }
            missing_expected = sorted(approved_allowlist_rel - final_actual_output_set)
            unexpected_created = sorted(final_actual_output_set - approved_allowlist_rel)
            incorrect_prefix = sorted(
                rel_path
                for rel_path in final_actual_output_set
                if not Path(rel_path).name.startswith(config.prefix)
            )
            final_exact_set_ok = not missing_expected and not unexpected_created and not incorrect_prefix

            final_inventory_delta = inventory_diff(
                before=before_inventory,
                after=final_inventory,
                approved_allowlist=approved_allowlist_rel,
            )
            if not final_inventory_delta["ok"]:
                raise SafetyError("Final inventory comparison failed.")

            protected_after = protected_snapshot()
            protected_changed_final = [
                rel_path
                for rel_path in protected_before
                if rel_path not in protected_after
                or protected_before[rel_path]["size_bytes"] != protected_after[rel_path]["size_bytes"]
                or protected_before[rel_path]["sha256"] != protected_after[rel_path]["sha256"]
            ]
            if protected_changed_final:
                raise SafetyError("Historical file snapshot changed after replay run.")

            if not final_exact_set_ok:
                raise SafetyError("Final output set does not exactly match approved write allowlist.")
            print_observability_stage("final integrity validation", "completed")

            print(
                json.dumps(
                    {
                        "status": "SMOKE_TEST_COMPLETED",
                        "final_exact_set_ok": final_exact_set_ok,
                        "missing_expected": missing_expected,
                        "unexpected_created": unexpected_created,
                        "incorrect_prefix": incorrect_prefix,
                    },
                    indent=2,
                ),
                flush=True,
            )
            return 0

    except Exception as exc:
        final_inventory = combined_inventory_snapshot()
        partial_files = sorted(rel_path for rel_path in final_inventory.keys() if rel_path not in before_inventory)
        print(
            json.dumps(
                {
                    "status": "FAILED_SMOKE_TEST",
                    "error_type": exc.__class__.__name__,
                    "error": str(exc),
                    "traceback": traceback.format_exc(),
                    "partial_created_files": partial_files,
                    "retry_rule": (
                        "Do not delete or overwrite partial outputs. "
                        f"Use a new unique prefix beginning with '{SMOKE_PREFIX_REQUIRED}' for any retry."
                    ),
                },
                indent=2,
            ),
            flush=True,
        )
        return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fixed-input deterministic replay runner for Experiment 1.")
    parser.add_argument("--mode", choices=("dry-run", "smoke"), default="dry-run")
    parser.add_argument(
        "--smoke-prefix",
        default=SMOKE_PREFIX_DEFAULT,
        help=f"Must begin with {SMOKE_PREFIX_REQUIRED}",
    )
    parser.add_argument(
        "--future-approval-full-run",
        action="store_true",
        help="Reserved for a future explicit 1,000-user replay. Disabled now.",
    )
    args = parser.parse_args(argv)

    if args.future_approval_full_run:
        raise SystemExit(
            "Full 1,000-user replay is intentionally disabled and not implemented here."
        )

    config = smoke_config(args.smoke_prefix)

    try:
        print_observability_stage("runner execution", "started")
        if args.mode == "dry-run":
            payload = dry_run_payload(config)
            print(json.dumps(payload, indent=2), flush=True)
            print(payload["verdict"], flush=True)
            print_observability_stage("normal process exit", "started")
            print_observability_stage("normal process exit", "completed")
            return 0 if payload["directory_inventories_identical"] else 1
        result = run_smoke(config)
        if result == 0:
            print_observability_stage("normal process exit", "started")
            print_observability_stage("normal process exit", "completed")
        return result
    except Exception as exc:
        print(
            json.dumps(
                {
                    "verdict": "UNSAFE_TO_SMOKE_TEST",
                    "error_type": exc.__class__.__name__,
                    "error": str(exc),
                    "traceback": traceback.format_exc(),
                },
                indent=2,
            ),
            flush=True,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
