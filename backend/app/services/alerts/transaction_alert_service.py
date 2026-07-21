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


def create_transaction_alert(txn_context: dict) -> dict:
    final_score = txn_context.get('final_score') or txn_context.get('risk_score') or txn_context.get('riskScore') or 0
    pr = evaluate_priority(final_score)
    aid = f"TXN-{uuid.uuid4().hex[:8].upper()}"
    transaction_id = str(txn_context.get('transaction_id') or txn_context.get('trans_id') or txn_context.get('id') or '').strip()
    user_id = str(txn_context.get('user_id') or txn_context.get('sender_id') or '').strip()
    created_at = txn_context.get('created_at') or txn_context.get('timestamp') or txn_context.get('ts') or datetime.utcnow().isoformat()
    alert = {
        'alert_id': aid,
        'alert_type': txn_context.get('alert_type') or txn_context.get('pattern') or 'TRANSACTION_SUSPECT',
        'transaction_id': transaction_id,
        'user_id': user_id,
        'priority': pr['priority'],
        'severity': pr['severity'],
        'risk_score': float(final_score),
        'behavior_score': float(txn_context.get('behavior_score') or txn_context.get('behaviorScore') or 0),
        'sequence_score': float(txn_context.get('sequence_score') or txn_context.get('sequenceScore') or 0),
        'graph_score': float(txn_context.get('graph_score') or txn_context.get('graphScore') or 0),
        'decision': txn_context.get('decision'),
        'assigned_queue': pr['queue'],
        'status': 'OPEN',
        'state': 'OPEN',
        'created_at': created_at,
        'metadata': txn_context,
    }

    # assignment
    assignment = assign_officer(alert['priority'], pr['queue'], alert_id=aid)
    alert['assigned_officer_id'] = assignment['assigned_officer_id']
    alert['assigned_officer_name'] = assignment['assigned_officer_name']
    alert['assigned_officer'] = assignment['assigned_officer_name']
    alert['assigned_at'] = assignment['assigned_at']
    alert['assigned_queue'] = assignment['assigned_queue']

    # SLA
    sla = create_sla_record(alert['alert_id'], alert['priority'], pr['sla_minutes'], created_at=created_at)
    alert['sla'] = sla
    alert['sla_minutes'] = sla['sla_minutes']
    alert['sla_due_at'] = sla['due_at']
    alert['remaining_seconds'] = sla.get('remaining_seconds', 0)
    alert['sla_breached'] = bool(sla.get('breached', False))

    # convert to case if rules match
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
        append_alert_row('transaction', alert)
    except Exception:
        pass

    # append to live memory and broadcast
    append_alert(alert)
    _publish_alert_event({'event': 'alert', 'data': alert})

    return alert
