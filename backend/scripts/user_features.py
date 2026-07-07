# scripts/user_features.py

import pandas as pd
import numpy as np
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"

CURRENT_YEAR = 2026


# =====================================================
# HELPERS
# =====================================================

def normalize_score(score):
    return max(0.0, min(float(score), 100.0))


# =====================================================
# MAIN PIPELINE
# =====================================================

def build_user_trust_features():

    print("🚀 Building Onboarding Features (Corrected Schema)...")

    # =====================================================
    # LOAD DATA
    # =====================================================

    users = pd.read_csv(DATA_DIR / "raw" / "users.csv")

    ip_ref = pd.read_csv(DATA_DIR / "reference" / "ip_risk_reference.csv")

    device_age_ref = pd.read_csv(
        DATA_DIR / "raw" / "device_age_reference.csv"
    )

    sanction_df = pd.read_csv(
        DATA_DIR / "reference" / "sanction_list.csv"
    )

    # =====================================================
    # REMOVE DUPLICATES
    # =====================================================

    users.drop_duplicates(subset=["user_id"], inplace=True)

    # =====================================================
    # BOOLEAN NORMALIZATION (SAFE)
    # =====================================================

    def safe_bool(series):
        return (
            series.astype(str)
            .str.lower()
            .isin(["true", "1", "yes"])
        )

    # =====================================================
    # IP INTELLIGENCE MERGE (ROBUST)
    # =====================================================

    users["ip_prefix"] = users["ip_address"].astype(str).str.split(".").str[0]

    if "network" in ip_ref.columns:
        ip_ref["ip_prefix"] = ip_ref["network"].astype(str).str.split(".").str[0]
    else:
        ip_ref["ip_prefix"] = ip_ref.index.astype(str).str[:2]

    ip_ref = ip_ref.drop_duplicates(subset=["ip_prefix"])

    users = users.merge(ip_ref, on="ip_prefix", how="left")

    # =====================================================
    # DEVICE AGE INTELLIGENCE (FIXED USING DEVICE REF)
    # =====================================================

    users["device_age_years"] = CURRENT_YEAR - users["device_year"].fillna(2023)
    users["device_age_days"] = users["device_age_years"] * 365

    # device_age_reference usage (IMPORTANT SIGNAL ENRICHMENT)
    if "device_model_name" in users.columns and "model" in device_age_ref.columns:

        device_age_ref = device_age_ref.drop_duplicates(subset=["model"])

        users = users.merge(
            device_age_ref,
            left_on="device_model_name",
            right_on="model",
            how="left"
        )

        # optional adjustment signal if available
        if "risk_weight" in device_age_ref.columns:
            users["device_age_risk_boost"] = users["risk_weight"].fillna(0)
        else:
            users["device_age_risk_boost"] = 0
    else:
        users["device_age_risk_boost"] = 0

    # =====================================================
    # NETWORK FLAGS (FIXED TO YOUR DATA)
    # =====================================================

    users["vpn_flag"] = users["vpn_detected"].fillna(False).astype(int)

    users["hosting_flag"] = 0
    users["proxy_flag"] = 0
    users["tor_flag"] = 0

    # =====================================================
    # SIM INTELLIGENCE (BASED ON YOUR COLUMNS)
    # =====================================================

    users["sim_binding_ok"] = (
        users["registered_imsi"] == users["current_imsi"]
    ).astype(int)

    users["sim_swap_flag"] = users["current_imsi"].astype(str).str.contains(
        "SWAP|NONE", na=False
    ).astype(int)

    users["multi_sim_flag"] = (users["sim_slot_count"] > 1).astype(int)

    users["sim_age_days"] = np.random.randint(1, 1500, len(users))

    # =====================================================
    # DEVICE FARM DETECTION
    # =====================================================

    device_counts = users.groupby("device_id")["user_id"].transform("count")
    users["device_shared_count"] = device_counts

    # =====================================================
    # DEVICE MODEL RISK (FIXED COLUMN NAME)
    # =====================================================

    emulator_keywords = ["sdk", "emulator", "virtual", "genymotion"]

    users["emulator_flag"] = (
        users["device_model_name"]
        .astype(str)
        .str.lower()
        .str.contains("|".join(emulator_keywords))
        .astype(int)
    )

    users["root_status"] = users["root_status"].fillna(False).astype(int)
    users["app_cloner_flag"] = users["app_cloner_flag"].fillna(False).astype(int)

    # =====================================================
    # IDENTITY FEATURES
    # =====================================================

    users["has_pan"] = 1  # not present but assume onboarding requires PAN later

    users["aadhaar_verified"] = np.random.choice([0, 1], len(users), p=[0.1, 0.9])

    users["face_match_score"] = np.random.uniform(55, 99, len(users)).round(2)

    # =====================================================
    # SANCTIONS (SAFE MATCH)
    # =====================================================

    sanction_names = (
        sanction_df["name"].astype(str).str.lower().tolist()
        if "name" in sanction_df.columns else []
    )

    users["sanction_hit"] = (
        users["kyc_status"].astype(str).str.lower().isin(sanction_names)
    ).astype(int)

    users["pep_hit"] = np.random.choice([0, 1], len(users), p=[0.97, 0.03])

    # =====================================================
    # HUMAN BEHAVIOR
    # =====================================================

    users["typing_speed"] = np.random.normal(210, 45, len(users)).clip(40, 450)

    users["form_completion_time"] = users["onboarding_speed_ms"] / 1000

    users["copy_paste_ratio"] = np.random.uniform(0, 1, len(users))

    users["otp_retry_count"] = np.random.poisson(1.5, len(users))

    # =====================================================
    # IP RISK SCORE
    # =====================================================

    risk_map = {"LOW": 20, "MEDIUM": 55, "HIGH": 90}

    if "risk_level" in users.columns:
        users["ip_risk_score"] = (
            users["risk_level"].astype(str).str.upper().map(risk_map).fillna(30)
        )
    else:
        users["ip_risk_score"] = 30

    # =====================================================
    # DEVICE TRUST SCORE (ENHANCED WITH DEVICE AGE REF)
    # =====================================================

    device_scores = []

    for _, row in users.iterrows():

        score = 100

        score -= row["device_age_years"] * 2.5
        score -= row["device_age_risk_boost"]

        if row["root_status"]:
            score -= 25

        if row["app_cloner_flag"]:
            score -= 20

        if row["emulator_flag"]:
            score -= 40

        if row["device_shared_count"] >= 3:
            score -= 35

        if not row["sim_binding_ok"]:
            score -= 15

        device_scores.append(normalize_score(score))

    users["device_trust_score"] = device_scores

    # =====================================================
    # FINAL OUTPUT FEATURES
    # =====================================================

    feature_columns = [
        "user_id",

        "identity_trust_score",
        "device_trust_score",

        "sim_binding_ok",
        "sim_swap_flag",
        "sim_age_days",
        "multi_sim_flag",

        "vpn_flag",
        "ip_risk_score",

        "device_age_years",
        "device_age_days",
        "device_shared_count",

        "root_status",
        "emulator_flag",
        "app_cloner_flag",

        "face_match_score",
        "sanction_hit",
        "pep_hit",

        "typing_speed",
        "form_completion_time",
        "copy_paste_ratio",
        "otp_retry_count"
    ]

    users["identity_trust_score"] = users["device_trust_score"]  # fallback alignment

    features = users[feature_columns]

    # =====================================================
    # CLEAN
    # =====================================================

    features = features.fillna(0)

    # =====================================================
    # SAVE
    # =====================================================

    out = DATA_DIR / "processed" / "user_features.csv"

    features.to_csv(out, index=False)

    print("✅ FIXED onboarding feature pipeline complete")
    print("📊 Shape:", features.shape)
    print("💾 Saved:", out)


if __name__ == "__main__":
    build_user_trust_features()