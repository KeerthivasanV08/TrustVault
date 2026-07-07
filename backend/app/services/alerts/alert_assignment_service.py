from typing import Dict, Tuple, List
from datetime import datetime
from .alert_storage_service import read_csv, append_row

# simulated officers
OFFICERS = ["OFFICER-01", "OFFICER-02", "OFFICER-03"]
SUPERVISOR = "SUPERVISOR-01"

TEAM_MAP = {
    "P1": "AML_HIGH_RISK",
    "P2": "AML_REVIEW",
    "P3": "AML_MONITORING",
    "INFO": "AML_INFO",
}


def _coerce_int(value: object, default: int = 0) -> int:
    try:
        if value in (None, ""):
            return default
        return int(str(value).strip())
    except Exception:
        return default


def _normalize_alerts(value: object) -> str:
    if value in (None, ""):
        return ""
    return str(value)


def _read_officer_state() -> Dict[str, Dict]:
    rows = read_csv('officer_queue')
    state = {}
    for r in rows:
        officer_id = (r.get('officer_id') or '').strip()
        if not officer_id:
            continue
        state[officer_id] = {
            'officer_id': officer_id,
            'assigned_count': _coerce_int(r.get('assigned_count'), 0),
            'alerts': _normalize_alerts(r.get('alerts')),
            'last_assigned_at': _normalize_alerts(r.get('last_assigned_at')),
        }
    return state


def _persist_officer_state(state: Dict[str, Dict]) -> None:
    # naive persistence: append a snapshot row per officer
    for oid, rec in state.items():
        try:
            append_row(
                'officer_queue',
                {
                    'officer_id': oid,
                    'assigned_count': _coerce_int(rec.get('assigned_count'), 0),
                    'alerts': _normalize_alerts(rec.get('alerts')),
                    'last_assigned_at': _normalize_alerts(rec.get('last_assigned_at')),
                },
            )
        except Exception:
            pass


def assign_officer(priority: str, queue: str) -> Dict:
    # choose team
    team = TEAM_MAP.get(priority, 'AML_MONITORING')
    state = _read_officer_state()

    # build workload map for simulated officers
    workload: Dict[str, int] = {o: 0 for o in OFFICERS}
    for oid, rec in state.items():
        workload[oid] = _coerce_int(rec.get('assigned_count'), 0)

    # pick lowest workload officer
    selected = min(workload.items(), key=lambda kv: kv[1])[0]
    # update state
    rec = state.get(selected, {})
    existing_alerts = _normalize_alerts(rec.get('alerts'))
    alerts = f"{existing_alerts}|{queue}" if existing_alerts else queue
    rec['assigned_count'] = _coerce_int(rec.get('assigned_count'), 0) + 1
    rec['alerts'] = alerts
    rec['last_assigned_at'] = datetime.utcnow().isoformat()
    state[selected] = rec
    try:
        _persist_officer_state(state)
    except Exception:
        pass

    return {"assigned_officer": selected, "assigned_team": team}
