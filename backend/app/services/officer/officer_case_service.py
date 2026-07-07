import pandas as pd
from datetime import datetime
from uuid import uuid4
from pathlib import Path

from app.core import storage_paths
from app.utils.file_utils import safe_to_csv, ensure_parent_dir

CASE_FILE = storage_paths.CASES_DIR / "officer_cases.csv"


class OfficerCaseService:
    def __init__(self):
        # ensure parent dirs and initialize CSV with headers if missing
        ensure_parent_dir(CASE_FILE)
        if not CASE_FILE.exists():
            safe_to_csv(
                pd.DataFrame(columns=[
                    "case_id",
                    "txn_id",
                    "user_id",
                    "risk_score",
                    "evidence_summary",
                    "status",
                    "assigned_to",
                    "created_at",
                ]),
                CASE_FILE,
            )

    def create_case(self, txn_id, sender_id, evidence, score):

        case = {
            "case_id": str(uuid4()),
            "txn_id": txn_id,
            "user_id": sender_id,
            "risk_score": score,
            "evidence_summary": str(evidence),
            "status": "OPEN",
            "assigned_to": None,
            "created_at": datetime.now().isoformat()
        }

        df = pd.read_csv(CASE_FILE) if CASE_FILE.exists() else pd.DataFrame()
        df = pd.concat([df, pd.DataFrame([case])], ignore_index=True)
        safe_to_csv(df, CASE_FILE)

        return case

    def update_case_status(self, case_id, status, officer_id):
        df = pd.read_csv(CASE_FILE) if CASE_FILE.exists() else pd.DataFrame()

        if not df.empty:
            df.loc[df["case_id"] == case_id, "status"] = status
            df.loc[df["case_id"] == case_id, "assigned_to"] = officer_id
            safe_to_csv(df, CASE_FILE)

        return {"case_id": case_id, "status": status}