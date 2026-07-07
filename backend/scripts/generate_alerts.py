# backend/scripts/generate_alerts.py
import pandas as pd
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parents[2]
PROCESSED_DIR = BASE_DIR / "data" / "processed"

def generate_alerts():
    print("🚀 Generating Operational Alert Queue...")

    # 1. Load Decisions and Labels
    onboarding = pd.read_csv(PROCESSED_DIR / "onboarding_results.csv")
    labels = pd.read_csv(PROCESSED_DIR / "labels.csv")

    # 2. Merge ML results with confirmed archetype labels
    df = onboarding.merge(labels, on="user_id", how="left").fillna(0)

    # 3. Enhanced Alert Logic
    # Trigger an alert if: ML says high risk OR Graph/Labels confirm a Mule/Bot
    alerts = df[
        (df["final_risk_score"] >= 70) | 
        (df["is_mule"] == 1) | 
        (df["is_bot"] == 1)
    ].copy()

    if alerts.empty:
        print("ℹ️ No risky entities found. No alerts generated.")
        return

    # 4. Professional Alert Metadata
    alerts["alert_id"] = [f"ALT-{datetime.now().strftime('%Y%m')}-{1000+i}" for i in range(len(alerts))]
    alerts["entity_type"] = "USER"
    alerts["status"] = "New"
    alerts["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 5. Smart Priority Logic
    def assign_priority(row):
        # Immediate P1 for confirmed archetypes regardless of score
        if row["is_mule"] == 1 or row["is_bot"] == 1 or row["final_risk_score"] >= 90:
            return "P1 (Critical)"
        if row["final_risk_score"] >= 75:
            return "P2 (High)"
        return "P3 (Medium)"

    alerts["alert_priority"] = alerts.apply(assign_priority, axis=1)

    # 6. Final Data Selection
    # We include 'control_reason' so the UI can explain the alert
    output = alerts[[
        "alert_id", "user_id", "entity_type", "final_risk_score", 
        "alert_priority", "control_reason", "status", "created_at"
    ]].rename(columns={"final_risk_score": "risk_score"})

    # 7. Save to Processed
    output_path = PROCESSED_DIR / "alerts.csv"
    output.to_csv(output_path, index=False)

    print(f"✅ alerts.csv created. Total Alerts: {len(output)}")
    print(f"🚨 P1 Alerts: {len(output[output['alert_priority'].str.contains('P1')])}")

if __name__ == "__main__":
    generate_alerts()