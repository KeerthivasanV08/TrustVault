import pandas as pd
from datetime import datetime, timedelta

from app.core import storage_paths
from app.utils.file_utils import ensure_parent_dir, safe_to_csv

PROCESSED_DIR = storage_paths.PROCESSED_DIR
RAW_DIR = storage_paths.DATA_DIR / "raw"

VELOCITY_PATH = PROCESSED_DIR / "user_velocity.csv"
TRANSACTIONS_PATH = RAW_DIR / "transactions.csv"


class VelocityService:

    def __init__(self):

        ensure_parent_dir(VELOCITY_PATH)
        ensure_parent_dir(TRANSACTIONS_PATH)

        if VELOCITY_PATH.exists():
            self.velocity_df = pd.read_csv(VELOCITY_PATH)
        else:
            self.velocity_df = pd.DataFrame(columns=[
                "user_id",
                "rolling_24h_sum",
                "txn_count_24h",
                "drain_ratio",
                "unique_counterparties_24h",
                "round_number_ratio",
                "near_threshold_count",
                "avg_holding_time_mins",
                "velocity_gradient",
                "last_updated",
            ])
            safe_to_csv(self.velocity_df, VELOCITY_PATH)

        if TRANSACTIONS_PATH.exists():
            self.transactions_df = pd.read_csv(TRANSACTIONS_PATH, parse_dates=["timestamp"])
            if "timestamp" in self.transactions_df.columns:
                self.transactions_df["timestamp"] = pd.to_datetime(self.transactions_df["timestamp"], errors="coerce", utc=True)
        else:
            self.transactions_df = pd.DataFrame(columns=["trans_id", "sender_id", "receiver_id", "amount", "timestamp"]) 
            safe_to_csv(self.transactions_df, TRANSACTIONS_PATH)

    # ---------------------------------------------------------
    # MAIN UPDATE METHOD
    # ---------------------------------------------------------

    def update_after_transaction(self, txn: dict):

        sender_id = txn["sender_id"]

        amount = float(txn["amount"])

        timestamp = pd.to_datetime(txn["timestamp"], utc=True, errors="coerce")

        payment_mode = txn.get("payment_mode", "UPI")

        # -----------------------------------------------------
        # APPEND NEW TRANSACTION
        # -----------------------------------------------------

        new_txn = pd.DataFrame([txn])

        new_txn["timestamp"] = pd.to_datetime(
            new_txn["timestamp"],
            errors="coerce",
            utc=True
        )

        self.transactions_df = pd.concat(
            [self.transactions_df, new_txn],
            ignore_index=True
        )

        if "timestamp" in self.transactions_df.columns:
            self.transactions_df["timestamp"] = pd.to_datetime(
                self.transactions_df["timestamp"],
                errors="coerce",
                utc=True
            )

        if pd.isna(timestamp):
            timestamp = pd.Timestamp.now(tz="UTC")

        # -----------------------------------------------------
        # FILTER USER TXNS
        # -----------------------------------------------------

        user_txns = self.transactions_df[
            self.transactions_df["sender_id"] == sender_id
        ].copy()

        user_txns = user_txns[user_txns["timestamp"].notna()]

        # -----------------------------------------------------
        # ROLLING 24H WINDOW
        # -----------------------------------------------------

        window_start = timestamp - timedelta(hours=24)

        recent_txns = user_txns[
            user_txns["timestamp"] >= window_start
        ]

        rolling_24h_sum = recent_txns["amount"].sum()

        txn_count_24h = len(recent_txns)

        # -----------------------------------------------------
        # INBOUND / OUTBOUND
        # -----------------------------------------------------

        inbound_txns = self.transactions_df[
            self.transactions_df["receiver_id"] == sender_id
        ]

        outbound_sum = user_txns["amount"].sum()

        inbound_sum = inbound_txns["amount"].sum()

        drain_ratio = 0

        if inbound_sum > 0:
            drain_ratio = outbound_sum / inbound_sum

        # -----------------------------------------------------
        # UNIQUE COUNTERPARTIES
        # -----------------------------------------------------

        unique_counterparties = (
            recent_txns["receiver_id"]
            .nunique()
        )

        # -----------------------------------------------------
        # ROUND NUMBER RATIO
        # -----------------------------------------------------

        round_amounts = recent_txns[
            recent_txns["amount"] % 1000 == 0
        ]

        round_number_ratio = 0

        if txn_count_24h > 0:
            round_number_ratio = (
                len(round_amounts) / txn_count_24h
            )

        # -----------------------------------------------------
        # NEAR THRESHOLD COUNT
        # -----------------------------------------------------

        near_threshold_count = len(
            recent_txns[
                (recent_txns["amount"] >= 45000)
                &
                (recent_txns["amount"] <= 49999)
            ]
        )

        # -----------------------------------------------------
        # AVG HOLDING TIME
        # -----------------------------------------------------

        avg_holding_time_mins = 0

        if "time_since_last_credit_ms" in recent_txns.columns:

            avg_holding_time_mins = (
                recent_txns["time_since_last_credit_ms"]
                .mean() / 60000
            )

        # -----------------------------------------------------
        # VELOCITY GRADIENT
        # -----------------------------------------------------

        velocity_gradient = (
            rolling_24h_sum / 24
        )

        # -----------------------------------------------------
        # UPDATE ROW
        # -----------------------------------------------------

        existing = self.velocity_df[
            self.velocity_df["user_id"] == sender_id
        ]

        updated_row = {

            "user_id": sender_id,

            "rolling_24h_sum": round(
                rolling_24h_sum, 2
            ),

            "txn_count_24h": txn_count_24h,

            "drain_ratio": round(
                drain_ratio, 4
            ),

            "unique_counterparties_24h":
                unique_counterparties,

            "round_number_ratio": round(
                round_number_ratio, 4
            ),

            "near_threshold_count":
                near_threshold_count,

            "avg_holding_time_mins":
                round(avg_holding_time_mins, 2),

            "velocity_gradient":
                round(velocity_gradient, 2),

            "last_updated":
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
        }

        # -----------------------------------------------------
        # UPSERT LOGIC
        # -----------------------------------------------------

        if existing.empty:

            self.velocity_df = pd.concat(
                [
                    self.velocity_df,
                    pd.DataFrame([updated_row])
                ],
                ignore_index=True
            )

        else:

            idx = existing.index[0]

            for k, v in updated_row.items():
                self.velocity_df.at[idx, k] = v

        # -----------------------------------------------------
        # SAVE FILES
        # -----------------------------------------------------

        self.velocity_df.to_csv(
            VELOCITY_PATH,
            index=False
        )

        self.transactions_df.to_csv(
            TRANSACTIONS_PATH,
            index=False
        )

        return updated_row