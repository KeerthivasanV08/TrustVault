"""
Case Operations Service

Handles:
- Close cases
- Reopen cases
- Update case status
- Track case history
- Integration with alert management
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional

from app.core.runtime_context import get_runtime_session_id
from app.services.cases.case_repository import case_repository
from app.db.file_storage import log_control_decision
from app.realtime.transaction_memory_store import publish_event
from app.services.transaction.audit_service import log_officer_action
import asyncio


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class CaseOperationsService:
    """Handles case-specific operations"""

    def __init__(self):
        self.runtime_session_id = get_runtime_session_id()

    def get_case(self, case_id: str) -> Optional[Dict[str, Any]]:
        """Get case by ID"""
        return case_repository.get_case(case_id)

    def close_case(
        self,
        case_id: str,
        closed_by: str,
        resolution: str,
        remarks: str = ""
    ) -> Dict[str, Any]:
        """
        Close case - investigation complete
        Case stays visible in history
        """
        case = self.get_case(case_id)
        if not case:
            raise ValueError(f"Case {case_id} not found")

        current_status = case.get("status", "OPEN")

        # Update case
        updated_case = case_repository.upsert_case({
            "case_id": case_id,
            "status": "CLOSED",
            "closed_at": _now(),
            "closed_by": closed_by,
            "resolution": resolution,
            "remarks": remarks,
            "runtime_session_id": self.runtime_session_id,
            # Preserve all other fields
            **{k: v for k, v in case.items() if k not in ["status", "closed_at", "closed_by", "resolution", "remarks", "updated_at"]}
        })

        # Log audit
        log_control_decision({
            "event": "CASE_CLOSED",
            "case_id": case_id,
            "actor": closed_by,
            "entity_type": "CASE",
            "old_state": current_status,
            "new_state": "CLOSED",
            "reason": f"Case closed - {resolution}. {remarks}",
            "timestamp": _now(),
            "runtime_session_id": self.runtime_session_id
        })
        log_officer_action(
            officer_id=closed_by,
            action="CASE_CLOSED",
            case_id=case_id,
            old_state=current_status,
            new_state="CLOSED",
            reason=resolution,
            notes=remarks,
            metadata={"case_id": case_id},
        )

        # Publish SSE event
        try:
            asyncio.create_task(publish_event({
                "type": "CASE_CLOSED",
                "case_id": case_id,
                "closed_by": closed_by,
                "resolution": resolution,
                "timestamp": _now(),
                "runtime_session_id": self.runtime_session_id
            }))
        except Exception:
            pass

        return {
            "status": "SUCCESS",
            "case_id": case_id,
            "new_state": "CLOSED",
            "resolution": resolution,
            "closed_at": _now()
        }

    def reopen_case(
        self,
        case_id: str,
        reopened_by: str,
        reason: str = ""
    ) -> Dict[str, Any]:
        """Reopen closed case"""
        case = self.get_case(case_id)
        if not case:
            raise ValueError(f"Case {case_id} not found")

        current_status = case.get("status", "OPEN")
        if current_status != "CLOSED":
            raise ValueError(f"Can only reopen CLOSED cases. Current status: {current_status}")

        # Update case
        updated_case = case_repository.upsert_case({
            "case_id": case_id,
            "status": "REOPENED",
            "reopened_at": _now(),
            "reopened_by": reopened_by,
            "reopen_reason": reason,
            "runtime_session_id": self.runtime_session_id,
            # Preserve all other fields
            **{k: v for k, v in case.items() if k not in ["status", "reopened_at", "reopened_by", "reopen_reason", "updated_at"]}
        })

        # Log audit
        log_control_decision({
            "event": "CASE_REOPENED",
            "case_id": case_id,
            "actor": reopened_by,
            "entity_type": "CASE",
            "old_state": "CLOSED",
            "new_state": "REOPENED",
            "reason": reason,
            "timestamp": _now(),
            "runtime_session_id": self.runtime_session_id
        })
        log_officer_action(
            officer_id=reopened_by,
            action="CASE_REOPENED",
            case_id=case_id,
            old_state="CLOSED",
            new_state="REOPENED",
            reason=reason,
            notes=f"Case reopened: {case_id}",
            metadata={"case_id": case_id},
        )

        # Publish SSE event
        try:
            asyncio.create_task(publish_event({
                "type": "CASE_REOPENED",
                "case_id": case_id,
                "reopened_by": reopened_by,
                "timestamp": _now(),
                "runtime_session_id": self.runtime_session_id
            }))
        except Exception:
            pass

        return {
            "status": "SUCCESS",
            "case_id": case_id,
            "new_state": "REOPENED",
            "reopened_at": _now()
        }


# Global instance
case_operations_service = CaseOperationsService()
