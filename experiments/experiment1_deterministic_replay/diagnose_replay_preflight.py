from __future__ import annotations

import faulthandler
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


START_TIME = time.perf_counter()
PROCESS_ID = os.getpid()


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def elapsed_seconds() -> float:
    return time.perf_counter() - START_TIME


def marker(stage_name: str, event: str, **details: object) -> None:
    fields = [
        utc_timestamp(),
        f"elapsed={elapsed_seconds():.3f}s",
        f"pid={PROCESS_ID}",
        f"stage={stage_name}",
        f"event={event}",
    ]
    for key, value in details.items():
        fields.append(f"{key}={value}")
    print(" | ".join(fields), flush=True)


def main() -> int:
    marker("script started", "before")
    faulthandler.enable()
    faulthandler.dump_traceback_later(30, repeat=True)
    marker("script started", "after")

    runner = None
    rows = None

    try:
        marker("standard-library imports", "before")
        import csv
        import hashlib
        import importlib.util
        import json
        marker("standard-library imports", "after")

        marker("project runner module import", "before")
        runner_path = Path(__file__).resolve().parent / "run_experiment1_frozen_replay.py"
        spec = importlib.util.spec_from_file_location(
            "experiment1_frozen_replay_runner_diagnostic",
            runner_path,
        )
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Unable to load runner module from {runner_path}")
        runner = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = runner
        spec.loader.exec_module(runner)
        marker("project runner module import", "after", runner_path=runner_path.name)

        marker("replay configuration/settings creation", "before")
        modules = runner.import_project_modules()
        Settings = modules["Settings"]
        config = runner.smoke_config("experiment1_deterministic_replay_smoke_diagnostic")
        base_settings = Settings()
        settings = runner.SettingsProxy(
            base_settings,
            processed_data_dir=runner.replay_processed_data_dir(config),
            processed_interactions_with_articles_csv_path=base_settings.processed_interactions_with_articles_csv_path,
            feedback_state_path=runner.feedback_override_path(config),
        )
        marker(
            "replay configuration/settings creation",
            "after",
            replay_processed_data_dir=str(settings.processed_data_dir),
            shared_processed_csv=str(settings.processed_interactions_with_articles_csv_path),
        )

        marker("frozen-input existence and size check", "before")
        frozen_path = runner.frozen_input_path()
        exists = frozen_path.exists()
        size_bytes = frozen_path.stat().st_size if exists else None
        marker(
            "frozen-input existence and size check",
            "after",
            exists=exists,
            size_bytes=size_bytes,
        )

        marker("frozen-input SHA-256 calculation", "before")
        frozen_sha256 = runner.sha256_file(frozen_path)
        marker("frozen-input SHA-256 calculation", "after", sha256=frozen_sha256)

        marker("frozen-input JSON loading", "before")
        rows = runner.load_json_rows(frozen_path)
        marker("frozen-input JSON loading", "after", row_count=len(rows))

        marker("frozen-row validation", "before")
        validation = runner.validate_frozen_rows(rows)
        marker(
            "frozen-row validation",
            "after",
            ok=validation["ok"],
            unique_customer_id_count=validation["unique_customer_id_count"],
        )

        marker("protected_snapshot() execution", "before")
        protected = runner.protected_snapshot()
        marker("protected_snapshot() execution", "after", protected_count=len(protected))

        marker("output allowlist construction", "before")
        allowlist = runner.declared_allowlist(settings, config)
        marker("output allowlist construction", "after", allowlist_count=len(allowlist))

        marker("supporting processed-interaction CSV existence and size check", "before")
        supporting_csv_path = runner.REPO_ROOT / runner.REQUIRED_SUPPORTING_INPUTS[0]
        supporting_exists = supporting_csv_path.exists()
        supporting_size_bytes = supporting_csv_path.stat().st_size if supporting_exists else None
        marker(
            "supporting processed-interaction CSV existence and size check",
            "after",
            exists=supporting_exists,
            size_bytes=supporting_size_bytes,
        )

        marker("optional read of only the CSV header and first row", "before")
        header_columns = 0
        first_row_columns = 0
        with supporting_csv_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.reader(handle)
            header = next(reader, [])
            first_row = next(reader, [])
            header_columns = len(header)
            first_row_columns = len(first_row)
        marker(
            "optional read of only the CSV header and first row",
            "after",
            header_columns=header_columns,
            first_row_columns=first_row_columns,
        )

        marker("diagnostic completed", "before")
        faulthandler.cancel_dump_traceback_later()
        marker("diagnostic completed", "after")
        return 0
    finally:
        faulthandler.cancel_dump_traceback_later()


if __name__ == "__main__":
    raise SystemExit(main())
