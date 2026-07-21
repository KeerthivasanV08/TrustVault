from fastapi import APIRouter, HTTPException
from app.services.cases.case_repository import case_repository

router = APIRouter()


@router.get("")
async def list_cases():
    return case_repository.list_cases()


@router.get("/{case_id}")
async def get_case(case_id: str):
    case = case_repository.get_case(case_id)
    if case:
        return case
    raise HTTPException(status_code=404, detail='Case not found')


@router.post("/create")
async def create_case(payload: dict):
    rec = {
        'case_id': payload.get('case_id'),
        'source_alert_id': payload.get('source_alert_id') or payload.get('source_alert'),
        'source_type': payload.get('source_type', 'MANUAL'),
        'priority': payload.get('priority', 'P3'),
        'status': payload.get('status', 'OPEN'),
        'assigned_officer': payload.get('assigned_officer', ''),
        'assigned_team': payload.get('assigned_team', ''),
        'creation_source': payload.get('creation_source', 'MANUAL_OFFICER'),
        'reason': str(payload.get('reason', payload.get('evidence', ''))),
        'evidence': str(payload.get('evidence', '')),
        'created_at': payload.get('created_at', ''),
        'updated_at': payload.get('updated_at', ''),
        'runtime_session_id': payload.get('runtime_session_id', ''),
    }
    return case_repository.upsert_case(rec)


@router.post("/{case_id}/assign")
async def assign_case(case_id: str, payload: dict):
    case = case_repository.get_case(case_id) or {'case_id': case_id}
    case.update({'assigned_officer': payload.get('assigned_officer', ''), 'assigned_team': payload.get('assigned_team', ''), 'status': payload.get('status', case.get('status', 'OPEN'))})
    return case_repository.upsert_case(case)


@router.post("/{case_id}/freeze")
async def freeze_case(case_id: str):
    case = case_repository.get_case(case_id) or {'case_id': case_id}
    case.update({'freeze_status': 'FROZEN', 'status': 'FROZEN'})
    return case_repository.upsert_case(case)


@router.post("/{case_id}/sar")
async def create_sar(case_id: str, payload: dict):
    case = case_repository.get_case(case_id) or {'case_id': case_id}
    case.update({'sar_status': 'FILED', 'reason': payload.get('reason', case.get('reason', ''))})
    return case_repository.upsert_case(case)
