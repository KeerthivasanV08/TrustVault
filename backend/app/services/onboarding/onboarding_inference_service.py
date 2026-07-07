import json
import joblib
import numpy as np
import pandas as pd

from pathlib import Path


# `app` directory (backend/app)
APP_DIR = Path(__file__).resolve().parents[2]

MODEL_DIR = APP_DIR / "models" / "onboarding"

MODEL_PATH = MODEL_DIR / "onboarding_lightgbm.pkl"

SCALER_PATH = MODEL_DIR / "onboarding_scaler.pkl"

FEATURE_PATH = MODEL_DIR / "onboarding_features.json"


class OnboardingInferenceService:

    _model = None
    _scaler = None
    _features = None

    def __init__(self):

        if self.__class__._model is None:

            self.__class__._model = (
                joblib.load(MODEL_PATH)
            )

            self.__class__._scaler = (
                joblib.load(SCALER_PATH)
            )

            with open(FEATURE_PATH, "r") as f:

                self.__class__._features = (
                    json.load(f)
                )

        self.model = self.__class__._model

        self.scaler = self.__class__._scaler

        self.features = self.__class__._features

    def predict_onboarding_risk(
        self,
        feature_df: pd.DataFrame
    ):

        expected_features = self.features["features"]

        feature_df = feature_df[
            expected_features
        ]

        scaled = self.scaler.transform(
            feature_df
        )

        prob = self.model.predict_proba(
            scaled
        )[:, 1][0]

        probability = round(
            float(prob),
            4
        )

        # -----------------------------------
        # LABEL
        # -----------------------------------

        if probability >= 0.90:

            label = "HIGH_RISK"

        elif probability >= 0.70:

            label = "MEDIUM_RISK"

        else:

            label = "LOW_RISK"

        # -----------------------------------
        # FEATURE IMPORTANCE
        # -----------------------------------

        importance = self.model.feature_importances_

        top_idx = np.argsort(
            importance
        )[::-1][:5]

        top_features = [

            expected_features[i]

            for i in top_idx
        ]

        return {

            "ml_probability":
                probability,

            "ml_label":
                label,

            "top_features":
                top_features
        }