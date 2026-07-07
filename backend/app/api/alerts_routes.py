from fastapi import APIRouter, HTTPException
from typing import List
from app.services.alerts.alert_storage_service import read_alerts_csv
from app.realtime.transaction_memory_store import LIVE_ALERTS
from app.services.alerts.escalation_service import check_and_escalate

router = APIRouter()


@router.get("")
async def all_alerts():
    # return live alerts snapshot
    return list(LIVE_ALERTS)


@router.get("/p1")
async def p1_alerts():
    return [a for a in list(LIVE_ALERTS) if a.get('priority') == 'P1']


@router.get("/p2")
async def p2_alerts():
    return [a for a in list(LIVE_ALERTS) if a.get('priority') == 'P2']


@router.get("/officer/{officer_id}")
async def alerts_for_officer(officer_id: str):
    return [a for a in list(LIVE_ALERTS) if a.get('assigned_officer') == officer_id]


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
async def acknowledge(alert_id: str):
    for a in LIVE_ALERTS:
        if a.get('alert_id') == alert_id:
            a['state'] = 'ACKNOWLEDGED'
            return {"status": "ok"}
    raise HTTPException(status_code=404, detail="Alert not found")


@router.post("/{alert_id}/close")
async def close(alert_id: str):
    for a in LIVE_ALERTS:
        if a.get('alert_id') == alert_id:
            a['state'] = 'CLOSED'
            return {"status": "ok"}
    raise HTTPException(status_code=404, detail="Alert not found")


@router.post("/{alert_id}/escalate")
async def escalate(alert_id: str):
    for a in LIVE_ALERTS:
        if a.get('alert_id') == alert_id:
            res = check_and_escalate(a)
            return res
    raise HTTPException(status_code=404, detail="Alert not found")
