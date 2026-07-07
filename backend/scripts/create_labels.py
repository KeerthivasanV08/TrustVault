# backend/scripts/create_labels.py

import pandas as pd
from pathlib import Path

# ---------------------------------------------------
# PATH CONFIG
# ---------------------------------------------------
BASE_DIR = Path(__file__).resolve().parents[2]

PROCESSED_DIR = BASE_DIR / "data" / "processed"
RAW_DIR = BASE_DIR / "data" / "raw"

# ---------------------------------------------------
# LABEL GENERATION ENGINE
# ---------------------------------------------------
def generate_realistic_labels():
    """
    Ground Truth Engine

    Builds high-fidelity AML labels by combining:

    - Identity Trust
    - Graph Topology
    - Transaction Behavior
    - SIM Integrity
    """

    print("🚀 Generating labels.csv ...")

    # ---------------------------------------------------
    # LOAD FEATURE FILES
    # ---------------------------------------------------
    try:

        user_f = pd.read_csv(
            PROCESSED_DIR / "user_features.csv"
        )

        graph_f = pd.read_csv(
            PROCESSED_DIR / "graph_features.csv"
        )

        txn_f = pd.read_csv(
            PROCESSED_DIR / "transaction_features.csv"
        )

        raw_txn = pd.read_csv(
            RAW_DIR / "transactions.csv"
        )

    except FileNotFoundError as e:

        print(f"❌ Missing required file: {e}")
        return

    # ---------------------------------------------------
    # VALIDATE REQUIRED COLUMNS
    # ---------------------------------------------------
    required_txn_cols = [
        "trans_id",
        "sender_id"
    ]

    for col in required_txn_cols:

        if col not in raw_txn.columns:

            print(
                f"❌ Missing column in transactions.csv: {col}"
            )

            return

    # ---------------------------------------------------
    # MERGE RAW TXN + TXN FEATURES
    # ---------------------------------------------------
    txn_user = raw_txn[[
        "trans_id",
        "sender_id"
    ]].merge(

        txn_f,

        on="trans_id",

        how="left"
    )

    # Rename sender_id → user_id
    txn_user.rename(columns={

        "sender_id": "user_id"

    }, inplace=True)

    # ---------------------------------------------------
    # USER-LEVEL AGGREGATION
    # CRITICAL:
    # One user = One label row
    # ---------------------------------------------------
    txn_agg = txn_user.groupby(
        "user_id",
        as_index=False
    ).agg({

        # Maximum wallet draining behavior
        "drain_ratio": "max",

        # Average anomaly deviation
        "amount_deviation": "mean",

        # Count of suspicious night activity
        "is_night_tx": "sum",

        # Average transaction execution speed
        "time_to_pay_ms": "mean",

        # SIM binding integrity ratio
        "is_sim_bound_at_tx": "mean"
    })

    # ---------------------------------------------------
    # MERGE ALL FEATURE LAYERS
    # ---------------------------------------------------
    merged = user_f.merge(

        graph_f,

        on="user_id",

        how="left"

    ).merge(

        txn_agg,

        on="user_id",

        how="left"
    )

    # ---------------------------------------------------
    # CLEAN NULLS
    # ---------------------------------------------------
    numeric_cols = merged.select_dtypes(
        include=["number"]
    ).columns

    merged[numeric_cols] = merged[
        numeric_cols
    ].fillna(0)

    # ---------------------------------------------------
    # LABEL LOGIC
    # ---------------------------------------------------

    # ---------------------------------------------------
    # 1. MULE ACCOUNT
    # Shared infra + drain behavior
    # ---------------------------------------------------
    merged["is_mule"] = (

        (
            merged["drain_ratio"] > 0.90
        )

        &

        (
            merged["mule_cluster_size"] >= 3
        )

        &

        (
            merged["graph_score"] >= 40
        )

    ).astype(int)

    # ---------------------------------------------------
    # 2. BOT / AUTOMATION
    # Low trust + super fast behavior
    # ---------------------------------------------------
    merged["is_bot"] = (

        (
            merged["identity_trust_score"] < 40
        )

        &

        (
            merged["time_to_pay_ms"] < 5000
        )

        &

        (
            merged["device_trust_score"] < 50
        )

    ).astype(int)

    # ---------------------------------------------------
    # 3. SYNTHETIC IDENTITY
    # VPN + geo mismatch
    # ---------------------------------------------------
    merged["is_synthetic"] = (

        (
            merged["city_mismatch_flag"] == 1
        )

        &

        (
            merged["vpn_flag"] == 1
        )

    ).astype(int)

    # ---------------------------------------------------
    # 4. ACCOUNT TAKEOVER (ATO)
    # SIM integrity violation
    # ---------------------------------------------------
    merged["is_ato"] = (

        merged["is_sim_bound_at_tx"] < 1.0

    ).astype(int)

    # ---------------------------------------------------
    # LABEL SOURCE
    # ---------------------------------------------------
    merged["label_source"] = (
        "multimodal_consensus_logic"
    )

    # ---------------------------------------------------
    # FINAL LABEL DATASET
    # ---------------------------------------------------
    labels = merged[[

        "user_id",

        "is_mule",

        "is_bot",

        "is_synthetic",

        "is_ato",

        "label_source"

    ]].copy()

    # ---------------------------------------------------
    # REMOVE DUPLICATES
    # SAFETY FIX
    # ---------------------------------------------------
    labels.drop_duplicates(

        subset=["user_id"],

        inplace=True
    )

    # ---------------------------------------------------
    # ENSURE OUTPUT DIRECTORY EXISTS
    # ---------------------------------------------------
    PROCESSED_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # ---------------------------------------------------
    # SAVE
    # ---------------------------------------------------
    output_path = (
        PROCESSED_DIR / "labels.csv"
    )

    labels.to_csv(
        output_path,
        index=False
    )

    # ---------------------------------------------------
    # SUMMARY
    # ---------------------------------------------------
    print("✅ labels.csv created successfully")
    print(f"📍 Location: {output_path}")

    print(
        f"📊 Total Users: {len(labels)}"
    )

    print(
        f"🚨 Mule Accounts: {labels['is_mule'].sum()}"
    )

    print(
        f"🤖 Bot Accounts: {labels['is_bot'].sum()}"
    )

    print(
        f"🔐 Synthetic Identities: "
        f"{labels['is_synthetic'].sum()}"
    )

    print(
        f"📱 Account Takeovers: "
        f"{labels['is_ato'].sum()}"
    )


# ---------------------------------------------------
# MAIN
# ---------------------------------------------------
if __name__ == "__main__":

    generate_realistic_labels()