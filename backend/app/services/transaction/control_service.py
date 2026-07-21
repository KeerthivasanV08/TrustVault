# backend/app/services/control_service.py

from datetime import datetime

import pandas as pd

from app.core.policy_engine import get_policy_engine
from app.core import storage_paths

from app.services.transaction.audit_service import (
    log_control_decision
)

from app.services.shared.reporting_service import (
    generate_report
)

from app.services.transaction.whitelist_service import (
    WhitelistService
)

PROCESSED_DIR = storage_paths.PROCESSED_DIR
RUNTIME_DIR = storage_paths.RUNTIME_DIR
POLICY = get_policy_engine()


def _load_indexed_csv(path, index_col):
    try:
        frame = pd.read_csv(path)
        if index_col not in frame.columns:
            frame[index_col] = ""
        return frame.set_index(index_col)
    except Exception:
        return pd.DataFrame(columns=[index_col]).set_index(index_col)


class RegulatoryControlEngine:

    def __init__(self):

        # ---------------------------------------------------
        # HIGH SPEED INDEXED LOAD
        # ---------------------------------------------------

        self.users = _load_indexed_csv(
            PROCESSED_DIR / "user_features.csv",
            "user_id",
        )

        self.velocity = _load_indexed_csv(
            RUNTIME_DIR / "user_velocity_state.csv",
            "user_id",
        )

        self.whitelist_service = (
            WhitelistService()
        )

    def evaluate(self, txn):

        sender_id = txn["sender_id"]

        amount = txn["amount"]

        # ---------------------------------------------------
        # WHITELIST BYPASS
        # ---------------------------------------------------

        if self.whitelist_service.is_whitelisted(
            sender_id
        ):

            return {
                "decision": "PASS",
                "reason": "WHITELISTED_USER"
            }

        # ---------------------------------------------------
        # ACCOUNT FREEZE CHECK
        # ---------------------------------------------------

        try:
            from app.services.officer.account_operations_service import account_operations_service
            if account_operations_service.is_account_frozen(sender_id):
                log_control_decision(
                    sender_id,
                    "transaction",
                    "BLOCK",
                    "ACCOUNT_FROZEN"
                )
                return {
                    "decision": "BLOCK",
                    "reason": "ACCOUNT_FROZEN"
                }
        except Exception:
            pass

        # ---------------------------------------------------
        # USER LOOKUP
        # ---------------------------------------------------

        try:

            user = self.users.loc[sender_id]

            velocity = self.velocity.loc[sender_id]

        except KeyError:

            return {
                "decision": "BLOCK",
                "reason": "UNKNOWN_USER"
            }

        # ---------------------------------------------------
        # HARD BLOCKS
        # ---------------------------------------------------

        # 1. SIM / DEVICE BINDING

        if txn["device_id"] != user["device_id"]:

            log_control_decision(
                sender_id,
                "transaction",
                "BLOCK",
                "DEVICE_BINDING_MISMATCH"
            )

            return {
                "decision": "BLOCK",
                "reason": "DEVICE_BINDING_MISMATCH"
            }

        # 2. NEW USER LIMIT

        created_at = pd.to_datetime(
            user["created_at"]
        )

        account_age_hours = (
            datetime.now() - created_at
        ).total_seconds() / 3600

        if (
            account_age_hours < 24 and
            amount >
            POLICY.get_transaction_rule("new_user_upi_limit", 5000)
        ):

            log_control_decision(
                sender_id,
                "transaction",
                "BLOCK",
                "NEW_USER_LIMIT_EXCEEDED"
            )

            return {
                "decision": "BLOCK",
                "reason": "NEW_USER_LIMIT_EXCEEDED"
            }

        # 3. DAILY UPI LIMIT

        if (
            velocity["rolling_24h_sum"] + amount >
            POLICY.get_transaction_rule("upi_daily_limit", 100000)
        ):

            log_control_decision(
                sender_id,
                "transaction",
                "BLOCK",
                "DAILY_UPI_LIMIT_EXCEEDED"
            )

            return {
                "decision": "BLOCK",
                "reason": "DAILY_UPI_LIMIT_EXCEEDED"
            }

        # 4. PAN MANDATE

        if (
            amount >=
            POLICY.get_transaction_rule("pan_cash_threshold", 50000)
            and
            user["kyc_status"] != "verified"
        ):

            log_control_decision(
                sender_id,
                "transaction",
                "BLOCK",
                "PAN_REQUIRED_ABOVE_50K"
            )

            return {
                "decision": "BLOCK",
                "reason": "PAN_REQUIRED_ABOVE_50K"
            }

        # ---------------------------------------------------
        # EDD TRIGGERS
        # ---------------------------------------------------

        edd_flags = []

        # Mule Hub

        if (
            user.get(
                "device_shared_count",
                0
            ) >=
            POLICY.get_transaction_rule("mule_hub_threshold", 3)
        ):

            edd_flags.append(
                "I4C_MULE_HUB"
            )

        # Dormancy

        if (
            user.get(
                "days_since_last_txn",
                0
            ) >
            POLICY.get_transaction_rule("dormancy_days", 180)
            and amount > 10000
        ):

            edd_flags.append(
                "DORMANT_ACCOUNT_REACTIVATION"
            )

        # Geo Anomaly

        if (
            user.get(
                "city_mismatch_flag",
                0
            ) == 1
            and amount >
            POLICY.get_transaction_rule("geo_limit", 25000)
        ):

            edd_flags.append(
                "GEO_ANOMALY"
            )

        # Rooted Device

        if (
            user.get(
                "root_status",
                False
            )
            or
            user.get(
                "app_cloner_flag",
                False
            )
        ):

            edd_flags.append(
                "DEVICE_TAMPERING"
            )

        # ---------------------------------------------------
        # REPORTING RULES
        # ---------------------------------------------------

        if (
            velocity.get(
                "fy_aggregate_credits",
                0
            ) + amount >
            POLICY.get_transaction_rule("savings_sft_limit", 1000000)
        ):

            generate_report(
                sender_id,
                "SFT",
                "SAVINGS_LIMIT_EXCEEDED",
                amount
            )

        if amount > POLICY.get_transaction_rule("ctr_limit", 1000000):

            generate_report(
                sender_id,
                "CTR",
                "CASH_THRESHOLD_EXCEEDED",
                amount
            )

        # ---------------------------------------------------
        # FINAL DECISION
        # ---------------------------------------------------

        if len(edd_flags) > 0:

            log_control_decision(
                sender_id,
                "transaction",
                "REVIEW",
                ",".join(edd_flags)
            )

            return {
                "decision": "REVIEW",
                "reason": edd_flags
            }

        return {
            "decision": "PASS",
            "reason": "COMPLIANT"
        }