import uuid
from datetime import datetime
from .alert_priority_service import evaluate_priority
from .alert_assignment_service import assign_officer
from .sla_service import create_sla_record
from .alert_queue_service import enqueue_alert
from .alert_storage_service import append_alert_row
from .case_conversion_service import convert_alert_to_case
from app.realtime.transaction_memory_store import append_alert, publish_event


def create_transaction_alert(txn_context: dict) -> dict:
    final_score = txn_context.get('final_score') or txn_context.get('risk_score') or txn_context.get('riskScore') or 0
    pr = evaluate_priority(final_score)
    aid = f"TXN-{uuid.uuid4().hex[:8].upper()}"
    alert = {
        'alert_id': aid,
        'alert_type': txn_context.get('alert_type') or txn_context.get('pattern') or 'TRANSACTION_SUSPECT',
        'priority': pr['priority'],
        'severity': pr['severity'],
        'risk_score': float(final_score),
        'behavior_score': float(txn_context.get('behavior_score') or txn_context.get('behaviorScore') or 0),
        'sequence_score': float(txn_context.get('sequence_score') or txn_context.get('sequenceScore') or 0),
        'graph_score': float(txn_context.get('graph_score') or txn_context.get('graphScore') or 0),
        'decision': txn_context.get('decision'),
        'created_at': datetime.utcnow().isoformat(),
        'metadata': txn_context,
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
        append_alert_row('transaction', alert)
    except Exception:
        pass

    # append to live memory and broadcast
    append_alert(alert)
    try:
        import asyncio

        asyncio.create_task(publish_event({'event': 'alert', 'data': alert}))
    except Exception:
        pass

    # convert to case if rules match
    _case = convert_alert_to_case(alert)
    if _case:
        alert['converted_case'] = _case

    return alert
