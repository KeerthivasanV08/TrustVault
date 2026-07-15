from datetime import datetime
from .sla_service import check_sla_breach
from .alert_storage_service import append_row
from app.core.runtime_context import get_runtime_session_id


def check_and_escalate(alert: dict) -> dict:
    """Check SLA and escalate to supervisor if breached."""
    aid = alert.get('alert_id')
    sla = check_sla_breach(aid)
    if sla.get('breached'):
        # log escalation
        rec = {
            'alert_id': aid,
            'escalated_to': 'SUPERVISOR-01',
            'reason': 'SLA_BREACH',
            'escalation_time': datetime.utcnow().isoformat(),
            'attempt': 1,
            'runtime_session_id': get_runtime_session_id(),
        }
        try:
            append_row('escalation_log', rec)
        except Exception:
            pass
        return {'escalated': True, 'escalated_to': 'SUPERVISOR-01'}
    return {'escalated': False}
