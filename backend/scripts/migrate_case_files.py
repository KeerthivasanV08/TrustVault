from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd

from app.core import storage_paths
from app.services.cases.case_repository import case_repository


LEGACY_CASE_FILES = [
    storage_paths.PROCESSED_DIR / "alerts" / "case_registry.csv",
    storage_paths.PROCESSED_DIR / "officer_cases.csv",
    storage_paths.CASES_DIR / "officer_cases.csv",
]


def _load(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def main() -> None:
    frames = []
    for path in LEGACY_CASE_FILES:
        frame = _load(path)
        if not frame.empty:
            frames.append(frame)

    if not frames:
        print("No legacy case files found.")
        return

    combined = pd.concat(frames, ignore_index=True, sort=False)
    normalized = case_repository.normalize_legacy_records(combined.to_dict(orient="records"))
    output = pd.DataFrame(normalized)
    before = len(combined)
    if not output.empty:
        if "updated_at" in output.columns:
            output["updated_at"] = output["updated_at"].fillna("")
        output = output.drop_duplicates(subset=["case_id"], keep="last")
    output.to_csv(storage_paths.CASE_REGISTRY_PATH, index=False)

    archive_dir = storage_paths.ARCHIVE_DIR / "cases"
    archive_dir.mkdir(parents=True, exist_ok=True)
    for path in LEGACY_CASE_FILES:
        if path.exists():
            shutil.move(str(path), str(archive_dir / path.name))

    print(f"Loaded {before} legacy rows; wrote {len(output)} canonical rows to {storage_paths.CASE_REGISTRY_PATH}")


if __name__ == "__main__":
    main()