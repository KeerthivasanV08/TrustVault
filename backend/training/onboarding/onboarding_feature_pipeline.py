# training/onboarding/onboarding_feature_pipeline.py

import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[3]
BACKEND_DIR = Path(__file__).resolve().parents[2]

DATA_DIR = ROOT_DIR / "data"
MODEL_DIR = BACKEND_DIR / "app" / "models" / "onboarding"

MODEL_DIR.mkdir(parents=True, exist_ok=True)


# =========================================================
# SAFE COLUMN DROPPER
# =========================================================
def safe_drop(df, cols):

    existing = [
        c for c in cols
        if c in df.columns
    ]

    return df.drop(columns=existing)


# =========================================================
# BOOLEAN NORMALIZATION
# =========================================================
def normalize_booleans(df):

    bool_cols = df.select_dtypes(
        include=["bool"]
    ).columns

    df[bool_cols] = df[
        bool_cols
    ].astype(int)

    return df


# =========================================================
# FEATURE ENGINEERING
# =========================================================
def create_engineered_features(df):

    # ---------------------------------------------
    # DEVICE RISK
    # ---------------------------------------------
    if "device_age_years" in df.columns:

        df["device_age_days"] = (
            df["device_age_years"] * 365
        )

        df["old_device_flag"] = (
            df["device_age_years"] > 5
        ).astype(int)

    # ---------------------------------------------
    # NETWORK RISK
    # ---------------------------------------------
    network_cols = [
        "vpn_flag",
        "hosting_flag",
        "proxy_flag",
        "tor_flag",
        "city_mismatch_flag"
    ]

    existing_network = [
        c for c in network_cols
        if c in df.columns
    ]

    if existing_network:

        df["network_risk_score"] = (
            df[existing_network]
            .sum(axis=1)
        )

    # ---------------------------------------------
    # SIM RISK
    # ---------------------------------------------
    sim_cols = [
        "sim_swap_flag",
        "multi_sim_flag"
    ]

    existing_sim = [
        c for c in sim_cols
        if c in df.columns
    ]

    if existing_sim:

        df["sim_risk_score"] = (
            df[existing_sim]
            .sum(axis=1)
        )

    # ---------------------------------------------
    # BEHAVIOR RISK
    # ---------------------------------------------
    if "copy_paste_ratio" in df.columns:

        df["high_copy_paste_flag"] = (
            df["copy_paste_ratio"] > 0.8
        ).astype(int)

    if "otp_retry_count" in df.columns:

        df["otp_abuse_flag"] = (
            df["otp_retry_count"] >= 3
        ).astype(int)

    if "form_completion_time" in df.columns:

        df["fast_form_submission"] = (
            df["form_completion_time"] < 15
        ).astype(int)

    return df


# =========================================================
# MAIN PIPELINE
# =========================================================
def prepare_onboarding_training_data():

    # =====================================================
    # LOAD DATASETS
    # =====================================================

    df_features = pd.read_csv(
        DATA_DIR
        / "processed"
        / "user_features.csv"
    )

    df_results = pd.read_csv(
        DATA_DIR
        / "processed"
        / "onboarding" / "account_risk_snapshot.csv"
    )

    df_labels = pd.read_csv(
        DATA_DIR
        / "processed"
        / "labels.csv"
    )

    print("✅ Datasets Loaded")

    # =====================================================
    # REMOVE DUPLICATES
    # =====================================================

    df_features.drop_duplicates(
        subset=["user_id"],
        inplace=True
    )

    df_results.drop_duplicates(
        subset=["user_id"],
        inplace=True
    )

    df_labels.drop_duplicates(
        subset=["user_id"],
        inplace=True
    )

    # =====================================================
    # SELECT SAFE META FEATURES
    # =====================================================

    allowed_meta_features = [

        "user_id",

        "identity_trust_score",

        "device_trust_score",

        "behavioral_confidence",

        "vpn_hosting_flag",

        "network_risk_score",

        "sim_risk_score"
    ]

    available_meta_features = [
        c for c in allowed_meta_features
        if c in df_results.columns
    ]

    df_results = df_results[
        available_meta_features
    ]

    # =====================================================
    # MERGE FEATURES + RESULTS
    # =====================================================

    df_master = pd.merge(
        df_features,
        df_results,
        on="user_id",
        how="left",
        suffixes=("", "_meta")
    )

    # =====================================================
    # MERGE LABELS
    # =====================================================

    df_master = pd.merge(
        df_master,
        df_labels,
        on="user_id",
        how="inner"
    )

    print("✅ DataFrames Merged")

    # =====================================================
    # CREATE TARGET
    # =====================================================

    fraud_columns = [

        "is_mule",

        "is_bot",

        "is_synthetic",

        "is_ato"
    ]

    existing_fraud_cols = [
        c for c in fraud_columns
        if c in df_master.columns
    ]

    df_master["target"] = (
        df_master[
            existing_fraud_cols
        ]
        .max(axis=1)
    )

    # =====================================================
    # FEATURE ENGINEERING
    # =====================================================

    df_master = create_engineered_features(
        df_master
    )

    # =====================================================
    # BOOLEAN NORMALIZATION
    # =====================================================

    df_master = normalize_booleans(
        df_master
    )

    # =====================================================
    # REMOVE LEAKAGE
    # =====================================================

    leakage_columns = [

        "user_id",

        "label_source",

        "target",

        "is_mule",

        "is_bot",

        "is_synthetic",

        "is_ato",

        "final_decision",

        "final_risk_score",

        "requires_block",

        "requires_review",

        "requires_edd",

        "officer_recommendation"
    ]

    X = safe_drop(
        df_master,
        leakage_columns
    )

    y = df_master["target"]

    # =====================================================
    # FILL NULLS
    # =====================================================

    X = X.fillna(0)

    # =====================================================
    # SAVE FEATURE LIST
    # =====================================================

    feature_list = list(X.columns)

    with open(
        MODEL_DIR / "onboarding_features.json",
        "w"
    ) as f:

        json.dump(
            feature_list,
            f,
            indent=4
        )

    print("✅ onboarding_features.json saved")

    # =====================================================
    # FINAL INFO
    # =====================================================

    print("\n========== TRAINING DATA ==========")
    print(f"Rows       : {len(X)}")
    print(f"Features   : {len(X.columns)}")
    print(f"Fraud Rate : {round(y.mean()*100, 2)}%")

    return X, y


if __name__ == "__main__":

    X, y = prepare_onboarding_training_data()

    print("\n✅ Onboarding Feature Pipeline Completed")