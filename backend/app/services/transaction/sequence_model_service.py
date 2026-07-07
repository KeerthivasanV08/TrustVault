from typing import Dict, Any
import logging
import numpy as np
import pandas as pd

from app.core.feature_schema import SEQUENCE_FEATURES
from app.core.model_loader import sequence_model

logger = logging.getLogger(__name__)
_MODEL_FALLBACK_LOGGED = False


class SequenceModelService:
    def __init__(self):
        self.model, self.scaler, self.metadata = sequence_model()
        self.sequence_features = (self.metadata or {}).get("features") or SEQUENCE_FEATURES

    def _fallback_score(self, behavioral_score: float | None = None) -> Dict[str, Any]:
        global _MODEL_FALLBACK_LOGGED
        if not _MODEL_FALLBACK_LOGGED:
            logger.warning("Sequence fallback activated: model unavailable or inference error")
            _MODEL_FALLBACK_LOGGED = True
        fallback = round(float(behavioral_score or 0.0) * 0.85, 4)
        return {"sequence_score": fallback, "sequence_pattern": "FALLBACK_BEHAVIORAL_PROXY"}

    def predict_sequence(self, last_transactions: pd.DataFrame, behavioral_score: float | None = None) -> Dict[str, Any]:
        if self.model is None:
            return self._fallback_score(behavioral_score)

        # last_transactions expected to be ordered oldest->newest
        if last_transactions is None or len(last_transactions) == 0:
            return {"sequence_score": 0.0, "sequence_pattern": "INSUFFICIENT_HISTORY"}

        seq_len = (self.metadata or {}).get("sequence_length", 10)

        if len(last_transactions) < seq_len:
            return {"sequence_score": 0.0, "sequence_pattern": "INSUFFICIENT_HISTORY"}

        try:
            features = last_transactions.copy()
            for column in self.sequence_features:
                if column not in features.columns:
                    features[column] = 0
            features = features[self.sequence_features].copy()
            num_cols = features.select_dtypes(include=["number"]).columns.tolist()

            if self.scaler is not None and len(num_cols):
                features[num_cols] = self.scaler.transform(features[num_cols])

            arr = features.values[-seq_len:]
            X = np.expand_dims(arr, 0)

            # model may be a Keras model or sklearn wrapper
            score = 0.0
            if self.model is not None:
                try:
                    if hasattr(self.model, "predict_proba"):
                        score = float(self.model.predict_proba(X)[0][1])
                    else:
                        score = float(self.model.predict(X)[0][0])
                except Exception:
                    logger.exception("Sequence model inference failed; using fallback")
                    return self._fallback_score(behavioral_score)

            # Simple heuristic-based pattern interpretation
            avg_amount = float(features["amount"].iloc[-seq_len:].mean()) if "amount" in features.columns else 0.0
            velocity = float(features.get("txn_velocity_1h", pd.Series([0])).iloc[-1]) if "txn_velocity_1h" in features.columns else 0.0

            if velocity > 10000 and score > 0.6:
                pattern = "GATHER_SCATTER"
            elif avg_amount > 50000 and score > 0.6:
                pattern = "LAUNDERING_FLOW"
            else:
                pattern = "SUSPICIOUS_BUT_UNCLEAR" if score > 0.5 else "NONE"

            return {"sequence_score": round(score, 4), "sequence_pattern": pattern}

        except Exception:
            logger.exception("Failed to build sequence inference; using fallback")
            return self._fallback_score(behavioral_score)
