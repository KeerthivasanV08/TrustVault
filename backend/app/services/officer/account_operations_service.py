"""
Account Operations Service

Handles:
- Freeze/Unfreeze accounts
- Whitelist accounts
- Track freeze status
- Integration with control service for blocking transactions
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional
import pandas as pd

from app.core.runtime_context import get_runtime_session_id
from app.core import storage_paths
from app.db.file_storage import log_control_decision
from app.realtime.transaction_memory_store import publish_event
from app.services.transaction.audit_service import log_officer_action
from app.utils.file_utils import ensure_parent_dir
import asyncio


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# Freeze registry
FREEZE_REGISTRY_PATH = storage_paths.PROCESSED_DIR / "accounts" / "freeze_registry.csv"
WHITELIST_REGISTRY_PATH = storage_paths.DATA_DIR / "reference" / "whitelist.csv"

FREEZE_COLUMNS = [
    "user_id",
    "account_status",
    "freeze_type",
    "freeze_reason",
    "frozen_by",
    "frozen_at",
    "lift_reason",
    "lifted_by",
    "lifted_at",
    "runtime_session_id"
]

WHITELIST_COLUMNS = [
    "user_id",
    "whitelisted",
    "whitelisted_by",
    "whitelisted_at",
    "reason",
    "runtime_session_id"
]


def _ensure_freeze_registry() -> None:
    ensure_parent_dir(FREEZE_REGISTRY_PATH)
    if not FREEZE_REGISTRY_PATH.exists():
        df = pd.DataFrame(columns=FREEZE_COLUMNS)
        df.to_csv(FREEZE_REGISTRY_PATH, index=False)


def _ensure_whitelist_registry() -> None:
    ensure_parent_dir(WHITELIST_REGISTRY_PATH)
    if not WHITELIST_REGISTRY_PATH.exists():
        df = pd.DataFrame(columns=WHITELIST_COLUMNS)
        df.to_csv(WHITELIST_REGISTRY_PATH, index=False)


def _atomic_write(df: pd.DataFrame, path) -> None:
    ensure_parent_dir(path)
    tmp_path = path.with_suffix(".tmp")
    df.to_csv(tmp_path, index=False)
    tmp_path.replace(path)


class AccountOperationsService:
    """Handles account freeze, whitelist, and status operations"""

    def __init__(self):
        self.runtime_session_id = get_runtime_session_id()
        _ensure_freeze_registry()
        _ensure_whitelist_registry()

    def get_account_status(self, user_id: str) -> Dict[str, Any]:
        """Get current account status"""
        try:
            _ensure_freeze_registry()
            df = pd.read_csv(FREEZE_REGISTRY_PATH)
            rows = df[df["user_id"].astype(str) == str(user_id)]
            if not rows.empty:
                return rows.tail(1).iloc[0].to_dict()
        except Exception:
            pass

        return {
            "user_id": str(user_id),
            "account_status": "ACTIVE",
            "freeze_type": "",
            "frozen_by": "",
            "frozen_at": ""
        }

    def is_account_frozen(self, user_id: str) -> bool:
        """Check if account is frozen"""
        status = self.get_account_status(user_id)
        return status.get("account_status", "ACTIVE") == "FROZEN"

    def freeze_account(
        self,
        user_id: str,
        freeze_type: str = "DEBIT_FREEZE",
        freeze_reason: str = "",
        frozen_by: str = "",
        case_id: str | None = None,
    ) -> Dict[str, Any]:
        """
        Freeze account
        - Validation: Don't freeze twice (return 409 if already frozen)
        - freeze_type: DEBIT_FREEZE (default), CREDIT_FREEZE, TOTAL_FREEZE
        """
        # Check if already frozen
        if self.is_account_frozen(user_id):
            raise ValueError(f"Account {user_id} is already frozen. Cannot freeze twice.")

        # Add freeze record
        try:
            _ensure_freeze_registry()
            df = pd.read_csv(FREEZE_REGISTRY_PATH)
        except Exception:
            df = pd.DataFrame(columns=FREEZE_COLUMNS)

        freeze_record = {
            "user_id": str(user_id),
            "account_status": "FROZEN",
            "freeze_type": freeze_type,
            "freeze_reason": freeze_reason,
            "frozen_by": frozen_by,
            "frozen_at": _now(),
            "lift_reason": "",
            "lifted_by": "",
            "lifted_at": "",
            "runtime_session_id": self.runtime_session_id
        }

        df = pd.concat([df, pd.DataFrame([freeze_record])], ignore_index=True)
        _atomic_write(df, FREEZE_REGISTRY_PATH)

        # Log audit
        log_control_decision({
            "event": "ACCOUNT_FROZEN",
            "user_id": user_id,
            "actor": frozen_by,
            "entity_type": "ACCOUNT",
            "old_state": "ACTIVE",
            "new_state": "FROZEN",
            "reason": f"{freeze_type}: {freeze_reason}",
            "timestamp": _now(),
            "runtime_session_id": self.runtime_session_id
        })
        log_officer_action(
            officer_id=frozen_by,
            action="ACCOUNT_FROZEN",
            case_id=case_id,
            old_state="ACTIVE",
            new_state="FROZEN",
            reason=f"{freeze_type}: {freeze_reason}".strip(),
            notes=f"Freeze applied to {user_id}",
            metadata={"user_id": user_id, "freeze_type": freeze_type},
        )

        # Publish SSE event
        try:
            asyncio.create_task(publish_event({
                "type": "ACCOUNT_FROZEN",
                "user_id": user_id,
                "freeze_type": freeze_type,
                "frozen_by": frozen_by,
                "timestamp": _now(),
                "runtime_session_id": self.runtime_session_id
            }))
        except Exception:
            pass

        return {
            "status": "SUCCESS",
            "user_id": user_id,
            "account_status": "FROZEN",
            "freeze_type": freeze_type,
            "frozen_at": _now()
        }

    def unfreeze_account(
        self,
        user_id: str,
        lift_reason: str = "",
        lifted_by: str = ""
    ) -> Dict[str, Any]:
        """Unfreeze account"""
        if not self.is_account_frozen(user_id):
            raise ValueError(f"Account {user_id} is not frozen.")

        try:
            _ensure_freeze_registry()
            df = pd.read_csv(FREEZE_REGISTRY_PATH)
        except Exception:
            df = pd.DataFrame(columns=FREEZE_COLUMNS)

        # Update most recent freeze record
        rows = df[df["user_id"].astype(str) == str(user_id)]
        if not rows.empty:
            idx = rows.index[-1]
            df.loc[idx, "account_status"] = "ACTIVE"
            df.loc[idx, "lift_reason"] = lift_reason
            df.loc[idx, "lifted_by"] = lifted_by
            df.loc[idx, "lifted_at"] = _now()

        _atomic_write(df, FREEZE_REGISTRY_PATH)

        # Log audit
        log_control_decision({
            "event": "ACCOUNT_UNFROZEN",
            "user_id": user_id,
            "actor": lifted_by,
            "entity_type": "ACCOUNT",
            "old_state": "FROZEN",
            "new_state": "ACTIVE",
            "reason": lift_reason,
            "timestamp": _now(),
            "runtime_session_id": self.runtime_session_id
        })
        log_officer_action(
            officer_id=lifted_by,
            action="ACCOUNT_UNFROZEN",
            case_id=None,
            old_state="FROZEN",
            new_state="ACTIVE",
            reason=lift_reason,
            notes=f"Freeze lifted for {user_id}",
            metadata={"user_id": user_id},
        )

        # Publish SSE event
        try:
            asyncio.create_task(publish_event({
                "type": "ACCOUNT_UNFROZEN",
                "user_id": user_id,
                "lifted_by": lifted_by,
                "timestamp": _now(),
                "runtime_session_id": self.runtime_session_id
            }))
        except Exception:
            pass

        return {
            "status": "SUCCESS",
            "user_id": user_id,
            "account_status": "ACTIVE",
            "lifted_at": _now()
        }

    def whitelist_account(
        self,
        user_id: str,
        reason: str = "",
        whitelisted_by: str = ""
    ) -> Dict[str, Any]:
        """Add account to whitelist"""
        try:
            _ensure_whitelist_registry()
            df = pd.read_csv(WHITELIST_REGISTRY_PATH)
        except Exception:
            df = pd.DataFrame(columns=WHITELIST_COLUMNS)

        whitelist_record = {
            "user_id": str(user_id),
            "whitelisted": True,
            "whitelisted_by": whitelisted_by,
            "whitelisted_at": _now(),
            "reason": reason,
            "runtime_session_id": self.runtime_session_id
        }

        # Check if already whitelisted
        existing = df[df["user_id"].astype(str) == str(user_id)]
        if not existing.empty:
            idx = existing.index[-1]
            df.loc[idx] = whitelist_record
        else:
            df = pd.concat([df, pd.DataFrame([whitelist_record])], ignore_index=True)

        _atomic_write(df, WHITELIST_REGISTRY_PATH)

        # Log audit
        log_control_decision({
            "event": "ACCOUNT_WHITELISTED",
            "user_id": user_id,
            "actor": whitelisted_by,
            "entity_type": "ACCOUNT",
            "old_state": "MONITORED",
            "new_state": "WHITELISTED",
            "reason": reason,
            "timestamp": _now(),
            "runtime_session_id": self.runtime_session_id
        })
        log_officer_action(
            officer_id=whitelisted_by,
            action="ACCOUNT_WHITELISTED",
            case_id=None,
            old_state="MONITORED",
            new_state="WHITELISTED",
            reason=reason,
            notes=f"Whitelist added for {user_id}",
            metadata={"user_id": user_id},
        )

        # Publish SSE event
        try:
            asyncio.create_task(publish_event({
                "type": "ACCOUNT_WHITELISTED",
                "user_id": user_id,
                "whitelisted_by": whitelisted_by,
                "timestamp": _now(),
                "runtime_session_id": self.runtime_session_id
            }))
        except Exception:
            pass

        return {
            "status": "SUCCESS",
            "user_id": user_id,
            "whitelisted": True,
            "whitelisted_at": _now()
        }

    def is_whitelisted(self, user_id: str) -> bool:
        """Check if account is whitelisted"""
        try:
            _ensure_whitelist_registry()
            df = pd.read_csv(WHITELIST_REGISTRY_PATH)
            rows = df[df["user_id"].astype(str) == str(user_id)]
            if not rows.empty:
                return bool(rows.tail(1).iloc[0].get("whitelisted", False))
        except Exception:
            pass
        return False


# Global instance
account_operations_service = AccountOperationsService()
