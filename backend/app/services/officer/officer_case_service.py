from datetime import datetime, timezone
from uuid import uuid4

from app.core.runtime_context import get_runtime_session_id
from app.services.cases.case_repository import case_repository


class OfficerCaseService:
    def __init__(self):
        self.repository = case_repository

    def create_case(self, txn_id, sender_id, evidence, score):

        case = {
            "case_id": str(uuid4()),
            "transaction_id": txn_id,
            "user_id": sender_id,
            "priority": "P1" if float(score or 0) >= 75 else "P2" if float(score or 0) >= 50 else "P3",
            "status": "OPEN",
            "assigned_officer": "",
            "assigned_team": "",
            "creation_source": "MANUAL_OFFICER",
            "reason": str(evidence),
            "evidence": str(evidence),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "runtime_session_id": get_runtime_session_id(),
        }

        return self.repository.upsert_case(case)

    def update_case_status(self, case_id, status, officer_id):
        case = self.repository.get_case(case_id) or {"case_id": case_id}
        case.update({
            "status": status,
            "assigned_officer": officer_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "runtime_session_id": get_runtime_session_id(),
        })
        return self.repository.upsert_case(case)