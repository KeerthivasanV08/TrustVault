from typing import Dict

from .investigator_assignment_service import assign_investigator


TEAM_MAP = {
    "P1": "AML_CRITICAL_QUEUE",
    "P2": "AML_REVIEW_QUEUE",
    "P3": "AML_MONITORING_QUEUE",
    "INFO": "AML_INFO_QUEUE",
}


def assign_officer(priority: str, queue: str, alert_id: str | None = None) -> Dict:
    assigned_queue = queue or TEAM_MAP.get(priority, 'AML_MONITORING_QUEUE')
    assignment = assign_investigator(assigned_queue, alert_id=alert_id)
    assignment['assigned_team'] = assigned_queue
    assignment['assigned_queue'] = assigned_queue
    return assignment
