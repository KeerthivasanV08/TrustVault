# training/onboarding/train_onboarding_model.py

import json
from pathlib import Path

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd

from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score
)

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from imblearn.over_sampling import SMOTE

from onboarding_feature_pipeline import (
    prepare_onboarding_training_data
)


BASE_DIR = Path(__file__).resolve().parents[2]

MODEL_DIR = (
    BASE_DIR
    / "app"
    / "models"
    / "onboarding"
)

MODEL_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# =========================================================
# TRAINING CONFIG
# =========================================================

RANDOM_STATE = 42

TEST_SIZE = 0.2

THRESHOLD = 0.60


# =========================================================
# LOAD DATA
# =========================================================

print("\n🚀 Loading Onboarding Training Data...")

X, y = prepare_onboarding_training_data()

print("✅ Training Data Ready")


# =========================================================
# TRAIN TEST SPLIT
# =========================================================

X_train, X_test, y_train, y_test = train_test_split(

    X,
    y,

    test_size=TEST_SIZE,

    random_state=RANDOM_STATE,

    stratify=y
)

print("✅ Train/Test Split Completed")


# =========================================================
# SCALING
# =========================================================

scaler = StandardScaler()

X_train_scaled = scaler.fit_transform(
    X_train
)

X_test_scaled = scaler.transform(
    X_test
)

print("✅ Feature Scaling Completed")


# =========================================================
# HANDLE IMBALANCE
# =========================================================

print("⚖️ Applying SMOTE...")

smote = SMOTE(
    random_state=RANDOM_STATE
)

X_train_balanced, y_train_balanced = smote.fit_resample(
    X_train_scaled,
    y_train
)

print("✅ SMOTE Completed")


# =========================================================
# LIGHTGBM MODEL
# =========================================================

print("🧠 Training LightGBM Model...")

model = lgb.LGBMClassifier(

    objective="binary",

    boosting_type="gbdt",

    learning_rate=0.03,

    n_estimators=300,

    max_depth=8,

    num_leaves=64,

    subsample=0.9,

    colsample_bytree=0.9,

    reg_alpha=0.5,

    reg_lambda=0.5,

    min_child_samples=20,

    is_unbalance=True,

    random_state=RANDOM_STATE
)

model.fit(

    X_train_balanced,
    y_train_balanced
)

print("✅ Model Training Completed")


# =========================================================
# PREDICTIONS
# =========================================================

y_probs = model.predict_proba(
    X_test_scaled
)[:, 1]

y_pred = (
    y_probs >= THRESHOLD
).astype(int)


# =========================================================
# METRICS
# =========================================================

precision = precision_score(
    y_test,
    y_pred
)

recall = recall_score(
    y_test,
    y_pred
)

f1 = f1_score(
    y_test,
    y_pred
)

roc_auc = roc_auc_score(
    y_test,
    y_probs
)

print("\n========== MODEL METRICS ==========")

print(f"Precision : {precision:.4f}")
print(f"Recall    : {recall:.4f}")
print(f"F1 Score  : {f1:.4f}")
print(f"ROC AUC   : {roc_auc:.4f}")

print("\n========== CLASSIFICATION REPORT ==========")

print(
    classification_report(
        y_test,
        y_pred
    )
)

print("\n========== CONFUSION MATRIX ==========")

print(
    confusion_matrix(
        y_test,
        y_pred
    )
)


# =========================================================
# FEATURE IMPORTANCE
# =========================================================

importance_df = pd.DataFrame({

    "feature": X.columns,

    "importance": model.feature_importances_
})

importance_df = importance_df.sort_values(
    by="importance",
    ascending=False
)

print("\n========== TOP FEATURES ==========")

print(
    importance_df.head(20)
)


# =========================================================
# SAVE MODEL
# =========================================================

joblib.dump(

    model,

    MODEL_DIR
    / "onboarding_lightgbm.pkl"
)

print("✅ onboarding_lightgbm.pkl saved")


# =========================================================
# SAVE SCALER
# =========================================================

joblib.dump(

    scaler,

    MODEL_DIR
    / "onboarding_scaler.pkl"
)

print("✅ onboarding_scaler.pkl saved")


# =========================================================
# SAVE TRAINING METADATA
# =========================================================

metadata = {

    "model_name": "onboarding_lightgbm",

    "version": "v2026.1",

    "threshold": THRESHOLD,

    "features_count": len(X.columns),

    "train_rows": len(X_train),

    "test_rows": len(X_test),

    "precision": float(precision),

    "recall": float(recall),

    "f1_score": float(f1),

    "roc_auc": float(roc_auc)
}

with open(
    MODEL_DIR / "onboarding_training_metadata.json",
    "w"
) as f:

    json.dump(
        metadata,
        f,
        indent=4
    )

print("✅ onboarding_training_metadata.json saved")


# =========================================================
# FINAL MESSAGE
# =========================================================

print("\n🎯 ONBOARDING MODEL TRAINING COMPLETED")
print("✅ LightGBM model saved")
print("✅ Scaler saved")
print("✅ Feature schema saved")
print("✅ Metadata saved")