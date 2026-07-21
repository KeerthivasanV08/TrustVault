import pandas as pd
from datetime import datetime
from threading import Lock

from app.core import storage_paths
from app.core.runtime_context import get_runtime_session_id
from app.utils.file_utils import safe_append_csv, ensure_parent_dir

LOG_PATH = storage_paths.ONBOARDING_DECISIONS_AUDIT_PATH


class OnboardingAuditService:
    _lock = Lock()

    def log(self, record: dict):
        ensure_parent_dir(LOG_PATH)

        record["created_at"] = datetime.utcnow().isoformat()
        record["runtime_session_id"] = get_runtime_session_id()
        record.setdefault("event_id", f"ONB-{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}")

        df = pd.DataFrame([record])

        with OnboardingAuditService._lock:
            safe_append_csv(df, LOG_PATH)