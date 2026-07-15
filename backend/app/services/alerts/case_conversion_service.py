import uuid
from datetime import datetime
from typing import List
from app.core.runtime_context import get_runtime_session_id
from app.services.cases.case_repository import case_repository


def convert_alert_to_case(alert: dict, related_alerts: List[str] = None) -> dict:
    """Auto-convert alerts into investigation cases based on rules."""
    related_alerts = related_alerts or []
    # auto-convert rules: all P1, repeated P2, mule/sanctions
    priority = alert.get('priority')
    alert_type = (alert.get('alert_type') or '').upper()
    should_convert = False
    if priority == 'P1':
        should_convert = True
    if priority == 'P2' and alert.get('repeat_count', 0) >= 2:
        should_convert = True
    if 'MULE' in alert_type or 'SANCTION' in alert_type or 'MULE_CLUSTER' in alert_type:
        should_convert = True

    if not should_convert:
        return {}

    case_id = f"CASE-{uuid.uuid4().hex[:8].upper()}"
    rec = {
        'case_id': case_id,
        'source_alert_id': alert.get('alert_id'),
        'source_type': alert.get('alert_type') or 'ALERT',
        'user_id': alert.get('user_id', ''),
        'transaction_id': alert.get('transaction_id', ''),
        'priority': priority,
        'status': 'OPEN',
        'assigned_officer': alert.get('assigned_officer_id') or alert.get('assigned_officer'),
        'assigned_team': alert.get('assigned_queue', ''),
        'creation_source': 'AUTO_ALERT',
        'reason': str(alert.get('alert_type') or alert.get('metadata') or {}),
        'evidence': str(alert.get('metadata') or {}),
        'created_at': datetime.utcnow().isoformat(),
        'updated_at': datetime.utcnow().isoformat(),
        'runtime_session_id': get_runtime_session_id(),
    }
    try:
        case_repository.upsert_case(rec)
    except Exception:
        pass
    return rec
