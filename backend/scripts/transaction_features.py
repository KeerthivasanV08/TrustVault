# scripts/transaction_features.py

import pandas as pd
import numpy as np

from pathlib import Path

# ---------------------------------------------------
# PATH CONFIG
# ---------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[2]

DATA_DIR = BASE_DIR / "data"

RAW_DIR = DATA_DIR / "raw"

PROCESSED_DIR = DATA_DIR / "processed"


# ---------------------------------------------------
# HELPERS
# ---------------------------------------------------

def safe_divide(a, b, default=0.0):
    """
    Safe division helper
    """
    if isinstance(a, pd.Series) or isinstance(b, pd.Series):
        numerator = a if isinstance(a, pd.Series) else pd.Series(a, index=b.index)
        denominator = b if isinstance(b, pd.Series) else pd.Series(b, index=numerator.index)

        return numerator.div(denominator.replace(0, np.nan)).fillna(default)

    try:
        if b == 0 or pd.isna(b):
            return default

        return a / b
    except Exception:
        return default


def calculate_drain_ratio(row):
    """
    How aggressively balance is depleted
    """
    return round(
        safe_divide(
            row["amount"],
            row["sender_bal_before"],
            0.0
        ),
        4
    )


# ---------------------------------------------------
# MAIN FEATURE BUILDER
# ---------------------------------------------------

def build_txn_features():

    print("🚀 Building Enterprise transaction_features.csv ...")

    # ---------------------------------------------------
    # LOAD RAW TRANSACTIONS
    # ---------------------------------------------------

    txns = pd.read_csv(
        RAW_DIR / "transactions.csv"
    )

    txns["timestamp"] = pd.to_datetime(
        txns["timestamp"]
    )

    # ---------------------------------------------------
    # SORT FOR SEQUENCE INTELLIGENCE
    # ---------------------------------------------------

    txns = txns.sort_values(
        by=["sender_id", "timestamp"]
    ).reset_index(drop=True)

    # ---------------------------------------------------
    # BASIC FEATURES
    # ---------------------------------------------------

    # =============================
    # DRAIN RATIO
    # =============================

    txns["drain_ratio"] = (
        txns.apply(
            calculate_drain_ratio,
            axis=1
        )
    )

    # =============================
    # NIGHT TRANSACTION
    # =============================

    txns["is_night_tx"] = (
        txns["timestamp"]
        .dt.hour
        .apply(
            lambda h:
            1 if h < 6 or h >= 22 else 0
        )
    )

    # =============================
    # AMOUNT DEVIATION
    # =============================

    avg_amt = (
        txns.groupby("sender_id")["amount"]
        .transform("mean")
    )

    txns["amount_deviation"] = (
        txns["amount"]
        / avg_amt.replace(0, np.nan)
    ).fillna(1.0)

    # ---------------------------------------------------
    # SEQUENCE INTELLIGENCE
    # ---------------------------------------------------

    # Previous transaction timestamp

    txns["prev_txn_ts"] = (
        txns.groupby("sender_id")["timestamp"]
        .shift(1)
    )

    # Time delta

    txns["time_to_pay_ms"] = (
        (
            txns["timestamp"]
            - txns["prev_txn_ts"]
        )
        .dt.total_seconds()
        .fillna(999999)
        * 1000
    ).astype(int)

    # Rapid relay behavior

    txns["rapid_outbound_after_inbound"] = (
        txns["time_to_pay_ms"] < 120000
    ).astype(int)

    # Forwarding delay in mins

    txns["forwarding_delay_mins"] = (
        txns["time_to_pay_ms"]
        / 60000
    ).round(2)

    # ---------------------------------------------------
    # STRUCTURING INTELLIGENCE
    # ---------------------------------------------------

    # Round amount

    txns["is_round_amount"] = (
        (txns["amount"] % 1000 == 0)
    ).astype(int)

    # Distance from PAN threshold

    txns["distance_from_50k_threshold"] = (
        50000 - txns["amount"]
    ).clip(lower=0)

    # Distance from UPI threshold

    txns["distance_from_1L_threshold"] = (
        100000 - txns["amount"]
    ).clip(lower=0)

    # Near-threshold behavior

    txns["near_threshold_flag"] = (
        (
            txns["amount"] >= 45000
        ) &
        (
            txns["amount"] < 50000
        )
    ).astype(int)

    # ---------------------------------------------------
    # FRAGMENTATION / STRUCTURING SCORE
    # ---------------------------------------------------

    fragmentation = (
        txns.groupby("sender_id")["near_threshold_flag"]
        .transform("mean")
    )

    txns["fragmentation_score"] = (
        fragmentation
        .fillna(0)
        .round(4)
    )

    # ---------------------------------------------------
    # COUNTERPARTY INTELLIGENCE
    # ---------------------------------------------------

    counterparty_diversity = (
        txns.groupby("sender_id")["receiver_id"]
        .transform("nunique")
    )

    txns["counterparty_diversity"] = (
        counterparty_diversity
    )

    # ---------------------------------------------------
    # VELOCITY FEATURES
    # ---------------------------------------------------

    # Transactions per sender in rolling order

    txns["txn_sequence"] = (
        txns.groupby("sender_id")
        .cumcount()
        + 1
    )

    # Hourly velocity approximation

    txns["txn_velocity_1h"] = (
        txns.groupby("sender_id")["trans_id"]
        .transform("count")
    )

    # ---------------------------------------------------
    # BALANCE DEPLETION
    # ---------------------------------------------------

    txns["balance_after_txn"] = (
        txns["sender_bal_before"]
        - txns["amount"]
    )

    txns["balance_depletion_speed"] = (
        safe_divide(
            txns["amount"],
            txns["sender_bal_before"],
            0
        )
    ).round(4)

    # ---------------------------------------------------
    # EMPTY ACCOUNT / MULE THROUGHOUT
    # ---------------------------------------------------

    txns["empty_account_flag"] = (
        txns["balance_after_txn"] < 500
    ).astype(int)

    # ---------------------------------------------------
    # SIM BINDING AT TRANSACTION
    # ---------------------------------------------------

    if "is_sim_bound" in txns.columns:

        txns["is_sim_bound_at_tx"] = (
            txns["is_sim_bound"]
            .astype(bool)
        )

    else:

        txns["is_sim_bound_at_tx"] = True

    # ---------------------------------------------------
    # FINAL FEATURE EXPORT
    # ---------------------------------------------------

    feature_columns = [

        # IDs
        "trans_id",
        "sender_id",
        "receiver_id",

        # Core txn
        "amount",

        # Behavioral
        "drain_ratio",
        "amount_deviation",
        "is_night_tx",

        # Sequence intelligence
        "time_to_pay_ms",
        "rapid_outbound_after_inbound",
        "forwarding_delay_mins",

        # Structuring
        "is_round_amount",
        "distance_from_50k_threshold",
        "distance_from_1L_threshold",
        "near_threshold_flag",
        "fragmentation_score",

        # Counterparty
        "counterparty_diversity",

        # Velocity
        "txn_velocity_1h",

        # Balance / throughput
        "balance_depletion_speed",
        "empty_account_flag",

        # SIM integrity
        "is_sim_bound_at_tx"
    ]

    features = txns[feature_columns]

    # ---------------------------------------------------
    # EXPORT
    # ---------------------------------------------------

    output_path = (
        PROCESSED_DIR
        / "transaction_features.csv"
    )

    features.to_csv(
        output_path,
        index=False
    )

    # ---------------------------------------------------
    # SUMMARY
    # ---------------------------------------------------

    print("\n✅ transaction_features.csv created")

    print(f"📍 Location: {output_path}")

    print("\n📊 Feature Summary:")

    print(
        f"""
        Total Transactions: {len(features)}

        Rapid Relay Cases:
        {features['rapid_outbound_after_inbound'].sum()}

        Near Threshold Cases:
        {features['near_threshold_flag'].sum()}

        Empty Account Cases:
        {features['empty_account_flag'].sum()}
        """
    )


# ---------------------------------------------------
# RUN
# ---------------------------------------------------

if __name__ == "__main__":

    build_txn_features()