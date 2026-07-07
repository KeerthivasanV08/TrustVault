# backend/scripts/build_final_dataset.py

import pandas as pd

from pathlib import Path


# =====================================================
# PATH CONFIG
# =====================================================

BASE_DIR = Path(__file__).resolve().parents[2]

RAW_DIR = BASE_DIR / "data" / "raw"

PROCESSED_DIR = BASE_DIR / "data" / "processed"


# =====================================================
# BUILD FINAL DATASET
# =====================================================

def build_final_dataset():

    print("🚀 Building Enterprise AML Dataset...")

    # =====================================================
    # LOAD DATASETS
    # =====================================================

    tx_raw = pd.read_csv(
        RAW_DIR / "transactions.csv"
    )

    txn_features = pd.read_csv(
        PROCESSED_DIR / "transaction_features.csv"
    )

    user_features = pd.read_csv(
        PROCESSED_DIR / "user_features.csv"
    )

    graph_features = pd.read_csv(
        PROCESSED_DIR / "graph_features.csv"
    )

    velocity_features = pd.read_csv(
        PROCESSED_DIR / "user_velocity.csv"
    )

    onboarding_results = pd.read_csv(
        PROCESSED_DIR / "onboarding_results.csv"
    )

    labels = pd.read_csv(
        PROCESSED_DIR / "labels.csv"
    )

    # =====================================================
    # MERGE TRANSACTION FEATURES
    # =====================================================

    print("📦 Merging Transaction Features...")

    cols_to_use = (
        txn_features.columns.difference(
            tx_raw.columns
        ).tolist()
        + ["trans_id"]
    )

    df = tx_raw.merge(

        txn_features[cols_to_use],

        on="trans_id",

        how="left"

    )

    # =====================================================
    # BUILD USER INTELLIGENCE LAYER
    # =====================================================

    print("🧠 Building User Intelligence Layer...")

    sender_intel = user_features.merge(

        graph_features,

        on="user_id",

        how="left"

    )

    sender_intel = sender_intel.merge(

        velocity_features,

        on="user_id",

        how="left"

    )

    # =====================================================
    # MERGE ONBOARDING INTELLIGENCE
    # =====================================================

    print("🛡️ Merging Onboarding Intelligence...")

    onboarding_cols = [

        "user_id",
        "final_risk_score",
        "risk_level",
        "cooling_period_active",
        "requires_review",
        "requires_block"

    ]

    sender_intel = sender_intel.merge(

        onboarding_results[onboarding_cols],

        on="user_id",

        how="left"

    )

    # =====================================================
    # MERGE LABELS
    # =====================================================

    print("🚨 Merging Fraud Labels...")

    sender_intel = sender_intel.merge(

        labels,

        on="user_id",

        how="left"

    )

    # =====================================================
    # MERGE INTO TRANSACTION DATASET
    # =====================================================

    print("🔗 Creating Final Transaction Intelligence Table...")

    df = df.merge(

        sender_intel,

        left_on="sender_id",

        right_on="user_id",

        how="left"

    )

    # Remove duplicate user_id after merge
    df.drop(

        columns=["user_id"],

        inplace=True,

        errors="ignore"

    )

    # =====================================================
    # CREATE MASTER FRAUD LABEL
    # =====================================================

    print("🎯 Creating Master Fraud Label...")

    df["is_fraud"] = (

        (
            df["is_mule"].fillna(0)
            +
            df["is_bot"].fillna(0)
            +
            df["is_synthetic"].fillna(0)
        ) > 0

    ).astype(int)

    # =====================================================
    # DATA CLEANING
    # =====================================================

    print("🧹 Cleaning Dataset...")

    # ---------------------------------------------
    # NUMERIC NULLS
    # ---------------------------------------------

    numeric_cols = df.select_dtypes(
        include=["number"]
    ).columns

    df[numeric_cols] = df[
        numeric_cols
    ].fillna(0)

    # ---------------------------------------------
    # OBJECT NULLS
    # ---------------------------------------------

    object_cols = df.select_dtypes(
        include=["object"]
    ).columns

    df[object_cols] = df[
        object_cols
    ].fillna("UNKNOWN")

    # =====================================================
    # REMOVE DUPLICATES
    # =====================================================

    print("🧬 Removing Duplicate Transactions...")

    before_dedup = len(df)

    df.drop_duplicates(

        subset=["trans_id"],

        inplace=True

    )

    after_dedup = len(df)

    print(
        f"✅ Removed {before_dedup - after_dedup} duplicate rows"
    )

    # =====================================================
    # BOOLEAN CONVERSION
    # =====================================================

    print("🔄 Converting Boolean Features...")

    bool_cols = df.select_dtypes(
        include=["bool"]
    ).columns

    df[bool_cols] = df[
        bool_cols
    ].astype(int)

    # =====================================================
    # FEATURE ENGINEERING
    # =====================================================

    print("⚙️ Engineering AML Features...")

    # ---------------------------------------------
    # ACCOUNT AGE
    # ---------------------------------------------

    df["account_age_days"] = (

        df["device_age_years"] * 365

    )

    # ---------------------------------------------
    # HIGH VALUE TRANSACTION
    # ---------------------------------------------

    df["high_value_txn"] = (

        df["amount"] >= 50000

    ).astype(int)

    # ---------------------------------------------
    # RAPID MOVEMENT
    # ---------------------------------------------

    df["rapid_movement"] = (

        df["forwarding_delay_mins"] < 5

    ).astype(int)

    # ---------------------------------------------
    # PASS THROUGH RATIO
    # ---------------------------------------------

    df["pass_through_ratio"] = (

        df["drain_ratio"]
        *
        df["balance_depletion_speed"]

    )

    # ---------------------------------------------
    # STRUCTURING FLAG
    # ---------------------------------------------

    df["structuring_pattern"] = (

        (
            df["amount"] >= 45000
        )
        &
        (
            df["amount"] < 50000
        )

    ).astype(int)

    # ---------------------------------------------
    # NIGHT HIGH VALUE FLAG
    # ---------------------------------------------

    df["night_high_value_txn"] = (

        (
            df["is_night_tx"] == 1
        )
        &
        (
            df["high_value_txn"] == 1
        )

    ).astype(int)

    # ---------------------------------------------
    # VELOCITY RISK SCORE
    # ---------------------------------------------

    df["velocity_risk_score"] = (

        (
            df["txn_velocity_1h"] * 0.4
        )
        +
        (
            df["tx_count_24h"] * 0.3
        )
        +
        (
            df["fragmentation_score"] * 0.3
        )

    )

    # ---------------------------------------------
    # NETWORK RISK COMPOSITE
    # ---------------------------------------------

    df["network_risk_score"] = (

        (
            df["graph_score"] * 0.5
        )
        +
        (
            df["known_fraud_connections"] * 0.3
        )
        +
        (
            df["mule_cluster_size"] * 0.2
        )

    )

    # =====================================================
    # REMOVE TARGET LEAKAGE
    # =====================================================

    print("🚫 Removing Label Leakage Columns...")

    leak_cols = [

        "is_mule",
        "is_bot",
        "is_synthetic",
        "is_ato"

    ]

    df.drop(

        columns=leak_cols,

        inplace=True,

        errors="ignore"

    )

    # =====================================================
    # FINAL VALIDATION
    # =====================================================

    print("🧪 Running Validation Checks...")

    if len(df) != len(df["trans_id"].unique()):

        print(
            "⚠️ Duplicate Transaction IDs Still Exist"
        )

    if "is_fraud" not in df.columns:

        raise ValueError(
            "❌ is_fraud label missing"
        )

    fraud_rate = round(

        df["is_fraud"].mean() * 100,

        2

    )

    print(f"🚨 Fraud Rate: {fraud_rate}%")

    # =====================================================
    # SAVE FULL DATASET
    # =====================================================

    full_output_path = (

        PROCESSED_DIR /
        "final_dataset.csv"

    )

    df.to_csv(

        full_output_path,

        index=False

    )

    print(
        f"💾 Saved Full Dataset → {full_output_path}"
    )

    # =====================================================
    # CREATE ML TRAINING DATASET
    # =====================================================

    print("🤖 Creating ML Training Dataset...")

    DROP_COLUMNS = [

        "trans_id",
        "sender_id",
        "receiver_id",
        "device_id",
        "timestamp",
        "location",
        "label_source"

    ]

    ml_df = df.drop(

        columns=DROP_COLUMNS,

        errors="ignore"

    )

    ml_output_path = (

        PROCESSED_DIR /
        "ml_training_dataset.csv"

    )

    ml_df.to_csv(

        ml_output_path,

        index=False

    )

    print(
        f"💾 Saved ML Dataset → {ml_output_path}"
    )

    # =====================================================
    # FINAL SUMMARY
    # =====================================================

    print("\n" + "=" * 60)

    print("✅ ENTERPRISE AML DATASET READY")

    print("=" * 60)

    print(f"📊 Full Dataset Shape: {df.shape}")

    print(f"🤖 ML Dataset Shape: {ml_df.shape}")

    print(f"🚨 Fraud Rate: {fraud_rate}%")

    print(f"📁 Saved Files:")
    print(f"   • {full_output_path.name}")
    print(f"   • {ml_output_path.name}")

    print("=" * 60)


# =====================================================
# ENTRYPOINT
# =====================================================

if __name__ == "__main__":

    build_final_dataset()