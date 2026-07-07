from fastapi import APIRouter, HTTPException
from typing import List
from app.services.alerts.alert_storage_service import read_csv, append_row
from app.realtime.transaction_memory_store import LIVE_ALERTS

router = APIRouter()


@router.get("")
async def list_cases():
    return read_csv('case_registry')


@router.get("/{case_id}")
async def get_case(case_id: str):
    cases = read_csv('case_registry')
    for c in cases:
        if c.get('case_id') == case_id:
            return c
    raise HTTPException(status_code=404, detail='Case not found')


@router.post("/create")
async def create_case(payload: dict):
    # minimal creation path
    rec = {
        'case_id': payload.get('case_id'),
        'source_alert': payload.get('source_alert'),
        'source_alerts': payload.get('source_alerts', ''),
        'priority': payload.get('priority', 'P3'),
        'status': payload.get('status', 'OPEN'),
        'assigned_officer': payload.get('assigned_officer', ''),
        'evidence': str(payload.get('evidence', '')),
        'created_at': payload.get('created_at', ''),
        'closed_at': payload.get('closed_at', ''),
    }
    append_row = globals().get('append_row')
    try:
        from app.services.alerts.alert_storage_service import append_row as _append

        _append('case_registry', rec)
    except Exception:
        pass
    return rec


@router.post("/{case_id}/assign")
async def assign_case(case_id: str, payload: dict):
    # naive assign: update CSV by appending a new snapshot
    try:
        from app.services.alerts.alert_storage_service import append_row as _append

        _append('case_registry', {'case_id': case_id, 'assigned_officer': payload.get('assigned_officer', '')})
    except Exception:
        pass
    return {"status": "ok"}


@router.post("/{case_id}/freeze")
async def freeze_case(case_id: str):
    try:
        from app.services.alerts.alert_storage_service import append_row as _append

        _append('case_registry', {'case_id': case_id, 'status': 'FROZEN'})
    except Exception:
        pass
    return {"status": "ok"}


@router.post("/{case_id}/sar")
async def create_sar(case_id: str, payload: dict):
    # SAR generation placeholder: mark case SAR flag
    try:
        from app.services.alerts.alert_storage_service import append_row as _append

        _append('case_registry', {'case_id': case_id, 'evidence': str(payload.get('evidence', 'SAR_CREATED'))})
    except Exception:
        pass
    return {"status": "ok"}
