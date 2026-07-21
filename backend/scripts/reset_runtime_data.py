from __future__ import annotations

import argparse
import shutil
from pathlib import Path

import pandas as pd

from app.core import storage_paths
from app.realtime.transaction_memory_store import (
    RECENT_TRANSACTIONS_PATH,
    USER_VELOCITY_STATE_PATH,
)
from app.services.alerts.alert_storage_service import DEFAULT_HEADERS, FILES, BASE_DIR as ALERTS_BASE_DIR
from app.services.cases.case_repository import case_repository
from app.core.runtime_context import get_runtime_session_id


RUNTIME_DIR = storage_paths.RUNTIME_DIR


def _write_empty_csv(path: Path, columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(columns=columns).to_csv(path, index=False)


def reset_runtime_files() -> None:
    _write_empty_csv(RECENT_TRANSACTIONS_PATH, [
        "trans_id",
        "sender_id",
        "receiver_id",
        "amount",
        "timestamp",
    ])
    _write_empty_csv(USER_VELOCITY_STATE_PATH, [
        "user_id",
        "rolling_24h_sum",
        "txn_count_24h",
        "unique_counterparties_24h",
        "drain_ratio",
        "round_number_ratio",
        "near_threshold_count",
        "avg_holding_time_mins",
        "velocity_gradient",
        "last_updated",
    ])
    print(f"Reset runtime files in {RUNTIME_DIR}")


def reset_alert_files() -> None:
    for key, filename in FILES.items():
        path = Path(ALERTS_BASE_DIR) / filename
        columns = DEFAULT_HEADERS[key]
        _write_empty_csv(path, columns)
    print(f"Reset alert ledgers in {ALERTS_BASE_DIR}")


def reset_cases(session_id: str | None = None) -> None:
    if not storage_paths.CASE_REGISTRY_PATH.exists():
        return
    frame = pd.read_csv(storage_paths.CASE_REGISTRY_PATH)
    if session_id:
        if "runtime_session_id" in frame.columns:
            frame = frame[frame["runtime_session_id"].astype(str) != str(session_id)]
    else:
        frame = frame.iloc[0:0]
    columns = list(frame.columns) if not frame.empty else list(case_repository._empty_frame().columns)
    _write_empty_csv(storage_paths.CASE_REGISTRY_PATH, columns)
    if not frame.empty:
        frame.to_csv(storage_paths.CASE_REGISTRY_PATH, index=False)


def archive_legacy_case_files() -> None:
    archive_dir = storage_paths.ARCHIVE_DIR / "cases"
    archive_dir.mkdir(parents=True, exist_ok=True)
    for path in [
        storage_paths.PROCESSED_DIR / "alerts" / "case_registry.csv",
        storage_paths.PROCESSED_DIR / "officer_cases.csv",
        storage_paths.CASES_DIR / "officer_cases.csv",
    ]:
        if path.exists():
            shutil.move(str(path), str(archive_dir / path.name))


def main() -> None:
    parser = argparse.ArgumentParser(description="Reset bounded runtime CSV snapshots for TrustVault.")
    parser.add_argument(
        "--alerts",
        action="store_true",
        help="Also clear alert ledgers under data/processed/alerts",
    )
    parser.add_argument("--cases", action="store_true", help="Clear runtime cases from the canonical registry")
    parser.add_argument("--session-id", default="", help="Only clear rows for the given runtime session id")
    parser.add_argument("--all-runtime", action="store_true", help="Clear all runtime/demo operational CSV state")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without modifying files")
    args = parser.parse_args()

    print(f"Runtime session: {get_runtime_session_id()}")
    print(f"Affecting runtime files under {RUNTIME_DIR}")
    if args.dry_run:
        return

    reset_runtime_files()
    if args.alerts:
        reset_alert_files()
    if args.cases or args.all_runtime:
        reset_cases(args.session_id or None)
        archive_legacy_case_files()


if __name__ == "__main__":
    main()
