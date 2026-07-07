from app.core import storage_paths

from .freeze_service import FreezeService
from .officer_case_service import OfficerCaseService
from .sar_service import SARService


class ManualReviewService:

    def __init__(self):
        self.freezer = FreezeService()
        self.cases = OfficerCaseService()
        self.sar = SARService()

    async def resolve_transaction(self, case_id, decision, officer_id, officer_notes=""):

        # fetch case
        import pandas as pd

        CASE_FILE = storage_paths.CASES_DIR / "officer_cases.csv"

        df = pd.read_csv(CASE_FILE)
        case = df[df["case_id"] == case_id].to_dict("records")

        if not case:
            return {"error": "CASE_NOT_FOUND"}

        case = case[0]

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