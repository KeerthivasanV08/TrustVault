from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Dict, Iterable, List

import pandas as pd

from app.core import storage_paths
from app.utils.file_utils import ensure_parent_dir


CASE_COLUMNS = [
    "case_id",
    "source_alert_id",
    "source_type",
    "user_id",
    "transaction_id",
    "priority",
    "status",
    "assigned_officer",
    "assigned_team",
    "creation_source",
    "reason",
    "evidence",
    "created_at",
    "updated_at",
    "sla_deadline",
    "escalation_level",
    "freeze_status",
    "sar_status",
    "resolution",
    "runtime_session_id",
]

_LOCK = Lock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_write(frame: pd.DataFrame, path: Path) -> None:
    ensure_parent_dir(path)
    tmp_path = path.with_suffix(".tmp")
    frame.to_csv(tmp_path, index=False)
    tmp_path.replace(path)


def _normalize_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, default=str, ensure_ascii=False)
    except Exception:
        return str(value)


class CaseRepository:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or storage_paths.CASE_REGISTRY_PATH
        ensure_parent_dir(self.path)

    def _empty_frame(self) -> pd.DataFrame:
        return pd.DataFrame(columns=CASE_COLUMNS)

    def _read_frame(self) -> pd.DataFrame:
        if not self.path.exists():
            return self._empty_frame()
        try:
            frame = pd.read_csv(self.path)
        except Exception:
            return self._empty_frame()
        for column in CASE_COLUMNS:
            if column not in frame.columns:
                frame[column] = ""
        return frame[CASE_COLUMNS]

    def list_cases(self) -> List[Dict[str, Any]]:
        frame = self._read_frame()
        if frame.empty:
            return []
        frame = frame.drop_duplicates(subset=["case_id"], keep="last")
        return frame.to_dict(orient="records")

    def get_case(self, case_id: str) -> Dict[str, Any] | None:
        frame = self._read_frame()
        if frame.empty:
            return None
        rows = frame[frame["case_id"].astype(str) == str(case_id)]
        if rows.empty:
            return None
        return rows.tail(1).iloc[0].to_dict()

    def upsert_case(self, record: Dict[str, Any]) -> Dict[str, Any]:
        with _LOCK:
            frame = self._read_frame()
            case_id = str(record.get("case_id") or "").strip()
            if not case_id:
                raise ValueError("case_id is required")

            now = _now()
            payload = {column: _normalize_value(record.get(column, "")) for column in CASE_COLUMNS}
            payload["case_id"] = case_id
            payload["updated_at"] = now
            if not payload.get("created_at"):
                payload["created_at"] = now

            if frame.empty:
                frame = pd.DataFrame([payload], columns=CASE_COLUMNS)
            else:
                frame = frame[frame["case_id"].astype(str) != case_id]
                frame = pd.concat([frame, pd.DataFrame([payload], columns=CASE_COLUMNS)], ignore_index=True)

            frame = frame.drop_duplicates(subset=["case_id"], keep="last")
            _atomic_write(frame[CASE_COLUMNS], self.path)
            return payload

    def normalize_legacy_records(self, records: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalized: List[Dict[str, Any]] = []
        for record in records:
            case_id = str(record.get("case_id") or record.get("id") or "").strip()
            if not case_id:
                continue
            normalized.append({
                "case_id": case_id,
                "source_alert_id": record.get("source_alert_id") or record.get("source_alert") or record.get("alert_id") or "",
                "source_type": record.get("source_type") or record.get("alert_type") or "CASE",
                "user_id": record.get("user_id") or "",
                "transaction_id": record.get("transaction_id") or record.get("txn_id") or "",
                "priority": record.get("priority") or "P3",
                "status": record.get("status") or "OPEN",
                "assigned_officer": record.get("assigned_officer") or record.get("assigned_to") or "",
                "assigned_team": record.get("assigned_team") or "",
                "creation_source": record.get("creation_source") or record.get("source_type") or "AUTO_ALERT",
                "reason": record.get("reason") or record.get("evidence_summary") or "",
                "evidence": record.get("evidence") or record.get("evidence_summary") or "",
                "created_at": record.get("created_at") or _now(),
                "updated_at": record.get("updated_at") or record.get("created_at") or _now(),
                "sla_deadline": record.get("sla_deadline") or "",
                "escalation_level": record.get("escalation_level") or "",
                "freeze_status": record.get("freeze_status") or record.get("status") or "",
                "sar_status": record.get("sar_status") or "",
                "resolution": record.get("resolution") or "",
                "runtime_session_id": record.get("runtime_session_id") or "",
            })
        return normalized


case_repository = CaseRepository()