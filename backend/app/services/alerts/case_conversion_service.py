import uuid
from datetime import datetime
from typing import List
from .alert_storage_service import append_row


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
        'source_alert': alert.get('alert_id'),
        'source_alerts': ','.join(related_alerts) if related_alerts else alert.get('alert_id'),
        'priority': priority,
        'status': 'OPEN',
        'assigned_officer': alert.get('assigned_officer'),
        'evidence': str(alert.get('metadata') or {}),
        'created_at': datetime.utcnow().isoformat(),
        'closed_at': '',
    }
    try:
        append_row('case_registry', rec)
    except Exception:
        pass
    return rec
