from __future__ import annotations

import shutil
import uuid
from pathlib import Path

import pandas as pd

from app.core import storage_paths


LEGACY_ONBOARDING_FILES = [
    storage_paths.PROCESSED_DIR / "onboarding_results.csv",
    storage_paths.AUDIT_DIR / "onboarding_results.csv",
]


def _load(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def main() -> None:
    snapshot_frames = []
    audit_frames = []
    for path in LEGACY_ONBOARDING_FILES:
        frame = _load(path)
        if frame.empty:
            continue
        if "event_id" in frame.columns or "decision" in frame.columns:
            audit_frames.append(frame)
        else:
            snapshot_frames.append(frame)

    if snapshot_frames:
        snapshot = pd.concat(snapshot_frames, ignore_index=True, sort=False)
        if "user_id" in snapshot.columns:
            snapshot = snapshot.drop_duplicates(subset=["user_id"], keep="last")
        storage_paths.ONBOARDING_RISK_SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
        snapshot.to_csv(storage_paths.ONBOARDING_RISK_SNAPSHOT_PATH, index=False)
        print(f"Wrote snapshot rows: {len(snapshot)}")

    if audit_frames:
        audit = pd.concat(audit_frames, ignore_index=True, sort=False)
        if "event_id" not in audit.columns:
            audit["event_id"] = [str(uuid.uuid4()) for _ in range(len(audit))]
        if "runtime_session_id" not in audit.columns:
            audit["runtime_session_id"] = ""
        audit = audit.drop_duplicates(subset=["event_id"], keep="last")
        storage_paths.ONBOARDING_DECISIONS_AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
        audit.to_csv(storage_paths.ONBOARDING_DECISIONS_AUDIT_PATH, index=False)
        print(f"Wrote audit rows: {len(audit)}")

    archive_dir = storage_paths.ARCHIVE_DIR / "onboarding"
    archive_dir.mkdir(parents=True, exist_ok=True)
    for path in LEGACY_ONBOARDING_FILES:
        if path.exists():
            shutil.move(str(path), str(archive_dir / path.name))


if __name__ == "__main__":
    main()