from fastapi import APIRouter, HTTPException
from typing import List
from app.realtime.transaction_memory_store import LIVE_ALERTS
from app.services.alerts.escalation_service import check_and_escalate
from app.services.officer.alert_management_service import alert_management_service
from app.services.officer.sla_breach_monitor import sla_breach_monitor
from app.services.alerts.alert_runtime_service import _parse_datetime


def _live_alert_snapshot(alert: dict) -> dict:
    snapshot = dict(alert)
    snapshot.setdefault("assigned_officer_name", snapshot.get("assigned_officer"))
    snapshot.setdefault("assigned_officer_id", snapshot.get("assigned_officer_id") or snapshot.get("assigned_officer"))
    snapshot.setdefault("transaction_id", snapshot.get("transaction_id") or snapshot.get("trans_id"))
    snapshot.setdefault("user_id", snapshot.get("user_id") or snapshot.get("sender_id"))
    snapshot.setdefault("queue", snapshot.get("assigned_queue") or snapshot.get("queue"))
    snapshot.setdefault("status", snapshot.get("status") or snapshot.get("state") or "OPEN")
    snapshot.setdefault("state", snapshot.get("state") or snapshot.get("status") or "OPEN")

    created_at = _parse_datetime(snapshot.get("created_at") or snapshot.get("timestamp") or snapshot.get("createdAt"))
    sla_due_at = _parse_datetime(snapshot.get("sla_due_at") or (snapshot.get("sla") or {}).get("due_at"))
    if created_at is not None and sla_due_at is not None:
        remaining_seconds = int((sla_due_at - __import__("datetime").datetime.now(__import__("datetime").timezone.utc)).total_seconds())
        snapshot["remaining_seconds"] = remaining_seconds
        snapshot["sla_breached"] = remaining_seconds < 0
    return snapshot

router = APIRouter()


@router.get("")
async def all_alerts():
    # return live alerts snapshot
    return [_live_alert_snapshot(alert) for alert in list(LIVE_ALERTS)]


@router.get("/p1")
async def p1_alerts():
    return [alert for alert in [_live_alert_snapshot(item) for item in list(LIVE_ALERTS)] if alert.get('priority') == 'P1']


@router.get("/p2")
async def p2_alerts():
    return [alert for alert in [_live_alert_snapshot(item) for item in list(LIVE_ALERTS)] if alert.get('priority') == 'P2']


@router.get("/p3")
async def p3_alerts():
    return [alert for alert in [_live_alert_snapshot(item) for item in list(LIVE_ALERTS)] if alert.get('priority') == 'P3']


@router.get("/breached")
async def breached_alerts():
    """Get all SLA breached alerts"""
    breached = sla_breach_monitor.get_breached_alerts()
    return {"status": "SUCCESS", "breached_alerts": breached, "count": len(breached)}


@router.get("/status/{state}")
async def alerts_by_status(state: str):
    """Get alerts by status (OPEN, UNDER_REVIEW, ESCALATED, SLA_BREACHED, CLOSED)"""
    state_upper = state.upper()
    return [alert for alert in [_live_alert_snapshot(item) for item in list(LIVE_ALERTS)] if str(alert.get('status', '')).upper() == state_upper]


@router.get("/officer/{officer_id}")
async def alerts_for_officer(officer_id: str):
    officer_upper = officer_id.upper()
    return [
        alert
        for alert in [_live_alert_snapshot(item) for item in list(LIVE_ALERTS)]
        if str(alert.get('assigned_officer_id', '')).upper() == officer_upper
        or str(alert.get('assigned_officer_name', '')).upper() == officer_upper
        or str(alert.get('assigned_officer', '')).upper() == officer_upper
    ]


@router.get("/queue")
async def queue_snapshot():
    from app.services.alerts.alert_queue_service import get_queue_snapshot

    return get_queue_snapshot()


@router.get("/escalations")
async def escalations():
    # escalate any breached alerts on demand
    results = []
    for a in list(LIVE_ALERTS):
        res = check_and_escalate(a)
        if res.get('escalated'):
            results.append({"alert_id": a.get('alert_id'), "escalated_to": res.get('escalated_to')})
    return results


@router.post("/{alert_id}/acknowledge")
async def acknowledge(alert_id: str, payload: dict | None = None):
    payload = payload or {}
    try:
        return alert_management_service.acknowledge_alert(
            alert_id=alert_id,
            officer_id=payload.get("officer_id", "OFFICER_UNKNOWN"),
            alert_type=payload.get("alert_type", "transaction"),
        )
    except ValueError as exc:
        detail = str(exc)
        status_code = 409 if "Already" in detail or "Cannot acknowledge" in detail else 404
        raise HTTPException(status_code=status_code, detail=detail)


@router.post("/{alert_id}/close")
async def close(alert_id: str, payload: dict | None = None):
    payload = payload or {}
    try:
        return alert_management_service.close_alert(
            alert_id=alert_id,
            closed_by=payload.get("officer_id", "OFFICER_UNKNOWN"),
            resolution=payload.get("resolution", "RESOLVED"),
            remarks=payload.get("remarks", ""),
            alert_type=payload.get("alert_type", "transaction"),
        )
    except ValueError as exc:
        detail = str(exc)
        status_code = 409 if "Already" in detail or "Cannot close" in detail else 404
        raise HTTPException(status_code=status_code, detail=detail)


@router.post("/{alert_id}/escalate")
async def escalate(alert_id: str, payload: dict | None = None):
    payload = payload or {}
    try:
        return alert_management_service.escalate_alert(
            alert_id=alert_id,
            escalated_by=payload.get("officer_id", "OFFICER_UNKNOWN"),
            escalation_reason=payload.get("reason", "Officer escalation"),
            alert_type=payload.get("alert_type", "transaction"),
        )
    except ValueError as exc:
        detail = str(exc)
        status_code = 409 if "Already" in detail else 404
        raise HTTPException(status_code=status_code, detail=detail)
