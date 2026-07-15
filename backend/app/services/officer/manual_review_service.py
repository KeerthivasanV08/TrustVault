from app.services.cases.case_repository import case_repository

from .freeze_service import FreezeService
from .officer_case_service import OfficerCaseService
from .sar_service import SARService


class ManualReviewService:

    def __init__(self):
        self.freezer = FreezeService()
        self.cases = OfficerCaseService()
        self.sar = SARService()

    async def resolve_transaction(self, case_id, decision, officer_id, officer_notes=""):

        case = case_repository.get_case(case_id)

        if not case:
            return {"error": "CASE_NOT_FOUND"}

        user_id = case["user_id"]

        # =========================
        # REJECT = FRAUD CONFIRMED
        # =========================
        if decision == "REJECT":

            self.freezer.apply_freeze(
                user_id=user_id,
                freeze_type="TOTAL"
            )

            sar_report = self.sar.generate_sar_form(
                case,
                officer_notes
            )

            return {
                "action": "ACCOUNT_FROZEN",
                "sar_filed": True,
                "sar_report": sar_report
            }

        # =========================
        # RELEASE = FALSE POSITIVE
        # =========================
        else:

            return {
                "action": "TRANSACTION_RELEASED",
                "status": "CLOSED"
            }