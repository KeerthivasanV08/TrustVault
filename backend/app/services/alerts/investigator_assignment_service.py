from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from app.core.runtime_context import get_runtime_session_id
from .alert_storage_service import read_csv, _file_path, DEFAULT_HEADERS

INVESTIGATOR_REGISTRY = [
    {"assigned_officer_id": "101", "assigned_officer_name": "Officer 101", "active": True},
    {"assigned_officer_id": "102", "assigned_officer_name": "Officer 102", "active": True},
    {"assigned_officer_id": "103", "assigned_officer_name": "Officer 103", "active": True},
    {"assigned_officer_id": "104", "assigned_officer_name": "Officer 104", "active": True},
    {"assigned_officer_id": "105", "assigned_officer_name": "Officer 105", "active": True},
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _coerce_int(value: object, default: int = 0) -> int:
    try:
        if value in (None, ""):
            return default
        return int(str(value).strip())
    except Exception:
        return default


def _load_registry_state() -> List[Dict[str, Any]]:
    state = read_csv('investigator_registry')
    if state:
        return state

    seed = []
    for investigator in INVESTIGATOR_REGISTRY:
        seed.append({
            **investigator,
            "assigned_count": 0,
            "last_assigned_at": "",
            "runtime_session_id": get_runtime_session_id(),
        })
    return seed


def _persist_registry_state(rows: List[Dict[str, Any]]) -> None:
    path = _file_path('investigator_registry')
    headers = DEFAULT_HEADERS['investigator_registry']
    import pandas as pd

    frame = pd.DataFrame(rows)
    for column in headers:
        if column not in frame.columns:
            frame[column] = ""
    frame = frame[headers]
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = target.with_suffix('.tmp')
    frame.to_csv(tmp_path, index=False)
    tmp_path.replace(target)


def get_investigator_profile(officer_id: str | None) -> Dict[str, Any]:
    if officer_id is None:
        return {}

    officer_key = str(officer_id).strip()
    for investigator in _load_registry_state():
        if str(investigator.get('assigned_officer_id', '')).strip() == officer_key:
            return investigator
        if str(investigator.get('assigned_officer_name', '')).strip().lower() == officer_key.lower():
            return investigator
    return {}


def assign_investigator(queue: str, alert_id: str | None = None) -> Dict[str, Any]:
    rows = _load_registry_state()
    active_rows = [row for row in rows if str(row.get('active', True)).lower() not in {'false', '0', 'no'}]
    if not active_rows:
        active_rows = rows

    def _sort_key(row: Dict[str, Any]) -> tuple[int, str]:
        return (
            _coerce_int(row.get('assigned_count'), 0),
            str(row.get('last_assigned_at') or ''),
        )

    selected = sorted(active_rows, key=_sort_key)[0]
    now = _now()
    selected['assigned_count'] = _coerce_int(selected.get('assigned_count'), 0) + 1
    selected['last_assigned_at'] = now
    selected['runtime_session_id'] = get_runtime_session_id()

    for idx, row in enumerate(rows):
        if str(row.get('assigned_officer_id', '')).strip() == str(selected.get('assigned_officer_id', '')).strip():
            rows[idx] = selected
            break

    _persist_registry_state(rows)

    assignment = {
        'assigned_officer_id': str(selected.get('assigned_officer_id', '')).strip(),
        'assigned_officer_name': str(selected.get('assigned_officer_name', '')).strip(),
        'assigned_officer': str(selected.get('assigned_officer_name', '')).strip(),
        'assigned_at': now,
        'assigned_count': _coerce_int(selected.get('assigned_count'), 0),
        'assigned_queue': queue,
        'queue': queue,
        'alert_id': alert_id or '',
    }

    return assignment


def get_assignment_registry() -> List[Dict[str, Any]]:
    return _load_registry_state()


def record_manual_assignment(officer_id: str, officer_name: str, queue: str = '', alert_id: str | None = None) -> Dict[str, Any]:
    profile = get_investigator_profile(officer_id) or {
        'assigned_officer_id': str(officer_id),
        'assigned_officer_name': officer_name or str(officer_id),
        'assigned_count': 0,
        'last_assigned_at': '',
        'active': True,
    }
    profile['assigned_count'] = _coerce_int(profile.get('assigned_count'), 0) + 1
    profile['last_assigned_at'] = _now()
    profile['runtime_session_id'] = get_runtime_session_id()

    rows = _load_registry_state()
    replaced = False
    for idx, row in enumerate(rows):
        if str(row.get('assigned_officer_id', '')).strip() == str(profile.get('assigned_officer_id', '')).strip():
            rows[idx] = profile
            replaced = True
            break
    if not replaced:
        rows.append(profile)
    _persist_registry_state(rows)

    return {
        'assigned_officer_id': str(profile.get('assigned_officer_id', '')).strip(),
        'assigned_officer_name': str(profile.get('assigned_officer_name', '')).strip(),
        'assigned_officer': str(profile.get('assigned_officer_name', '')).strip(),
        'assigned_at': profile.get('last_assigned_at', _now()),
        'assigned_count': _coerce_int(profile.get('assigned_count'), 0),
        'assigned_queue': queue,
        'queue': queue,
        'alert_id': alert_id or '',
    }
