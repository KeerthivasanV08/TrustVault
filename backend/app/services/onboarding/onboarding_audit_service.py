import pandas as pd
from datetime import datetime
from threading import Lock

from app.core import storage_paths
from app.utils.file_utils import safe_append_csv, ensure_parent_dir

LOG_PATH = storage_paths.AUDIT_DIR / "onboarding_results.csv"


class OnboardingAuditService:
    _lock = Lock()

    def log(self, record: dict):
        ensure_parent_dir(LOG_PATH)

        record["created_at"] = datetime.utcnow().isoformat()

        df = pd.DataFrame([record])

        with OnboardingAuditService._lock:
            safe_append_csv(df, LOG_PATH)