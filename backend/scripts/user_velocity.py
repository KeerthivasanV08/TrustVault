import pandas as pd
from pathlib import Path

from app.core import storage_paths

BASE_DIR = Path(__file__).resolve().parents[2]
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

def build_user_velocity():
    print("⏳ Calculating Time-Bound Behavioral Velocity...")
    txns = pd.read_csv(RAW_DIR / "transactions.csv")
    txns["timestamp"] = pd.to_datetime(txns["timestamp"])
    
    # 1. Define 'Current Time' for the simulation
    # In production, this is 'now'. In a lab, it's the latest txn in the data.
    current_time = txns["timestamp"].max()

    # 2. Filter data for specific windows
    last_24h = txns[txns["timestamp"] >= (current_time - pd.Timedelta(days=1))]
    last_7d = txns[txns["timestamp"] >= (current_time - pd.Timedelta(days=7))]

    # 3. Calculate 24h Metrics
    v24 = last_24h.groupby("sender_id").agg(
        tx_count_24h=("trans_id", "count")
    ).reset_index()

    # 4. Calculate 7d Metrics
    v7 = last_7d.groupby("sender_id").agg(
        avg_tx_amount_7d=("amount", "mean"),
        unique_receivers_7d=("receiver_id", "nunique")
    ).reset_index()

    # 5. Get Last Transaction Time for all users
    v_last = txns.groupby("sender_id").agg(
        last_tx_timestamp=("timestamp", "max")
    ).reset_index()

    # 6. Merge all windows into one Master Velocity File
    # Start with all users who have ever transacted
    velocity = v_last.merge(v24, on="sender_id", how="left")
    velocity = velocity.merge(v7, on="sender_id", how="left")

    # 7. Final Polish
    velocity.rename(columns={"sender_id": "user_id"}, inplace=True)
    velocity.fillna(0, inplace=True) # If no tx in window, count is 0
    
    # Add a derived feature: Days since last activity
    velocity["days_since_last_tx"] = (current_time - velocity["last_tx_timestamp"]).dt.days

    velocity.to_csv(storage_paths.TRAINING_VELOCITY_PATH, index=False)
    print(f"✅ training/user_velocity.csv created. Reference Time: {current_time}")

if __name__ == "__main__":
    build_user_velocity()