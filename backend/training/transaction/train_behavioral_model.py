import json
import joblib
import lightgbm as lgb
import pandas as pd
import numpy as np
import sys

from pathlib import Path

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler


# -----------------------------------
# PATH SETUP
# -----------------------------------

# repository root (aml_system) used for data
ROOT_DIR = Path(__file__).resolve().parents[3]

# backend folder used for model storage (aml_system/backend)
BACKEND_DIR = Path(__file__).resolve().parents[2]

DATASET_PATH = ROOT_DIR / "data" / "processed" / "final_dataset.csv"

MODEL_DIR = BACKEND_DIR / "app" / "models" / "transaction"

MODEL_DIR.mkdir(parents=True, exist_ok=True)

if __package__ in (None, ""):
    if str(BACKEND_DIR) not in sys.path:

        sys.path.insert(
            0,
            str(BACKEND_DIR)
        )

from app.core.feature_schema import BEHAVIOR_SCHEMA, BEHAVIOR_NUMERIC_FEATURES

from training.common.metrics import evaluate_binary_model

# -----------------------------------
# MAIN TRAINING
# -----------------------------------


def train():

    print(
        "\n🚀 Starting Behavioral Model Training..."
    )

    # -----------------------------------
    # LOAD DATASET
    # -----------------------------------

    df = pd.read_csv(
        DATASET_PATH
    )

    print(
        f"✅ Dataset Loaded: {len(df)} rows"
    )

    # -----------------------------------
    # FEATURE ENGINEERING
    # -----------------------------------

    from training.transaction.behavioral_feature_pipeline import (
        build_behavioral_features
    )

    X, y = build_behavioral_features(df)

    print(
        f"✅ Features Prepared: {X.shape[1]} features"
    )

    # -----------------------------------
    # TRAIN / TEST SPLIT
    # -----------------------------------

    X_train, X_test, y_train, y_test = train_test_split(

        X,

        y,

        test_size=0.2,

        stratify=y,

        random_state=42
    )

    print(
        "✅ Train/Test Split Completed"
    )

    # -----------------------------------
    # SCALE NUMERICAL FEATURES ONLY
    # -----------------------------------

    num_cols = [column for column in BEHAVIOR_NUMERIC_FEATURES if column in X.columns]

    scaler = StandardScaler()

    X_train[num_cols] = scaler.fit_transform(
        X_train[num_cols]
    )

    X_test[num_cols] = scaler.transform(
        X_test[num_cols]
    )

    print(
        "✅ Numerical Feature Scaling Completed"
    )

    # -----------------------------------
    # LIGHTGBM MODEL
    # -----------------------------------

    model = lgb.LGBMClassifier(

        objective="binary",

        n_estimators=500,

        learning_rate=0.05,

        num_leaves=64,

        max_depth=10,

        class_weight="balanced",

        subsample=0.8,

        colsample_bytree=0.8,

        random_state=42
    )

    print(
        "🧠 Training LightGBM Behavioral Model..."
    )

    model.fit(

        X_train,

        y_train,

        eval_set=[(X_test, y_test)],

        callbacks=[
            lgb.early_stopping(
                stopping_rounds=50
            )
        ]
    )

    print(
        "✅ Model Training Completed"
    )

    # -----------------------------------
    # PREDICTIONS
    # -----------------------------------

    preds = model.predict(
        X_test
    )

    probs = model.predict_proba(
        X_test
    )[:, 1]

    # -----------------------------------
    # EVALUATION
    # -----------------------------------

    evaluate_binary_model(

        y_true=y_test,

        y_pred=preds,

        y_prob=probs,

        model_name="BEHAVIORAL MODEL"
    )

    # -----------------------------------
    # SAVE MODEL
    # -----------------------------------

    joblib.dump(

        model,

        MODEL_DIR
        / "behavioral_lightgbm.pkl"
    )

    print(
        "✅ behavioral_lightgbm.pkl saved"
    )

    # -----------------------------------
    # SAVE SCALER
    # -----------------------------------

    joblib.dump(

        scaler,

        MODEL_DIR
        / "behavioral_scaler.pkl"
    )

    print(
        "✅ behavioral_scaler.pkl saved"
    )

    # -----------------------------------
    # SAVE FEATURE SCHEMA
    # -----------------------------------

    feature_schema = {
        "features": BEHAVIOR_SCHEMA["features"],
        "numerical_features": BEHAVIOR_SCHEMA["numerical_features"],
        "categorical_features": BEHAVIOR_SCHEMA["categorical_features"],
    }

    with open(

        MODEL_DIR
        / "behavioral_features.json",

        "w"
    ) as f:

        json.dump(
            feature_schema,
            f,
            indent=2
        )

    print(
        "✅ behavioral_features.json saved"
    )

    # -----------------------------------
    # FEATURE IMPORTANCE
    # -----------------------------------

    importance_df = pd.DataFrame({

        "feature": X.columns,

        "importance": model.feature_importances_
    })

    importance_df = importance_df.sort_values(

        by="importance",

        ascending=False
    )

    print(
        "\n========== TOP FEATURES =========="
    )

    print(
        importance_df.head(15)
    )

    print(
        "\n🎯 BEHAVIORAL MODEL TRAINING COMPLETED"
    )


# -----------------------------------
# ENTRYPOINT
# -----------------------------------

if __name__ == "__main__":

    train()