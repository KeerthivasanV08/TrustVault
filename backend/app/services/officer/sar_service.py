from datetime import datetime

class SARService:

    def generate_sar_form(self, case_details, officer_notes):

        report = {
            "report_type": "STR_SAR",
            "reporting_entity": "TRUSTVAULT_AML_ENGINE",
            "target_user": case_details["user_id"],
            "txn_id": case_details.get("txn_id"),
            "risk_score": case_details.get("risk_score"),
            "suspicion_reason": case_details["evidence_summary"],
            "officer_assessment": officer_notes,
            "timestamp": datetime.now().isoformat()
        }

        return report