import os
import csv
from typing import Dict, List

# Compute path to TrustVault/data/processed/alerts from the backend package
BASE_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'data', 'processed', 'alerts')
)

FILES = {
    'onboarding_alerts': 'onboarding_alerts.csv',
    'transaction_alerts': 'transaction_alerts.csv',
    'officer_queue': 'officer_queue.csv',
    'case_registry': 'case_registry.csv',
    'sla_tracking': 'sla_tracking.csv',
    'escalation_log': 'escalation_log.csv',
}

DEFAULT_HEADERS = {
    'onboarding_alerts': ['alert_id', 'alert_type', 'priority', 'severity', 'risk_score', 'decision', 'requires_edd', 'assigned_queue', 'assigned_officer', 'state', 'created_at', 'updated_at', 'metadata'],
    'transaction_alerts': ['alert_id', 'alert_type', 'priority', 'severity', 'risk_score', 'behavior_score', 'sequence_score', 'graph_score', 'decision', 'assigned_queue', 'assigned_officer', 'state', 'created_at', 'updated_at', 'metadata'],
    'officer_queue': ['officer_id', 'assigned_count', 'alerts', 'last_assigned_at'],
    'case_registry': ['case_id', 'source_alert', 'source_alerts', 'priority', 'status', 'assigned_officer', 'evidence', 'created_at', 'closed_at'],
    'sla_tracking': ['alert_id', 'priority', 'sla_minutes', 'created_at', 'due_at', 'breached', 'last_checked'],
    'escalation_log': ['alert_id', 'escalated_to', 'reason', 'escalation_time', 'attempt'],
}


def ensure_storage() -> None:
    os.makedirs(BASE_DIR, exist_ok=True)
    for key, fname in FILES.items():
        path = os.path.join(BASE_DIR, fname)
        if not os.path.exists(path):
            with open(path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(DEFAULT_HEADERS[key])


def _file_path(key: str) -> str:
    return os.path.join(BASE_DIR, FILES[key])


def append_row(key: str, row: Dict) -> None:
    ensure_storage()
    path = _file_path(key)
    headers = DEFAULT_HEADERS[key]
    with open(path, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
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
