import pandas as pd

# Metadata that isn't a feature
DROP_COLUMNS = [
    "trans_id", "sender_id", "receiver_id", "device_id", 
    "timestamp", "label_source", "location", "last_tx_timestamp"
]

# CRITICAL: These are results of the transaction. Including them = 100% fake accuracy.
LEAKAGE_COLUMNS = [
    "final_risk_score", "risk_level", "cooling_period_active", 
    "requires_review", "requires_block"
]

TARGET_COLUMN = "is_fraud"

def build_behavioral_features(df):
    df = df.copy()
    
    # Check if target exists (for training) or not (for inference)
    y = df[TARGET_COLUMN] if TARGET_COLUMN in df.columns else None

    # Drop non-features and leakage
    to_drop = DROP_COLUMNS + LEAKAGE_COLUMNS + [TARGET_COLUMN]
    X = df.drop(columns=[c for c in to_drop if c in df.columns], errors="ignore")

    # Handle Categorical Data properly for LightGBM
    # LightGBM works better when categories are 'category' type rather than dummy variables
    categorical_cols = X.select_dtypes(include=["object"]).columns
    for col in categorical_cols:
        X[col] = X[col].astype("category")

    return X, y