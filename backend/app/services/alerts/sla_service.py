from datetime import datetime, timedelta
from typing import Dict, Optional
from .alert_storage_service import append_row

# in-memory SLA registry for quick checks
_SLA_REGISTRY: Dict[str, Dict] = {}


def _now() -> datetime:
    return datetime.utcnow()


def create_sla_record(alert_id: str, priority: str, sla_minutes: int) -> Dict:
    created = _now()
    due = created + timedelta(minutes=int(sla_minutes))
    rec = {
        "alert_id": alert_id,
        "priority": priority,
        "sla_minutes": sla_minutes,
        "created_at": created.isoformat(),
        "due_at": due.isoformat(),
        "breached": False,
        "last_checked": created.isoformat(),
    }
    _SLA_REGISTRY[alert_id] = rec
    try:
        append_row('sla_tracking', rec)
    except Exception:
        pass
    return rec


def calculate_remaining_time(alert_id: str) -> Optional[int]:
    rec = _SLA_REGISTRY.get(alert_id)
    if not rec:
        return None
    due = datetime.fromisoformat(rec['due_at'])
    delta = due - _now()
    return max(int(delta.total_seconds() / 60), -1)


def check_sla_breach(alert_id: str) -> Dict:
    rec = _SLA_REGISTRY.get(alert_id)
    if not rec:
        return {"sla_status": "UNKNOWN", "remaining_minutes": None, "breached": False}
    remaining = calculate_remaining_time(alert_id)
    breached = remaining is not None and remaining < 0
    rec['breached'] = breached
    rec['last_checked'] = _now().isoformat()
    return {"sla_status": "ACTIVE" if not breached else "BREACHED", "remaining_minutes": remaining, "breached": breached}
