from datetime import datetime, timedelta
from typing import Dict, Optional
from .alert_storage_service import append_row
from app.core.runtime_context import get_runtime_session_id

# in-memory SLA registry for quick checks
_SLA_REGISTRY: Dict[str, Dict] = {}


def _now() -> datetime:
    return datetime.utcnow()


def _parse_datetime(value: object) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        return datetime.utcfromtimestamp(float(value) / 1000.0 if float(value) > 10_000_000_000 else float(value))
    if value in (None, ""):
        return _now()
    text = str(value).strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
        return parsed.replace(tzinfo=None) if parsed.tzinfo else parsed
    except Exception:
        return _now()


def create_sla_record(alert_id: str, priority: str, sla_minutes: int, created_at: object | None = None) -> Dict:
    created = _parse_datetime(created_at) if created_at is not None else _now()
    due = created + timedelta(minutes=int(sla_minutes))
    now = _now()
    remaining_seconds = int((due - now).total_seconds())
    rec = {
        "alert_id": alert_id,
        "priority": priority,
        "sla_minutes": sla_minutes,
        "created_at": created.isoformat(),
        "due_at": due.isoformat(),
        "remaining_seconds": remaining_seconds,
        "breached": remaining_seconds < 0,
        "last_checked": now.isoformat(),
        "runtime_session_id": get_runtime_session_id(),
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
    return int(delta.total_seconds())


def check_sla_breach(alert_id: str) -> Dict:
    rec = _SLA_REGISTRY.get(alert_id)
    if not rec:
        return {"sla_status": "UNKNOWN", "remaining_seconds": None, "breached": False}
    remaining = calculate_remaining_time(alert_id)
    breached = remaining is not None and remaining < 0
    rec['breached'] = breached
    rec['last_checked'] = _now().isoformat()
    rec['remaining_seconds'] = remaining
    return {"sla_status": "ACTIVE" if not breached else "BREACHED", "remaining_seconds": remaining, "breached": breached}
