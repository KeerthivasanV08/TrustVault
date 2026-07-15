import uuid
from datetime import datetime
import asyncio
from .alert_priority_service import evaluate_priority
from .alert_assignment_service import assign_officer
from .sla_service import create_sla_record
from .alert_queue_service import enqueue_alert
from .alert_storage_service import append_alert_row
from .case_conversion_service import convert_alert_to_case
from app.realtime.transaction_memory_store import append_alert, publish_event


def _publish_alert_event(payload: dict) -> None:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return

    try:
        loop.create_task(publish_event(payload))
    except Exception:
        pass


def create_onboarding_alert(onboarding_result: dict) -> dict:
    # build alert
    final_score = onboarding_result.get('final_score') or onboarding_result.get('risk_score') or 0
    pr = evaluate_priority(final_score)
    aid = f"ONB-{uuid.uuid4().hex[:8].upper()}"
    user_id = str(onboarding_result.get('user_id') or onboarding_result.get('sender_id') or '').strip()
    alert = {
        'alert_id': aid,
        'alert_type': onboarding_result.get('alert_type') or 'ONBOARDING_SUSPECT',
        'transaction_id': str(onboarding_result.get('transaction_id') or onboarding_result.get('trans_id') or '').strip(),
        'user_id': user_id,
        'priority': pr['priority'],
        'severity': pr['severity'],
        'risk_score': float(final_score),
        'decision': onboarding_result.get('decision'),
        'requires_edd': onboarding_result.get('requires_edd', False),
        'assigned_queue': pr['queue'],
        'status': 'OPEN',
        'state': 'OPEN',
        'created_at': onboarding_result.get('created_at') or onboarding_result.get('timestamp') or datetime.utcnow().isoformat(),
        'metadata': onboarding_result,
    }

    # assignment
    assignment = assign_officer(alert['priority'], pr['queue'], alert_id=aid)
    alert['assigned_officer_id'] = assignment['assigned_officer_id']
    alert['assigned_officer_name'] = assignment['assigned_officer_name']
    alert['assigned_officer'] = assignment['assigned_officer_name']
    alert['assigned_at'] = assignment['assigned_at']
    alert['assigned_queue'] = assignment['assigned_queue']

    # SLA
    sla = create_sla_record(alert['alert_id'], alert['priority'], pr['sla_minutes'], created_at=alert['created_at'])
    alert['sla'] = sla
    alert['sla_minutes'] = sla['sla_minutes']
    alert['sla_due_at'] = sla['due_at']
    alert['remaining_seconds'] = sla.get('remaining_seconds', 0)
    alert['sla_breached'] = bool(sla.get('breached', False))

    # case conversion
    _case = convert_alert_to_case(alert)
    if _case:
        alert['converted_case'] = _case
        alert['case_id'] = _case.get('case_id', '')
        alert['status'] = _case.get('status', alert.get('status', 'OPEN'))
        alert['state'] = alert['status']

    # enqueue
    enqueue_alert(alert['assigned_queue'], alert)

    # persist
    try:
        append_alert_row('onboarding', alert)
    except Exception:
        pass

    # append to live memory and broadcast
    append_alert(alert)
    _publish_alert_event({'event': 'alert', 'data': alert})

    return alert
