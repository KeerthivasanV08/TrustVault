import uuid
from datetime import datetime
from .alert_priority_service import evaluate_priority
from .alert_assignment_service import assign_officer
from .sla_service import create_sla_record
from .alert_queue_service import enqueue_alert
from .alert_storage_service import append_alert_row
from .case_conversion_service import convert_alert_to_case
from app.realtime.transaction_memory_store import append_alert, publish_event


def create_onboarding_alert(onboarding_result: dict) -> dict:
    # build alert
    final_score = onboarding_result.get('final_score') or onboarding_result.get('risk_score') or 0
    pr = evaluate_priority(final_score)
    aid = f"ONB-{uuid.uuid4().hex[:8].upper()}"
    alert = {
        'alert_id': aid,
        'alert_type': onboarding_result.get('alert_type') or 'ONBOARDING_SUSPECT',
        'priority': pr['priority'],
        'severity': pr['severity'],
        'risk_score': float(final_score),
        'decision': onboarding_result.get('decision'),
        'requires_edd': onboarding_result.get('requires_edd', False),
        'created_at': datetime.utcnow().isoformat(),
        'metadata': onboarding_result,
    }

    # assignment
    assignment = assign_officer(alert['priority'], pr['queue'])
    alert['assigned_officer'] = assignment['assigned_officer']
    alert['assigned_queue'] = pr['queue']

    # SLA
    sla = create_sla_record(alert['alert_id'], alert['priority'], pr['sla_minutes'])
    alert['sla'] = sla

    # enqueue
    enqueue_alert(alert['assigned_queue'], alert)

    # persist
    try:
        append_alert_row('onboarding', alert)
    except Exception:
        pass

    # append to live memory and broadcast
    append_alert(alert)
    try:
        import asyncio

        asyncio.create_task(publish_event({'event': 'alert', 'data': alert}))
    except Exception:
        pass

    # case conversion
    _case = convert_alert_to_case(alert)
    if _case:
        alert['converted_case'] = _case

    return alert
