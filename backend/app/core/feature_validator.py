from __future__ import annotations

import logging

import pandas as pd

from app.core.feature_schema import (
    BEHAVIOR_CATEGORICAL_FEATURES,
    BEHAVIOR_FEATURE_ORDER,
    BEHAVIOR_NUMERIC_FEATURES,
)

logger = logging.getLogger(__name__)


def _log_validation_issue(message: str) -> None:
    try:
        logger.warning(message)
    except Exception:
        pass


def validate_behavior_features(df: pd.DataFrame) -> pd.DataFrame:
    frame = df.copy()

    unexpected = [column for column in frame.columns if column not in BEHAVIOR_FEATURE_ORDER]
    if unexpected:
        _log_validation_issue(f"[FEATURES] Unexpected columns dropped: {unexpected}")
        frame = frame.drop(columns=unexpected, errors="ignore")

    missing = [column for column in BEHAVIOR_FEATURE_ORDER if column not in frame.columns]
    if missing:
        _log_validation_issue(f"[FEATURES] Missing columns filled with defaults: {missing}")
        for column in missing:
            frame[column] = 0 if column in BEHAVIOR_NUMERIC_FEATURES else "UNKNOWN"

    for column in BEHAVIOR_NUMERIC_FEATURES:
        if column in frame.columns:
            try:
                frame[column] = pd.to_numeric(frame[column], errors="coerce").fillna(0)
            except Exception:
                frame[column] = 0

    for column in BEHAVIOR_CATEGORICAL_FEATURES:
        if column in frame.columns:
            try:
                frame[column] = frame[column].astype("string").fillna("UNKNOWN").astype("category")
            except Exception:
                frame[column] = pd.Series(["UNKNOWN"] * len(frame), dtype="category")

    return frame.reindex(columns=BEHAVIOR_FEATURE_ORDER)
