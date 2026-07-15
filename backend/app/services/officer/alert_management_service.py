"""
Alert Management Service

Handles officer interactions with alerts:
- Acknowledge alerts
- Escalate alerts
- Close alerts
- Request EDD
- Track alert status transitions
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional
import pandas as pd

from app.core.runtime_context import get_runtime_session_id
from app.services.alerts.alert_storage_service import read_csv, append_row
from app.services.alerts.investigator_assignment_service import get_investigator_profile
from app.services.cases.case_repository import case_repository
from app.db.file_storage import log_control_decision
from app.services.transaction.audit_service import log_officer_action
from app.realtime.transaction_memory_store import publish_event, LIVE_ALERTS


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_write_csv(frame: pd.DataFrame, path: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = target.with_suffix(".tmp")
    frame.to_csv(tmp_path, index=False)
    tmp_path.replace(target)


def _publish_runtime_event(payload: Dict[str, Any]) -> None:
    import asyncio

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return

    try:
        loop.create_task(publish_event(payload))
    except Exception:
        pass


def _publish_alert_snapshot(alert: Dict[str, Any]) -> None:
    import asyncio

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return

    try:
        loop.create_task(publish_event({"event": "alert", "data": alert}))
    except Exception:
        pass


class AlertManagementService:
    """Handles officer alert operations"""

    def __init__(self):
        self.runtime_session_id = get_runtime_session_id()

    def get_alert(self, alert_id: str, alert_type: str = "transaction") -> Optional[Dict[str, Any]]:
        """Retrieve alert by ID"""
        for alert in LIVE_ALERTS:
            if str(alert.get("alert_id", "")) == str(alert_id):
                return dict(alert)

        try:
            alerts = read_csv(f"{alert_type}_alerts")
            for alert in alerts:
                if str(alert.get("alert_id", "")) == str(alert_id):
                    return alert
        except Exception:
            pass
        return None

    def update_alert_status(
        self,
        alert_id: str,
        new_status: str,
        alert_type: str = "transaction",
        **additional_fields
    ) -> Dict[str, Any]:
        """Update alert status in storage"""
        try:
            alerts = read_csv(f"{alert_type}_alerts")
            file_key = f"{alert_type}_alerts"

            # Find and update the alert
            updated_alert = None
            for alert in alerts:
                if str(alert.get("alert_id", "")) == str(alert_id):
                    alert["status"] = new_status
                    alert["state"] = new_status
                    alert["updated_at"] = _now()
                    if "assigned_officer_id" in additional_fields or "assigned_officer" in additional_fields:
                        officer_id = str(additional_fields.get("assigned_officer_id") or additional_fields.get("assigned_officer") or "").strip()
                        officer_profile = get_investigator_profile(officer_id) if officer_id else {}
                        alert["assigned_officer_id"] = officer_id
                        alert["assigned_officer_name"] = officer_profile.get("assigned_officer_name") or officer_id
                        alert["assigned_officer"] = alert["assigned_officer_name"]
                    for key, value in additional_fields.items():
                        if key not in ["runtime_session_id", "alert_id", "alert_type"]:
                            alert[key] = value
                    alert["runtime_session_id"] = self.runtime_session_id
                    updated_alert = alert
                    break

            if updated_alert:
                # Write back to storage
                df = pd.DataFrame(alerts)
                path_key = f"{alert_type}_alerts"
                from app.services.alerts.alert_storage_service import _file_path, DEFAULT_HEADERS
                path = _file_path(path_key)
                headers = DEFAULT_HEADERS.get(path_key, [])
                
                # Ensure all columns exist
                for col in headers:
                    if col not in df.columns:
                        df[col] = ""
                
                df = df[headers]
                _atomic_write_csv(df, path)

                for live_alert in LIVE_ALERTS:
                    if str(live_alert.get("alert_id", "")) == str(alert_id):
                        live_alert.update(updated_alert)
                        break

                _publish_alert_snapshot(updated_alert)

                return updated_alert
        except Exception as e:
            print(f"Error updating alert: {e}")

        return {}

    def acknowledge_alert(
        self,
        alert_id: str,
        officer_id: str,
        alert_type: str = "transaction"
    ) -> Dict[str, Any]:
        """
        Acknowledge alert - officer takes ownership for investigation
        Status: OPEN → UNDER_REVIEW
        """
        alert = self.get_alert(alert_id, alert_type)
        if not alert:
            raise ValueError(f"Alert {alert_id} not found")

        current_status = alert.get("state", "OPEN")
        if current_status == "UNDER_REVIEW":
            raise ValueError("Already acknowledged")
        if current_status not in ["OPEN"]:
            raise ValueError(f"Cannot acknowledge alert in {current_status} state")

        updated_alert = self.update_alert_status(
            alert_id,
            "UNDER_REVIEW",
            alert_type,
            status="UNDER_REVIEW",
            assigned_officer=officer_id,
            assigned_officer_id=officer_id,
            acknowledged_by=officer_id,
            acknowledged_at=_now()
        )

        case_id = str(alert.get("case_id") or alert.get("source_case_id") or "")
        if case_id:
            try:
                case = case_repository.get_case(case_id) or {"case_id": case_id}
                case_repository.upsert_case({
                    **case,
                    "case_id": case_id,
                    "status": "UNDER_REVIEW",
                    "assigned_officer": officer_id,
                    "updated_at": _now(),
                    "runtime_session_id": self.runtime_session_id,
                })
            except Exception:
                pass

        # Log audit
        log_officer_action(
            officer_id=officer_id,
            action="ACTION_ACKNOWLEDGED",
            alert_id=alert_id,
            case_id=case_id or None,
            old_state=current_status,
            new_state="UNDER_REVIEW",
            reason="Officer acknowledged alert",
            notes="Alert Center acknowledgement",
            metadata={"alert_type": alert_type},
        )
        await_audit_log_officer_action(
            action="ACTION_ACKNOWLEDGED",
            alert_id=alert_id,
            officer_id=officer_id,
            old_state=current_status,
            new_state="UNDER_REVIEW",
            entity_type="ALERT"
        )

        # Publish SSE event
        try:
            _publish_runtime_event({
                "type": "ALERT_ACKNOWLEDGED",
                "alert_id": alert_id,
                "officer_id": officer_id,
                "status": "UNDER_REVIEW",
                "timestamp": _now(),
                "runtime_session_id": self.runtime_session_id
            })
        except Exception:
            pass

        return {
            "status": "SUCCESS",
            "alert_id": alert_id,
            "new_state": "UNDER_REVIEW",
            "assigned_officer": officer_id,
            "case_id": case_id or None,
            "acknowledged_at": _now()
        }

    def escalate_alert(
        self,
        alert_id: str,
        escalated_by: str,
        escalation_reason: str,
        alert_type: str = "transaction"
    ) -> Dict[str, Any]:
        """Escalate alert to higher priority/queue"""
        alert = self.get_alert(alert_id, alert_type)
        if not alert:
            raise ValueError(f"Alert {alert_id} not found")

        current_priority = alert.get("priority", "P3")
        if current_priority == "P1":
            raise ValueError("Already highest priority")
        
        # Determine new priority and queue
        escalation_mapping = {
            "P3": {"priority": "P2", "queue": "AML_REVIEW_QUEUE"},
            "P2": {"priority": "P1", "queue": "AML_CRITICAL_QUEUE"},
        }

        escalation_config = escalation_mapping.get(current_priority, {"priority": "P1", "queue": "MLRO_QUEUE"})
        new_priority = escalation_config["priority"]
        new_queue = escalation_config["queue"]

        # Update alert
        updated_alert = self.update_alert_status(
            alert_id,
            "ESCALATED",
            alert_type,
            status="ESCALATED",
            previous_priority=current_priority,
            new_priority=new_priority,
            priority=new_priority,
            assigned_queue=new_queue,
            escalated_by=escalated_by,
            assigned_officer=escalated_by,
            assigned_officer_id=escalated_by,
            escalated_at=_now(),
            escalation_reason=escalation_reason
        )

        case_id = str(alert.get("case_id") or alert.get("source_case_id") or "")
        if case_id:
            try:
                case = case_repository.get_case(case_id) or {"case_id": case_id}
                case_repository.upsert_case({
                    **case,
                    "case_id": case_id,
                    "priority": new_priority,
                    "status": "ESCALATED",
                    "assigned_officer": case.get("assigned_officer", "") or escalated_by,
                    "escalation_level": new_priority,
                    "updated_at": _now(),
                    "runtime_session_id": self.runtime_session_id,
                })
            except Exception:
                pass

        # Log escalation
        append_row("escalation_log", {
            "alert_id": alert_id,
            "escalated_to": new_queue,
            "escalated_by": escalated_by,
            "reason": escalation_reason,
            "escalation_time": _now(),
            "runtime_session_id": self.runtime_session_id
        })

        # Log audit
        log_officer_action(
            officer_id=escalated_by,
            action="ACTION_ESCALATED",
            alert_id=alert_id,
            case_id=case_id or None,
            old_state=current_priority,
            new_state=new_priority,
            reason=escalation_reason or f"Escalated to {new_queue}",
            notes=f"Escalated to {new_queue}",
            metadata={"alert_type": alert_type, "new_queue": new_queue},
        )
        await_audit_log_officer_action(
            action="ACTION_ESCALATED",
            alert_id=alert_id,
            officer_id=escalated_by,
            old_state=current_priority,
            new_state=new_priority,
            entity_type="ALERT",
            reason=f"Escalated to {new_queue}: {escalation_reason}"
        )

        # Publish SSE event
        try:
            _publish_runtime_event({
                "type": "ALERT_ESCALATED",
                "alert_id": alert_id,
                "old_priority": current_priority,
                "new_priority": new_priority,
                "new_queue": new_queue,
                "officer_id": escalated_by,
                "timestamp": _now(),
                "runtime_session_id": self.runtime_session_id
            })
        except Exception:
            pass

        return {
            "status": "SUCCESS",
            "alert_id": alert_id,
            "old_priority": current_priority,
            "new_priority": new_priority,
            "new_queue": new_queue,
            "case_id": case_id or None,
            "escalation_reason": escalation_reason
        }

    def request_edd(
        self,
        alert_id: str,
        requested_by: str,
        required_documents: list = None,
        alert_type: str = "transaction"
    ) -> Dict[str, Any]:
        """Request Enhanced Due Diligence"""
        alert = self.get_alert(alert_id, alert_type)
        if not alert:
            raise ValueError(f"Alert {alert_id} not found")

        if required_documents is None:
            required_documents = [
                "PAN",
                "Proof of Funds",
                "Selfie",
                "Address Proof",
                "Income Proof"
            ]

        updated_alert = self.update_alert_status(
            alert_id,
            "EDD_REQUESTED",
            alert_type,
            requires_edd=True,
            edd_status="PENDING_CUSTOMER",
            edd_requested_by=requested_by,
            edd_requested_at=_now(),
            edd_required_documents=str(required_documents),
            assigned_officer=requested_by,
            assigned_officer_id=requested_by,
        )

        case_id = str(alert.get("case_id") or alert.get("source_case_id") or "")
        if case_id:
            try:
                case = case_repository.get_case(case_id) or {"case_id": case_id}
                case_repository.upsert_case({
                    **case,
                    "case_id": case_id,
                    "status": "EDD_REQUESTED",
                    "assigned_officer": requested_by,
                    "updated_at": _now(),
                    "runtime_session_id": self.runtime_session_id,
                })
            except Exception:
                pass

        # Log audit
        await_audit_log_officer_action(
            action="REQUEST_EDD",
            alert_id=alert_id,
            officer_id=requested_by,
            old_state=alert.get("state", "UNKNOWN"),
            new_state="EDD_REQUESTED",
            entity_type="ALERT",
            reason=f"EDD requested with documents: {', '.join(required_documents)}"
        )

        # Publish SSE event
        try:
            _publish_runtime_event({
                "type": "EDD_REQUESTED",
                "alert_id": alert_id,
                "requested_by": requested_by,
                "required_documents": required_documents,
                "timestamp": _now(),
                "runtime_session_id": self.runtime_session_id
            })
        except Exception:
            pass

        return {
            "status": "SUCCESS",
            "alert_id": alert_id,
            "edd_status": "PENDING_CUSTOMER",
            "required_documents": required_documents,
            "requested_at": _now()
        }

    def close_alert(
        self,
        alert_id: str,
        closed_by: str,
        resolution: str,
        remarks: str = "",
        alert_type: str = "transaction"
    ) -> Dict[str, Any]:
        """
        Close alert - investigation complete
        Can only close if status is UNDER_REVIEW or ESCALATED
        """
        alert = self.get_alert(alert_id, alert_type)
        if not alert:
            raise ValueError(f"Alert {alert_id} not found")

        current_status = alert.get("state", "OPEN")
        if current_status == "CLOSED":
            raise ValueError("Already Closed")
        if current_status not in ["UNDER_REVIEW", "ESCALATED"]:
            raise ValueError(f"Cannot close alert in {current_status} state. Must be UNDER_REVIEW or ESCALATED")

        updated_alert = self.update_alert_status(
            alert_id,
            "CLOSED",
            alert_type,
            status="CLOSED",
            closed_by=closed_by,
            closed_at=_now(),
            resolution=resolution,
            remarks=remarks,
            assigned_officer=closed_by,
            assigned_officer_id=closed_by,
        )

        # If linked case exists, close it too
        source_alert_id = alert.get("alert_id")
        case_id = str(alert.get("case_id") or alert.get("source_case_id") or "")
        try:
            cases = case_repository.list_cases()
            for case in cases:
                if str(case.get("source_alert_id", "")) == str(source_alert_id):
                    case_repository.upsert_case({
                        "case_id": case["case_id"],
                        "status": "CLOSED",
                        "closed_at": _now(),
                        "resolution": resolution,
                        "remarks": remarks,
                        **{k: v for k, v in case.items() if k not in ["status", "closed_at", "resolution", "remarks"]}
                    })
                    break
            if case_id:
                case = case_repository.get_case(case_id)
                if case:
                    case_repository.upsert_case({
                        **case,
                        "case_id": case_id,
                        "status": "CLOSED",
                        "closed_at": _now(),
                        "resolution": resolution,
                        "assigned_officer": closed_by,
                        "updated_at": _now(),
                        "runtime_session_id": self.runtime_session_id,
                    })
        except Exception:
            pass

        # Log audit
        log_officer_action(
            officer_id=closed_by,
            action="ACTION_CLOSED",
            alert_id=alert_id,
            case_id=case_id or None,
            old_state=current_status,
            new_state="CLOSED",
            reason=resolution,
            notes=remarks,
            metadata={"alert_type": alert_type},
        )
        await_audit_log_officer_action(
            action="ACTION_CLOSED",
            alert_id=alert_id,
            officer_id=closed_by,
            old_state=current_status,
            new_state="CLOSED",
            entity_type="ALERT",
            reason=f"Closed with resolution: {resolution}. {remarks}"
        )

        # Publish SSE event
        try:
            _publish_runtime_event({
                "type": "ALERT_CLOSED",
                "alert_id": alert_id,
                "officer_id": closed_by,
                "resolution": resolution,
                "timestamp": _now(),
                "runtime_session_id": self.runtime_session_id
            })
        except Exception:
            pass

        return {
            "status": "SUCCESS",
            "alert_id": alert_id,
            "new_state": "CLOSED",
            "resolution": resolution,
            "case_id": case_id or None,
            "closed_at": _now()
        }


def await_audit_log_officer_action(
    action: str,
    alert_id: str = "",
    officer_id: str = "",
    old_state: str = "",
    new_state: str = "",
    entity_type: str = "",
    reason: str = ""
) -> None:
    """Log officer action to audit trail"""
    try:
        log_control_decision({
            "event": action,
            "alert_id": alert_id,
            "actor": officer_id,
            "entity_type": entity_type,
            "old_state": old_state,
            "new_state": new_state,
            "reason": reason,
            "timestamp": _now(),
            "runtime_session_id": get_runtime_session_id()
        })
    except Exception as e:
        print(f"Error logging audit: {e}")


# Global instance
alert_management_service = AlertManagementService()
