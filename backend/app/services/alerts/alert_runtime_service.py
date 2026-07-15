from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional

from app.services.cases.case_repository import case_repository
from .investigator_assignment_service import get_investigator_profile


def _parse_datetime(value: Any) -> Optional[datetime]:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value) / 1000.0 if float(value) > 10_000_000_000 else float(value), tz=timezone.utc)
        except Exception:
            return None
    text = str(value).strip()
    if not text:
        return None
    try:
        normalized = text.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        return parsed.astimezone(timezone.utc) if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _format_datetime(value: Optional[datetime]) -> str:
    if value is None:
        return ""
    return value.astimezone(timezone.utc).isoformat()


def _coerce_int(value: Any, default: int = 0) -> int:
    try:
        if value in (None, ""):
            return default
        return int(float(value))
    except Exception:
        return default


def _coerce_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except Exception:
        return default


def _build_case_index() -> Dict[str, Dict[str, Any]]:
    index: Dict[str, Dict[str, Any]] = {}
    try:
        for case in case_repository.list_cases():
            case_id = str(case.get("case_id") or "").strip()
            if case_id:
                index[case_id] = case
            source_alert_id = str(case.get("source_alert_id") or "").strip()
            if source_alert_id and source_alert_id not in index:
                index[source_alert_id] = case
    except Exception:
        pass
    return index


def _extract_alert_case(alert: Dict[str, Any], case_index: Dict[str, Dict[str, Any]] | None = None) -> Dict[str, Any]:
    case_id = str(alert.get("case_id") or alert.get("source_case_id") or alert.get("converted_case", {}).get("case_id") or "").strip()
    if case_id:
        case = case_index.get(case_id) if case_index else case_repository.get_case(case_id)
        if case:
            return case

    source_alert_id = str(alert.get("alert_id") or alert.get("source_alert_id") or "").strip()
    if not source_alert_id:
        return {}

    if case_index and source_alert_id in case_index:
        return case_index[source_alert_id]

    for case in case_repository.list_cases():
        if str(case.get("source_alert_id", "")).strip() == source_alert_id:
            return case
    return {}


def _map_case_status(status: str, fallback: str) -> str:
    normalized = str(status or fallback or "OPEN").upper()
    return {
        "FROZEN": "ACCOUNT_FROZEN",
        "SAR_FILED": "SAR_GENERATED",
        "GENERATED": "SAR_GENERATED",
        "ACK": "UNDER_REVIEW",
        "ACKNOWLEDGED": "UNDER_REVIEW",
        "IN_REVIEW": "UNDER_REVIEW",
        "REVIEW": "UNDER_REVIEW",
        "CLOSED": "CLOSED",
        "ESCALATED": "ESCALATED",
        "EDD_REQUESTED": "EDD_REQUESTED",
        "OPEN": "OPEN",
    }.get(normalized, normalized)


def build_alert_dto(alert: Dict[str, Any], alert_type: str = "transaction", case_index: Dict[str, Dict[str, Any]] | None = None) -> Dict[str, Any]:
    metadata = alert.get("metadata") if isinstance(alert.get("metadata"), dict) else {}
    case = _extract_alert_case(alert, case_index=case_index)

    created_at = _parse_datetime(
        alert.get("created_at")
        or alert.get("createdAt")
        or alert.get("timestamp")
        or metadata.get("timestamp")
        or metadata.get("created_at")
    )
    if created_at is None:
        created_at = datetime.now(timezone.utc)

    risk_score = _coerce_float(
        alert.get("risk_score")
        or alert.get("final_score")
        or metadata.get("final_score")
        or metadata.get("risk_score")
    )
    priority = str(alert.get("priority") or metadata.get("priority") or "P3").upper()
    severity = str(alert.get("severity") or metadata.get("severity") or "MEDIUM").upper()
    queue = str(alert.get("assigned_queue") or alert.get("queue") or metadata.get("queue") or "").strip() or {
        "P1": "AML_CRITICAL_QUEUE",
        "P2": "AML_REVIEW_QUEUE",
        "P3": "AML_MONITORING_QUEUE",
        "INFO": "AML_INFO_QUEUE",
    }.get(priority, "AML_MONITORING_QUEUE")

    transaction_id = str(
        alert.get("transaction_id")
        or alert.get("trans_id")
        or metadata.get("transaction_id")
        or metadata.get("trans_id")
        or ""
    ).strip()
    user_id = str(
        alert.get("user_id")
        or alert.get("sender_id")
        or metadata.get("user_id")
        or metadata.get("sender_id")
        or ""
    ).strip()

    sla_minutes = _coerce_int(alert.get("sla_minutes") or (alert.get("sla") or {}).get("sla_minutes") or metadata.get("sla_minutes"), 0)
    sla_due_at = _parse_datetime(alert.get("sla_due_at") or (alert.get("sla") or {}).get("due_at") or metadata.get("sla_due_at"))
    if sla_due_at is None and sla_minutes > 0:
        sla_due_at = created_at + timedelta(minutes=sla_minutes)
    elif sla_due_at is None:
        sla_due_at = created_at

    now = datetime.now(timezone.utc)
    remaining_seconds = int((sla_due_at - now).total_seconds())
    sla_breached = remaining_seconds < 0

    assigned_officer_id = str(
        alert.get("assigned_officer_id")
        or case.get("assigned_officer")
        or alert.get("assigned_officer")
        or ""
    ).strip()
    assigned_profile = get_investigator_profile(assigned_officer_id) if assigned_officer_id else {}
    assigned_officer_name = str(
        alert.get("assigned_officer_name")
        or assigned_profile.get("assigned_officer_name")
        or alert.get("assigned_officer")
        or case.get("assigned_officer")
        or assigned_officer_id
        or ""
    ).strip()
    assigned_at = _format_datetime(_parse_datetime(alert.get("assigned_at") or assigned_profile.get("last_assigned_at")))
    case_id = str(alert.get("case_id") or case.get("case_id") or "").strip()
    status = _map_case_status(case.get("status") or alert.get("status") or alert.get("state") or "OPEN", alert.get("state") or "OPEN")
    state = status

    payload: Dict[str, Any] = {
        "alert_id": str(alert.get("alert_id") or alert.get("alertId") or "").strip(),
        "transaction_id": transaction_id,
        "user_id": user_id,
        "risk_score": risk_score,
        "priority": priority,
        "severity": severity,
        "queue": queue,
        "assigned_officer_id": assigned_officer_id,
        "assigned_officer_name": assigned_officer_name,
        "assigned_officer": assigned_officer_name,
        "assigned_at": assigned_at,
        "status": status,
        "state": state,
        "created_at": _format_datetime(created_at),
        "sla_due_at": _format_datetime(sla_due_at),
        "remaining_seconds": remaining_seconds,
        "sla_breached": sla_breached,
        "case_id": case_id,
        "alert_type": alert.get("alert_type") or metadata.get("alert_type") or ("TRANSACTION_SUSPECT" if alert_type == "transaction" else "ONBOARDING_SUSPECT"),
        "decision": alert.get("decision") or metadata.get("decision") or "",
        "behavior_score": _coerce_float(alert.get("behavior_score") or metadata.get("behavior_score")),
        "sequence_score": _coerce_float(alert.get("sequence_score") or metadata.get("sequence_score")),
        "graph_score": _coerce_float(alert.get("graph_score") or metadata.get("graph_score")),
        "requires_edd": bool(alert.get("requires_edd") or metadata.get("requires_edd") or False),
        "metadata": metadata,
    }

    if alert.get("sla"):
        payload["sla"] = alert.get("sla")
    if alert.get("converted_case"):
        payload["converted_case"] = alert.get("converted_case")

    return payload


def build_alert_collection(alerts: list[Dict[str, Any]], alert_type: str = "transaction") -> list[Dict[str, Any]]:
    case_index = _build_case_index()
    return [build_alert_dto(alert, alert_type=alert_type, case_index=case_index) for alert in alerts]
