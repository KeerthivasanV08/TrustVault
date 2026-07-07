from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from app.core import storage_paths
from app.utils.file_utils import ensure_parent_dir

PROCESSED_DIR = storage_paths.PROCESSED_DIR

CONTROL_FILE = PROCESSED_DIR / "control_decisions.csv"
REPORT_FILE = PROCESSED_DIR / "reports.csv"
EXPLAIN_FILE = PROCESSED_DIR / "explainability_log.csv"

CONTROL_COLUMNS = [
    "decision_id",
    "timestamp",
    "gate",
    "user_id",
    "transaction_id",
    "decision",
    "reason",
    "severity",
    "requires_review",
    "metadata",
]

REPORT_COLUMNS = [
    "report_id",
    "timestamp",
    "report_type",
    "user_id",
    "transaction_id",
    "decision",
    "final_score",
    "behavior_score",
    "sequence_score",
    "graph_score",
    "rule_score",
    "officer_recommendation",
    "immediate_action",
    "reason",
    "reasons",
    "amount",
    "source_engine",
    "escalation_level",
    "review_status",
    "evidence",
    "metadata",
]

EXPLAIN_COLUMNS = [
    "event_id",
    "timestamp",
    "report_id",
    "gate",
    "user_id",
    "transaction_id",
    "category",
    "finding",
    "evidence",
    "metadata",
]


def _ensure_processed_dir() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_json(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, default=str, ensure_ascii=False)
    except Exception:
        return str(value)


def _append_row(path: Path, row: Mapping[str, Any], columns: list[str]) -> None:
    _ensure_processed_dir()
    ensure_parent_dir(path)
    dataframe = pd.DataFrame([{column: row.get(column, "") for column in columns}])
    dataframe.to_csv(path, mode="a", header=not path.exists(), index=False)


def log_control_decision(record: Mapping[str, Any]) -> None:
    row = {
        "decision_id": record.get("decision_id", str(uuid.uuid4())),
        "timestamp": record.get("timestamp", _now()),
        "gate": record.get("gate", "UNKNOWN"),
        "user_id": record.get("user_id", ""),
        "transaction_id": record.get("transaction_id", ""),
        "decision": record.get("decision", ""),
        "reason": record.get("reason", ""),
        "severity": record.get("severity", "MEDIUM"),
        "requires_review": bool(record.get("requires_review", False)),
        "metadata": _to_json(record.get("metadata", {})),
    }
    _append_row(CONTROL_FILE, row, CONTROL_COLUMNS)


def log_report(record: Mapping[str, Any]) -> None:
    row = {
        "report_id": record.get("report_id", str(uuid.uuid4())),
        "timestamp": record.get("timestamp", _now()),
        "report_type": record.get("report_type", "UNKNOWN"),
        "user_id": record.get("user_id", ""),
        "transaction_id": record.get("transaction_id", ""),
        "decision": record.get("decision", ""),
        "final_score": record.get("final_score", 0),
        "behavior_score": record.get("behavior_score", 0),
        "sequence_score": record.get("sequence_score", 0),
        "graph_score": record.get("graph_score", 0),
        "rule_score": record.get("rule_score", 0),
        "officer_recommendation": record.get("officer_recommendation", ""),
        "immediate_action": record.get("immediate_action", ""),
        "reason": record.get("reason", ""),
        "reasons": _to_json(record.get("reasons", [])),
        "amount": record.get("amount", 0),
        "source_engine": record.get("source_engine", ""),
        "escalation_level": record.get("escalation_level", ""),
        "review_status": record.get("review_status", ""),
        "evidence": _to_json(record.get("evidence", [])),
        "metadata": _to_json(record.get("metadata", {})),
    }
    _append_row(REPORT_FILE, row, REPORT_COLUMNS)
    return row["report_id"]


def log_explainability(record: Mapping[str, Any]) -> None:
    row = {
        "event_id": record.get("event_id", str(uuid.uuid4())),
        "timestamp": record.get("timestamp", _now()),
        "report_id": record.get("report_id", ""),
        "gate": record.get("gate", "UNKNOWN"),
        "user_id": record.get("user_id", ""),
        "transaction_id": record.get("transaction_id", ""),
        "category": record.get("category", "UNKNOWN"),
        "finding": record.get("finding", "UNKNOWN"),
        "evidence": _to_json(record.get("evidence", {})),
        "metadata": _to_json(record.get("metadata", {})),
    }
    _append_row(EXPLAIN_FILE, row, EXPLAIN_COLUMNS)