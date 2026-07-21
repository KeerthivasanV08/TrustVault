from collections import deque
from datetime import datetime, timedelta, timezone

import pandas as pd

from app.realtime.transaction_memory_store import (
    USER_RECENT_HISTORY,
    USER_VELOCITY_STATE,
    initialize_runtime_store,
    update_user_velocity_state,
)


def _filter_last_24_hours(rows: list[dict], timestamp: pd.Timestamp) -> list[dict]:
    if not rows:
        return []

    window_start = timestamp - timedelta(hours=24)
    filtered: list[dict] = []
    for row in rows:
        row_timestamp = pd.to_datetime(row.get("timestamp"), utc=True, errors="coerce")
        if pd.isna(row_timestamp) or row_timestamp >= window_start:
            filtered.append(row)
    return filtered


def _numeric(value: object, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def _count_unique_counterparties(rows: list[dict]) -> int:
    counterparties = set()
    for row in rows:
        receiver_id = row.get("receiver_id")
        if receiver_id not in (None, ""):
            counterparties.add(str(receiver_id))
    return len(counterparties)


_VELOCITY_SERVICE_INITIALIZED = False


class VelocityService:

    def __init__(self):
        global _VELOCITY_SERVICE_INITIALIZED
        if not _VELOCITY_SERVICE_INITIALIZED:
            initialize_runtime_store()
            _VELOCITY_SERVICE_INITIALIZED = True
        self.user_history = USER_RECENT_HISTORY
        self.user_state = USER_VELOCITY_STATE

    # ---------------------------------------------------------
    # MAIN UPDATE METHOD
    # ---------------------------------------------------------

    def update_after_transaction(self, txn: dict):
        sender_id = txn["sender_id"]
        trans_id = str(txn.get("trans_id") or txn.get("transaction_id") or txn.get("id") or "")
        amount = float(txn["amount"])
        timestamp = pd.to_datetime(txn["timestamp"], utc=True, errors="coerce")

        if pd.isna(timestamp):
            timestamp = pd.Timestamp.now(tz="UTC")

        user_history = list(self.user_history.get(sender_id, deque()))
        if trans_id and any(str(row.get("trans_id") or row.get("transaction_id") or row.get("id") or "") == trans_id for row in user_history):
            existing_state = self.user_state.get(sender_id)
            if existing_state:
                return existing_state

        candidate_history = user_history + [dict(txn)]
        recent_txns = _filter_last_24_hours(candidate_history, timestamp)

        rolling_24h_sum = sum(_numeric(row.get("amount")) for row in recent_txns)
        txn_count_24h = len(recent_txns)

        inbound_rows = [row for row in recent_txns if str(row.get("receiver_id") or "") == sender_id]
        outbound_sum = sum(_numeric(row.get("amount")) for row in recent_txns if str(row.get("sender_id") or "") == sender_id)
        inbound_sum = sum(_numeric(row.get("amount")) for row in inbound_rows)
        drain_ratio = outbound_sum / inbound_sum if inbound_sum > 0 else 0.0

        unique_counterparties = _count_unique_counterparties(recent_txns)

        round_amounts = [row for row in recent_txns if int(_numeric(row.get("amount"))) % 1000 == 0]
        round_number_ratio = (len(round_amounts) / txn_count_24h) if txn_count_24h > 0 else 0.0

        near_threshold_count = sum(
            1
            for row in recent_txns
            if 45000 <= _numeric(row.get("amount")) <= 49999
        )

        avg_holding_time_mins = 0.0
        holding_values = [
            _numeric(row.get("time_since_last_credit_ms")) / 60000
            for row in recent_txns
            if row.get("time_since_last_credit_ms") not in (None, "")
        ]
        if holding_values:
            avg_holding_time_mins = sum(holding_values) / len(holding_values)

        velocity_gradient = rolling_24h_sum / 24 if rolling_24h_sum else 0.0

        updated_row = {
            "user_id": sender_id,
            "rolling_24h_sum": round(rolling_24h_sum, 2),
            "txn_count_24h": txn_count_24h,
            "unique_counterparties_24h": unique_counterparties,
            "drain_ratio": round(drain_ratio, 4),
            "round_number_ratio": round(round_number_ratio, 4),
            "near_threshold_count": near_threshold_count,
            "avg_holding_time_mins": round(avg_holding_time_mins, 2),
            "velocity_gradient": round(velocity_gradient, 2),
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }

        self.user_state[sender_id] = updated_row
        update_user_velocity_state(sender_id, updated_row)
        return updated_row