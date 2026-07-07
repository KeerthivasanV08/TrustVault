# training/transaction/evaluate_behavioral_model.py

import json
import joblib
import pandas as pd
import numpy as np
import sys

from pathlib import Path

from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    roc_auc_score
)

ROOT_DIR = Path(__file__).resolve().parents[3]
BACKEND_DIR = Path(__file__).resolve().parents[2]

# -----------------------------------
# PACKAGE FIX
# -----------------------------------

if __package__ in (None, ""):
    if str(BACKEND_DIR) not in sys.path:

        sys.path.insert(
            0,
            str(BACKEND_DIR)
        )

from app.core.feature_schema import BEHAVIOR_NUMERIC_FEATURES
from app.core.feature_validator import validate_behavior_features

# -----------------------------------
# IMPORT PIPELINE
# -----------------------------------

from training.transaction.behavioral_feature_pipeline import (
    build_behavioral_features
)

# -----------------------------------
# PATHS
# -----------------------------------

MODEL_DIR = BACKEND_DIR / "app" / "models" / "transaction"

DATASET_PATH = ROOT_DIR / "data" / "processed" / "final_dataset.csv"

# -----------------------------------
# MAIN EVALUATION
# -----------------------------------


def evaluate():

    print(
        "\n🚀 Starting Behavioral Model Evaluation..."
    )

    # -----------------------------------
    # LOAD DATA
    # -----------------------------------

    df = pd.read_csv(
        DATASET_PATH
    )

    print(
        f"✅ Dataset Loaded: {len(df)} rows"
    )

    # -----------------------------------
    # BUILD FEATURES
    # -----------------------------------

    X, y = build_behavioral_features(df)

    print(
        f"✅ Features Prepared: {X.shape[1]} features"
    )

    # -----------------------------------
    # LOAD MODEL
    # -----------------------------------

    model = joblib.load(
        MODEL_DIR
        / "behavioral_lightgbm.pkl"
    )

    scaler = joblib.load(
        MODEL_DIR
        / "behavioral_scaler.pkl"
    )

    # -----------------------------------
    # LOAD FEATURE SCHEMA
    # -----------------------------------

    with open(
        MODEL_DIR
        / "behavioral_features.json",
        "r"
    ) as f:

        feature_schema = json.load(f)

    numerical_features = [column for column in BEHAVIOR_NUMERIC_FEATURES if column in X.columns]

    # -----------------------------------
    # SCALE NUMERICAL FEATURES ONLY
    # -----------------------------------

    X = validate_behavior_features(X)
    X[numerical_features] = scaler.transform(X[numerical_features])

    print(
        "✅ Numerical Features Scaled"
    )

    # -----------------------------------
    # PREDICTIONS
    # -----------------------------------

    y_prob = model.predict_proba(X)[:, 1]

    y_pred = (
        y_prob >= 0.70
    ).astype(int)

    # -----------------------------------
    # METRICS
    # -----------------------------------

    print("\n========== ROC AUC ==========")

    print(
        roc_auc_score(
            y,
            y_prob
        )
    )

    print(
        "\n========== CLASSIFICATION REPORT =========="
    )

    print(
        classification_report(
            y,
            y_pred
        )
    )

    print(
        "\n========== CONFUSION MATRIX =========="
    )

    print(
        confusion_matrix(
            y,
            y_pred
        )
    )

    # -----------------------------------
    # TOP RISK SCORES
    # -----------------------------------

    risk_df = pd.DataFrame({

        "fraud_probability": y_prob,

        "predicted_label": y_pred
    })

    print(
        "\n========== TOP HIGH-RISK SCORES =========="
    )

    print(
        risk_df
        .sort_values(
            by="fraud_probability",
            ascending=False
        )
        .head(10)
    )

    print(
        "\n🎯 BEHAVIORAL MODEL EVALUATION COMPLETED"
    )


# -----------------------------------
# ENTRYPOINT
# -----------------------------------

if __name__ == "__main__":

    evaluate()