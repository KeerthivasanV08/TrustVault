import pandas as pd
from datetime import datetime

from app.core import storage_paths
from app.utils.file_utils import ensure_parent_dir, safe_to_csv, safe_append_csv

WHITELIST_FILE = storage_paths.DATA_DIR / "reference" / "whitelist.csv"


class WhitelistOverrideService:

    def __init__(self):
        ensure_parent_dir(WHITELIST_FILE)
        if not WHITELIST_FILE.exists():
            safe_to_csv(pd.DataFrame(columns=[
                "user_id",
                "reason",
                "added_by",
                "timestamp"
            ]), WHITELIST_FILE)

    def add_to_whitelist(self, user_id, reason, officer_id):

        new_entry = {
            "user_id": user_id,
            "reason": reason,
            "added_by": officer_id,
            "timestamp": datetime.now().isoformat()
        }

        row = pd.DataFrame([new_entry])

        if not WHITELIST_FILE.exists():
            safe_to_csv(row, WHITELIST_FILE)
        else:
            safe_append_csv(row, WHITELIST_FILE)

        return {"status": "WHITELISTED", "user_id": user_id}