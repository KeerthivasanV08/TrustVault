# training/onboarding/evaluate_onboarding_model.py

import joblib

from pathlib import Path

from onboarding_feature_pipeline import (
    prepare_onboarding_training_data
)

BASE_DIR = Path(__file__).resolve().parents[3]

MODEL_DIR = (
    BASE_DIR
    / "app"
    / "models"
    / "onboarding"
)

DATASET_PATH = (
    BASE_DIR
    / "data"
    / "processed"
    / "onboarding_final_dataset.csv"
)


def evaluate():

    X, y = prepare_onboarding_training_data()

    model = joblib.load(
        MODEL_DIR / "onboarding_lightgbm.pkl"
    )

    scaler = joblib.load(
        MODEL_DIR / "onboarding_scaler.pkl"
    )

    X = scaler.transform(X)

    score = model.score(
        scaler.transform(X),
        y
    )

    print(
        f"Accuracy: {score}"
    )


if __name__ == "__main__":
    evaluate()