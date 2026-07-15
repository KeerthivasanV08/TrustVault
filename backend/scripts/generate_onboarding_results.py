# scripts/generate_onboarding_results.py

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import uuid

from app.core import storage_paths

# ---------------------------------------------------
# PATH CONFIG
# ---------------------------------------------------
BASE_DIR = Path(__file__).resolve().parents[2]

RAW_DIR = BASE_DIR / "data" / "raw"
REF_DIR = BASE_DIR / "data" / "reference"
PROCESSED_DIR = BASE_DIR / "data" / "processed"

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------
# MAIN ENGINE
# ---------------------------------------------------

def generate_onboarding_results():

    print("🚀 Generating account_risk_snapshot.csv ...")

    # ---------------------------------------------------
    # LOAD DATASETS
    # ---------------------------------------------------

    try:

        user_f = pd.read_csv(PROCESSED_DIR / "user_features.csv")
        graph_f = pd.read_csv(storage_paths.TRAINING_GRAPH_FEATURES_PATH)
        labels = pd.read_csv(PROCESSED_DIR / "labels.csv")

        users_raw = pd.read_csv(RAW_DIR / "users.csv")

        ip_risk = pd.read_csv(REF_DIR / "ip_risk_reference.csv")

    except FileNotFoundError as e:
        print(f"❌ Missing required file: {e}")
        return

    # ---------------------------------------------------
    # REMOVE DUPLICATES
    # ---------------------------------------------------

    user_f = user_f.drop_duplicates(subset=["user_id"])
    graph_f = graph_f.drop_duplicates(subset=["user_id"])
    labels = labels.drop_duplicates(subset=["user_id"])
    users_raw = users_raw.drop_duplicates(subset=["user_id"])

    # ---------------------------------------------------
    # MERGE FEATURE LAYERS
    # ---------------------------------------------------

    df = (
        users_raw
        .merge(user_f, on="user_id", how="left")
        .merge(graph_f, on="user_id", how="left")
        .merge(labels, on="user_id", how="left")
    )

    df.fillna(0, inplace=True)

    # ---------------------------------------------------
    # UNIQUE ONBOARDING SESSION ID
    # ---------------------------------------------------

    df["onboarding_id"] = [
        f"ONB_{uuid.uuid4().hex[:10].upper()}"
        for _ in range(len(df))
    ]

    # ---------------------------------------------------
    # STANDARDIZED FLAGS
    # ---------------------------------------------------

    def col_or_default(column_name, default_value=0):
        if column_name in df.columns:
            return df[column_name]

        return pd.Series(default_value, index=df.index)

    df["vpn_hosting_flag"] = (
        col_or_default("vpn_flag").astype(int) |
        col_or_default("hosting_flag").astype(int)
    )

    df["hardware_drift_flag"] = (
        col_or_default("device_drift_flag").astype(int)
    )

    df["device_reuse_count"] = (
        col_or_default("mule_cluster_size")
    )

    # ---------------------------------------------------
    # SIM BINDING STATUS
    # ---------------------------------------------------

    def sim_binding_logic(row):

        if row.get("sim_swap_flag", 0) == 1:
            return "MISMATCH"

        return "VERIFIED"

    df["sim_binding_status"] = df.apply(sim_binding_logic, axis=1)

    # ---------------------------------------------------
    # SANCTION MATCH
    # ---------------------------------------------------

    df["sanction_match"] = 0

    # ---------------------------------------------------
    # SYNTHETIC IDENTITY PROBABILITY
    # ---------------------------------------------------

    synthetic_prob = (
        (
            col_or_default("vpn_hosting_flag") * 0.30 +
            col_or_default("hardware_drift_flag") * 0.30 +
            (col_or_default("device_reuse_count") >= 3).astype(int) * 0.20 +
            col_or_default("sim_swap_flag") * 0.20
        )
        * 100
    )

    df["synthetic_identity_probability"] = (
        synthetic_prob.clip(0, 100).round(2)
    )

    # ---------------------------------------------------
    # BEHAVIORAL CONFIDENCE
    # ---------------------------------------------------

    df["behavioral_confidence"] = (
        100 -
        df["synthetic_identity_probability"]
    ).clip(0, 100).round(2)

    # ---------------------------------------------------
    # IDENTITY TRUST SCORE
    # ---------------------------------------------------

    if "identity_trust_score" not in df.columns:
        df["identity_trust_score"] = 50

    # ---------------------------------------------------
    # BASE ML RISK
    # ---------------------------------------------------

    df["onboarding_ml_risk"] = (
        (
            (100 - df["identity_trust_score"]) * 0.50
        ) +
        (
            (100 - col_or_default("device_trust_score", 50)) * 0.30
        ) +
        (
            col_or_default("graph_score") * 0.20
        )
    ).clip(0, 100).round(2)

    # ---------------------------------------------------
    # HARD REGULATORY PENALTIES
    # ---------------------------------------------------

    df["final_risk_score"] = (
        df["onboarding_ml_risk"] +

        (df["vpn_hosting_flag"] * 15) +

        (df["hardware_drift_flag"] * 25) +

        (
            (df["device_reuse_count"] >= 3).astype(int) * 30
        ) +

        (
            (df["sim_binding_status"] == "MISMATCH").astype(int) * 35
        ) +

        (
            df["sanction_match"] * 100
        )
    ).clip(0, 100).round(2)

    # ---------------------------------------------------
    # RISK CLASSIFICATION
    # ---------------------------------------------------

    def classify_risk(score):

        if score >= 85:
            return "CRITICAL"

        elif score >= 70:
            return "HIGH"

        elif score >= 50:
            return "MEDIUM"

        return "LOW"

    df["risk_level"] = df["final_risk_score"].apply(classify_risk)

    # ---------------------------------------------------
    # REVIEW / BLOCK FLAGS
    # ---------------------------------------------------

    df["requires_review"] = (
        df["final_risk_score"] >= 70
    ).astype(int)

    df["requires_block"] = (
        df["final_risk_score"] >= 85
    ).astype(int)

    # ---------------------------------------------------
    # FINAL ONBOARDING DECISION
    # ---------------------------------------------------

    def onboarding_decision(row):

        if row["requires_block"] == 1:
            return "REJECT"

        elif row["requires_review"] == 1:
            return "REVIEW"

        return "APPROVE"

    df["decision"] = df.apply(
        onboarding_decision,
        axis=1
    )

    # ---------------------------------------------------
    # REVIEW PRIORITY
    # ---------------------------------------------------

    def review_priority(row):

        if row["decision"] == "REJECT":
            return "P1"

        elif row["decision"] == "REVIEW":
            return "P2"

        return "P3"

    df["review_priority"] = df.apply(
        review_priority,
        axis=1
    )

    # ---------------------------------------------------
    # COOLING PERIOD
    # ---------------------------------------------------

    df["cooling_period_active"] = (
        df["final_risk_score"] >= 50
    ).astype(int)

    # ---------------------------------------------------
    # CONTROL REASONS
    # ---------------------------------------------------

    def build_control_reason(row):

        reasons = []

        # VPN / Hosting
        if row["vpn_hosting_flag"] == 1:
            reasons.append("VPN_HOSTING_NODE")

        # SIM mismatch
        if row["sim_binding_status"] == "MISMATCH":
            reasons.append("SIM_BINDING_FAILURE")

        # Hardware drift
        if row["hardware_drift_flag"] == 1:
            reasons.append("HARDWARE_DRIFT_DETECTED")

        # Device reuse
        if row["device_reuse_count"] >= 3:
            reasons.append(
                f"MULE_HUB_DEVICE_REUSE_{int(row['device_reuse_count'])}"
            )

        # Synthetic identity
        if row["synthetic_identity_probability"] >= 70:
            reasons.append("HIGH_SYNTHETIC_IDENTITY_PROBABILITY")

        # Mule label
        if row.get("is_mule", 0) == 1:
            reasons.append("KNOWN_MULE_TOPOLOGY_PATTERN")

        if len(reasons) == 0:
            return "CLEAN_ONBOARDING"

        return " | ".join(reasons)

    df["control_reason"] = df.apply(
        build_control_reason,
        axis=1
    )

    # ---------------------------------------------------
    # TIMESTAMP
    # ---------------------------------------------------

    df["processed_at"] = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    # ---------------------------------------------------
    # OUTPUT COLUMNS
    # ---------------------------------------------------

    output_cols = [

        "onboarding_id",

        "user_id",

        "device_id",

        "ip_address",

        "identity_trust_score",

        "synthetic_identity_probability",

        "behavioral_confidence",

        "hardware_drift_flag",

        "vpn_hosting_flag",

        "sim_binding_status",

        "device_reuse_count",

        "sanction_match",

        "onboarding_ml_risk",

        "final_risk_score",

        "decision",

        "risk_level",

        "requires_review",

        "requires_block",

        "cooling_period_active",

        "control_reason",

        "review_priority",

        "processed_at"
    ]

    # ---------------------------------------------------
    # SAFE COLUMN FILTER
    # ---------------------------------------------------

    existing_cols = [
        col for col in output_cols
        if col in df.columns
    ]

    output_df = df[existing_cols]

    # ---------------------------------------------------
    # SAVE OUTPUT
    # ---------------------------------------------------

    output_path = storage_paths.ONBOARDING_RISK_SNAPSHOT_PATH

    output_df.to_csv(
        output_path,
        index=False
    )

    # ---------------------------------------------------
    # STATS
    # ---------------------------------------------------

    print("\n✅ account_risk_snapshot.csv generated successfully")

    print("\n📊 Decision Distribution:")
    print(output_df["decision"].value_counts())

    print("\n📊 Risk Levels:")
    print(output_df["risk_level"].value_counts())

    print(f"\n📁 Saved To: {output_path}")

# ---------------------------------------------------
# ENTRYPOINT
# ---------------------------------------------------

if __name__ == "__main__":
    generate_onboarding_results()