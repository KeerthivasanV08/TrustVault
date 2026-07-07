from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

import pandas as pd

from app.core import storage_paths
from app.utils.file_utils import ensure_parent_dir

logger = logging.getLogger(__name__)

AUDIT_DIR = storage_paths.AUDIT_DIR
TRANSACTION_AUDIT_FILE = AUDIT_DIR / "transaction_audit.csv"
ML_AUDIT_FILE = AUDIT_DIR / "ml_audit.csv"
OFFICER_AUDIT_FILE = AUDIT_DIR / "officer_audit.csv"
EXPLAINABILITY_AUDIT_FILE = AUDIT_DIR / "explainability_audit.csv"

TRANSACTION_AUDIT_COLUMNS = [
    "event_id",
    "timestamp",
    "transaction_id",
    "user_id",
    "decision",
    "risk_score",
    "priority",
    "reasons",
    "rule_hits",
]

ML_AUDIT_COLUMNS = [
    "event_id",
    "timestamp",
    "transaction_id",
    "behavior_score",
    "sequence_score",
    "graph_score",
    "final_score",
]

OFFICER_AUDIT_COLUMNS = [
    "event_id",
    "timestamp",
    "officer_id",
    "action",
    "case_id",
    "notes",
]

EXPLAINABILITY_AUDIT_COLUMNS = [
    "event_id",
    "timestamp",
    "transaction_id",
    "user_id",
    "category",
    "finding",
    "evidence",
    "metadata",
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, default=str, ensure_ascii=False)
    except Exception:
        return str(value)


def _ensure_audit_dir() -> None:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)


def _seed_csv(path: Path, columns: Sequence[str]) -> None:
    ensure_parent_dir(path)
    if not path.exists():
        pd.DataFrame(columns=list(columns)).to_csv(path, index=False)


def initialize_transaction_audit_storage() -> None:
    storage_paths.initialize_storage_directories()
    _ensure_audit_dir()
    _seed_csv(TRANSACTION_AUDIT_FILE, TRANSACTION_AUDIT_COLUMNS)
    _seed_csv(ML_AUDIT_FILE, ML_AUDIT_COLUMNS)
    _seed_csv(OFFICER_AUDIT_FILE, OFFICER_AUDIT_COLUMNS)
    _seed_csv(EXPLAINABILITY_AUDIT_FILE, EXPLAINABILITY_AUDIT_COLUMNS)


def _append_row(path: Path, row: Mapping[str, Any], columns: Sequence[str]) -> str:
    _ensure_audit_dir()
    ensure_parent_dir(path)

    payload = {column: row.get(column, "") for column in columns}
    frame = pd.DataFrame([payload])
    frame.to_csv(path, mode="a", header=not path.exists(), index=False)
    return str(payload.get("event_id", ""))


def log_transaction_decision(
    transaction_id: str,
    user_id: str,
    decision: str,
    risk_score: float = 0.0,
    priority: str = "UNKNOWN",
    reasons: Any = None,
    rule_hits: Any = None,
    timestamp: str | None = None,
) -> str:
    row = {
        "event_id": str(uuid.uuid4()),
        "timestamp": timestamp or _now(),
        "transaction_id": transaction_id,
        "user_id": user_id,
        "decision": decision,
        "risk_score": risk_score,
        "priority": priority,
        "reasons": _stringify(reasons or []),
        "rule_hits": _stringify(rule_hits or []),
    }
    return _append_row(TRANSACTION_AUDIT_FILE, row, TRANSACTION_AUDIT_COLUMNS)


def log_control_decision(
    entity_id: str | None = None,
    entity_type: str | None = None,
    decision: str | None = None,
    reason: Any = None,
    transaction_id: str | None = None,
    user_id: str | None = None,
    risk_score: float = 0.0,
    priority: str = "UNKNOWN",
    rule_hits: Any = None,
    timestamp: str | None = None,
    **_: Any,
) -> str:
    resolved_transaction_id = transaction_id or entity_id or ""
    resolved_user_id = user_id or entity_id or ""
    resolved_decision = decision or "UNKNOWN"
    resolved_priority = priority if priority != "UNKNOWN" else resolved_decision
    resolved_rule_hits = rule_hits if rule_hits is not None else [reason] if reason else []

    return log_transaction_decision(
        transaction_id=resolved_transaction_id,
        user_id=resolved_user_id,
        decision=resolved_decision,
        risk_score=risk_score,
        priority=resolved_priority,
        reasons=reason if reason is not None else [],
        rule_hits=resolved_rule_hits,
        timestamp=timestamp,
    )


def log_ml_scores(
    transaction_id: str,
    behavior_score: float = 0.0,
    sequence_score: float = 0.0,
    graph_score: float = 0.0,
    final_score: float = 0.0,
    timestamp: str | None = None,
) -> str:
    row = {
        "event_id": str(uuid.uuid4()),
        "timestamp": timestamp or _now(),
        "transaction_id": transaction_id,
        "behavior_score": behavior_score,
        "sequence_score": sequence_score,
        "graph_score": graph_score,
        "final_score": final_score,
    }
    return _append_row(ML_AUDIT_FILE, row, ML_AUDIT_COLUMNS)


def log_officer_action(
    officer_id: str,
    action: str,
    case_id: str | None = None,
    notes: str | None = None,
    timestamp: str | None = None,
) -> str:
    row = {
        "event_id": str(uuid.uuid4()),
        "timestamp": timestamp or _now(),
        "officer_id": officer_id,
        "action": action,
        "case_id": case_id or "",
        "notes": notes or "",
    }
    return _append_row(OFFICER_AUDIT_FILE, row, OFFICER_AUDIT_COLUMNS)


def log_explainability_event(
    transaction_id: str,
    category: str,
    finding: str,
    user_id: str | None = None,
    evidence: Any = None,
    metadata: Any = None,
    timestamp: str | None = None,
) -> str:
    row = {
        "event_id": str(uuid.uuid4()),
        "timestamp": timestamp or _now(),
        "transaction_id": transaction_id,
        "user_id": user_id or "",
        "category": category,
        "finding": finding,
        "evidence": _stringify(evidence if evidence is not None else {}),
        "metadata": _stringify(metadata if metadata is not None else {}),
    }
    return _append_row(EXPLAINABILITY_AUDIT_FILE, row, EXPLAINABILITY_AUDIT_COLUMNS)


class AuditService:
    def log_transaction_decision(self, *args: Any, **kwargs: Any) -> str:
        return log_transaction_decision(*args, **kwargs)

    def log_control_decision(self, *args: Any, **kwargs: Any) -> str:
        return log_control_decision(*args, **kwargs)

    def log_ml_scores(self, *args: Any, **kwargs: Any) -> str:
        return log_ml_scores(*args, **kwargs)

    def log_officer_action(self, *args: Any, **kwargs: Any) -> str:
        return log_officer_action(*args, **kwargs)

    def log_explainability_event(self, *args: Any, **kwargs: Any) -> str:
        return log_explainability_event(*args, **kwargs)

    def log_all(self, txn: Mapping[str, Any], decision: Mapping[str, Any], evidence: Sequence[Mapping[str, Any]] | None) -> None:
        transaction_id = str(txn.get("trans_id") or txn.get("transaction_id") or "")
        user_id = str(txn.get("sender_id") or txn.get("user_id") or "")
        reasons = decision.get("reasons") or decision.get("reason") or []
        rule_hits = decision.get("rule_hits") or decision.get("control_reasons") or reasons

        self.log_transaction_decision(
            transaction_id=transaction_id,
            user_id=user_id,
            decision=str(decision.get("decision") or decision.get("immediate_action") or "UNKNOWN"),
            risk_score=float(decision.get("final_score", 0) or 0),
            priority=str(decision.get("officer_recommendation") or decision.get("priority") or "UNKNOWN"),
            reasons=reasons,
            rule_hits=rule_hits,
        )

        self.log_ml_scores(
            transaction_id=transaction_id,
            behavior_score=float(decision.get("behavior_score", 0) or 0),
            sequence_score=float(decision.get("sequence_score", 0) or 0),
            graph_score=float(decision.get("graph_score", 0) or 0),
            final_score=float(decision.get("final_score", 0) or 0),
        )

        for item in evidence or []:
            self.log_explainability_event(
                transaction_id=transaction_id,
                user_id=user_id,
                category=str(item.get("category", "UNKNOWN")),
                finding=str(item.get("finding", "UNKNOWN")),
                evidence=item,
                metadata={
                    "source": "AuditService.log_all",
                },
            )


__all__ = [
    "AuditService",
    "initialize_transaction_audit_storage",
    "log_control_decision",
    "log_transaction_decision",
    "log_ml_scores",
    "log_officer_action",
    "log_explainability_event",
]
