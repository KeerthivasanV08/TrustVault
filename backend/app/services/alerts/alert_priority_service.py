from typing import Dict


def evaluate_priority(final_score: float) -> Dict:
    """Map a numeric score in [0,1] or [0,100] to priority, severity, SLA and escalation."""
    try:
        score = float(final_score)
    except Exception:
        score = 0.0

    # normalize 0..100 -> 0..1
    if score > 1:
        norm = score / 100.0
    else:
        norm = score

    if norm >= 0.92:
        priority = "P1"
        severity = "CRITICAL"
        sla_minutes = 15
        escalation_minutes = 20
        queue = "AML_CRITICAL_QUEUE"
    elif norm >= 0.75:
        priority = "P2"
        severity = "HIGH"
        sla_minutes = 120
        escalation_minutes = 180
        queue = "AML_REVIEW_QUEUE"
    elif norm >= 0.5:
        priority = "P3"
        severity = "MEDIUM"
        sla_minutes = 1440
        escalation_minutes = 2880
        queue = "AML_MONITORING_QUEUE"
    else:
        priority = "INFO"
        severity = "LOW"
        sla_minutes = 10080
        escalation_minutes = 20160
        queue = "AML_INFO_QUEUE"

    return {
        "priority": priority,
        "severity": severity,
        "sla_minutes": sla_minutes,
        "escalation_minutes": escalation_minutes,
        "queue": queue,
    }
