import pandas as pd

from app.core import storage_paths
from app.utils.file_utils import ensure_parent_dir, safe_to_csv

USER_FILE = storage_paths.PROCESSED_DIR / "user_features.csv"


class FreezeService:

    def apply_freeze(self, user_id, freeze_type="TOTAL"):

        ensure_parent_dir(USER_FILE)
        if USER_FILE.exists():
            df = pd.read_csv(USER_FILE)
        else:
            df = pd.DataFrame(columns=["user_id", "account_status"])

        if "account_status" not in df.columns:
            df["account_status"] = "ACTIVE"

        if user_id in df["user_id"].astype(str).tolist():
            df.loc[df["user_id"].astype(str) == str(user_id), "account_status"] = "FROZEN"
        else:
            df = pd.concat([df, pd.DataFrame([{"user_id": user_id, "account_status": "FROZEN"}])], ignore_index=True)

        safe_to_csv(df, USER_FILE)

        print(f"CRITICAL: {freeze_type} freeze applied on {user_id}")

        return {
            "status": "SUCCESS",
            "user_id": user_id,
            "action": freeze_type
        }

    def lift_freeze(self, user_id):

        ensure_parent_dir(USER_FILE)
        if USER_FILE.exists():
            df = pd.read_csv(USER_FILE)
        else:
            df = pd.DataFrame(columns=["user_id", "account_status"])

        if "user_id" in df.columns:
            df.loc[df["user_id"] == user_id, "account_status"] = "ACTIVE"

        safe_to_csv(df, USER_FILE)

        return {"status": "ACTIVE", "user_id": user_id}