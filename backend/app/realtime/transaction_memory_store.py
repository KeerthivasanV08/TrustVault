import asyncio
from collections import deque
from typing import Any, Dict, List

# In-memory deques for quick realtime access
LIVE_TRANSACTIONS: deque = deque(maxlen=500)
LIVE_ALERTS: deque = deque(maxlen=200)
LIVE_GRAPH_EVENTS: deque = deque(maxlen=500)

DASHBOARD_METRICS: Dict[str, Any] = {
    "total_transactions": 0,
    "blocked_transactions": 0,
    "review_queue": 0,
    "high_risk_count": 0,
}

# Simple pub/sub for SSE subscribers
_SUBSCRIBERS: List[asyncio.Queue] = []


def append_transaction(txn: Dict) -> None:
    LIVE_TRANSACTIONS.appendleft(txn)
    DASHBOARD_METRICS["total_transactions"] = DASHBOARD_METRICS.get("total_transactions", 0) + 1


def append_alert(alert: Dict) -> None:
    LIVE_ALERTS.appendleft(alert)
    DASHBOARD_METRICS["review_queue"] = max(0, DASHBOARD_METRICS.get("review_queue", 0) + 1)


def append_graph_event(event: Dict) -> None:
    LIVE_GRAPH_EVENTS.appendleft(event)


def update_metrics(updates: Dict[str, int]) -> None:
    for k, v in updates.items():
        DASHBOARD_METRICS[k] = v


def subscribe() -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue()
    _SUBSCRIBERS.append(q)
    return q


def unsubscribe(q: asyncio.Queue) -> None:
    try:
        _SUBSCRIBERS.remove(q)
    except ValueError:
        pass


async def publish_event(event: Dict) -> None:
    # push to all subscriber queues (non-blocking best-effort)
    for q in list(_SUBSCRIBERS):
        try:
            q.put_nowait(event)
        except Exception:
            # if queue is full or closed, remove it
            try:
                _SUBSCRIBERS.remove(q)
            except Exception:
                pass
