import os
import csv
from typing import Dict, List

from app.core.runtime_context import get_runtime_session_id

# Compute path to TrustVault/data/processed/alerts from the backend package
BASE_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'data', 'processed', 'alerts')
)

FILES = {
    'onboarding_alerts': 'onboarding_alerts.csv',
    'transaction_alerts': 'transaction_alerts.csv',
    'officer_queue': 'officer_queue.csv',
    'investigator_registry': 'investigator_registry.csv',
    'case_registry': 'case_registry.csv',
    'sla_tracking': 'sla_tracking.csv',
    'escalation_log': 'escalation_log.csv',
}

DEFAULT_HEADERS = {
    'onboarding_alerts': ['alert_id', 'alert_type', 'transaction_id', 'user_id', 'priority', 'severity', 'risk_score', 'decision', 'requires_edd', 'assigned_queue', 'assigned_officer', 'assigned_officer_id', 'assigned_officer_name', 'assigned_at', 'case_id', 'status', 'state', 'sla_minutes', 'sla_due_at', 'remaining_seconds', 'sla_breached', 'acknowledged_by', 'acknowledged_at', 'escalated_by', 'escalated_at', 'previous_priority', 'new_priority', 'reason', 'closed_by', 'closed_at', 'resolution', 'remarks', 'created_at', 'updated_at', 'metadata'],
    'transaction_alerts': ['alert_id', 'alert_type', 'transaction_id', 'user_id', 'priority', 'severity', 'risk_score', 'behavior_score', 'sequence_score', 'graph_score', 'decision', 'assigned_queue', 'assigned_officer', 'assigned_officer_id', 'assigned_officer_name', 'assigned_at', 'case_id', 'status', 'state', 'sla_minutes', 'sla_due_at', 'remaining_seconds', 'sla_breached', 'acknowledged_by', 'acknowledged_at', 'escalated_by', 'escalated_at', 'previous_priority', 'new_priority', 'reason', 'closed_by', 'closed_at', 'resolution', 'remarks', 'created_at', 'updated_at', 'metadata'],
    'officer_queue': ['officer_id', 'assigned_count', 'alerts', 'last_assigned_at'],
    'investigator_registry': ['assigned_officer_id', 'assigned_officer_name', 'assigned_count', 'last_assigned_at', 'active', 'runtime_session_id'],
    'case_registry': ['case_id', 'source_alert_id', 'source_type', 'user_id', 'transaction_id', 'priority', 'status', 'assigned_officer', 'assigned_team', 'creation_source', 'reason', 'evidence', 'created_at', 'updated_at', 'sla_deadline', 'escalation_level', 'freeze_status', 'sar_status', 'resolution', 'runtime_session_id'],
    'sla_tracking': ['alert_id', 'priority', 'sla_minutes', 'created_at', 'due_at', 'breached', 'last_checked'],
    'escalation_log': ['alert_id', 'escalated_to', 'escalated_by', 'reason', 'escalation_time', 'attempt', 'runtime_session_id'],
}


def _migrate_storage_file(key: str) -> None:
    path = _file_path(key)
    headers = DEFAULT_HEADERS[key]
    if not os.path.exists(path):
        return

    try:
        frame = pd.read_csv(path)
    except Exception:
        return

    changed = False
    for column in headers:
        if column not in frame.columns:
            frame[column] = ""
            changed = True

    if changed or list(frame.columns) != headers:
        frame = frame.reindex(columns=headers, fill_value="")
        frame.to_csv(path, index=False)


def ensure_storage() -> None:
    os.makedirs(BASE_DIR, exist_ok=True)
    for key, fname in FILES.items():
        path = os.path.join(BASE_DIR, fname)
        if not os.path.exists(path):
            with open(path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(DEFAULT_HEADERS[key])
        else:
            _migrate_storage_file(key)


def _file_path(key: str) -> str:
    return os.path.join(BASE_DIR, FILES[key])


def append_row(key: str, row: Dict) -> None:
    ensure_storage()
    path = _file_path(key)
    headers = DEFAULT_HEADERS[key]
    with open(path, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        row = dict(row)
        row.setdefault('runtime_session_id', get_runtime_session_id())
        writer.writerow([row.get(h, '') for h in headers])


def read_csv(key: str) -> List[Dict]:
    ensure_storage()
    path = _file_path(key)
    items: List[Dict] = []
    with open(path, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            items.append(dict(r))
    return items


def append_alert_row(alert_type: str, row: Dict) -> None:
    if alert_type == 'onboarding':
        append_row('onboarding_alerts', row)
    else:
        append_row('transaction_alerts', row)


def read_alerts_csv(which: str = 'transaction') -> List[Dict]:
    if which == 'onboarding':
        return read_csv('onboarding_alerts')
    return read_csv('transaction_alerts')
