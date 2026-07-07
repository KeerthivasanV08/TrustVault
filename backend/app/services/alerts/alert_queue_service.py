from collections import deque
from typing import Dict, Any, List
from .alert_storage_service import append_row

QUEUES: Dict[str, deque] = {
    'P1_QUEUE': deque(),
    'P2_QUEUE': deque(),
    'P3_QUEUE': deque(),
    'EDD_QUEUE': deque(),
    'MANUAL_REVIEW_QUEUE': deque(),
}


def enqueue_alert(queue_name: str, alert: Dict[str, Any]) -> None:
    q = QUEUES.setdefault(queue_name, deque())
    q.append(alert)
    # persist a snapshot row for officer_queue for traceability
    try:
        append_row('officer_queue', {'officer_id': alert.get('assigned_officer', ''), 'assigned_count': 1, 'alerts': alert.get('alert_id', ''), 'last_assigned_at': alert.get('created_at', '')})
    except Exception:
        pass


def dequeue_alert(queue_name: str) -> Dict[str, Any]:
    q = QUEUES.get(queue_name) or deque()
    if not q:
        return {}
    return q.popleft()


def get_queue_snapshot() -> Dict[str, Dict[str, Any]]:
    snap: Dict[str, Dict[str, Any]] = {}
    for k, q in QUEUES.items():
        snap[k] = {
            'size': len(q),
            'oldest': q[0] if len(q) > 0 else None,
        }
    return snap


def get_officer_queue(officer_id: str) -> List[Dict[str, Any]]:
    # naive: read queue persistence is stored in officer_queue CSV rows; but in-memory we don't map by officer
    return []
