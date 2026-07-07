from typing import Dict, List, Optional, Any, Mapping
import logging

import pandas as pd
import numpy as np

from app.core.feature_schema import (
    BEHAVIOR_CATEGORICAL_FEATURES,
    BEHAVIOR_FEATURE_ORDER,
    BEHAVIOR_NUMERIC_FEATURES,
)
from app.core.feature_validator import validate_behavior_features
from app.core.model_loader import behavioral_model

logger = logging.getLogger(__name__)


class MLBehaviorService:
    def __init__(self):
        self.model, self.scaler, self.features = behavioral_model()
        self.feature_order = BEHAVIOR_FEATURE_ORDER

    def _default_row(self) -> Dict[str, Any]:
        return {
            feature: (0 if feature in BEHAVIOR_NUMERIC_FEATURES else "UNKNOWN")
            for feature in self.feature_order
        }

    def _lookup(self, source: Mapping[str, Any], keys: List[str], default: Any = 0) -> Any:
        for key in keys:
            value = source.get(key)
            if value not in (None, ""):
                return value
        return default

    def build_features_from_context(
        self,
        txn: Dict,
        velocity_context: Dict,
        onboarding_context: Dict,
        graph_context: Optional[Dict] = None,
    ) -> pd.DataFrame:
        row = self._default_row()

        row.update({
            "amount": txn.get("amount", 0),
            "sender_bal_before": txn.get("sender_bal_before", txn.get("balance_before", 0)),
            "sender_bal_after": txn.get("sender_bal_after", txn.get("balance_after", 0)),
            "receiver_bal_after": txn.get("receiver_bal_after", 0),
            "is_sim_bound": txn.get("is_sim_bound", onboarding_context.get("sim_binding_ok", 0)),
            "time_to_pay_ms": txn.get("time_to_pay_ms", 0),
            "amount_deviation": txn.get("amount_deviation", 0),
            "balance_depletion_speed": txn.get("balance_depletion_speed", 0),
            "counterparty_diversity": velocity_context.get("unique_counterparties_24h", 0),
            "distance_from_1L_threshold": txn.get("distance_from_1L_threshold", 0),
            "distance_from_50k_threshold": txn.get("distance_from_50k_threshold", 0),
            "drain_ratio": velocity_context.get("drain_ratio", 0),
            "empty_account_flag": txn.get("empty_account_flag", 0),
            "forwarding_delay_mins": velocity_context.get("forwarding_delay_mins", 999),
            "fragmentation_score": velocity_context.get("fragmentation_score", 0),
            "is_night_tx": txn.get("is_night_tx", 0),
            "is_round_amount": txn.get("is_round_amount", 0),
            "is_sim_bound_at_tx": txn.get("is_sim_bound_at_tx", onboarding_context.get("sim_binding_ok", 0)),
            "near_threshold_flag": velocity_context.get("near_threshold_count", 0),
            "rapid_outbound_after_inbound": velocity_context.get("rapid_outbound_after_inbound", 0),
            "txn_velocity_1h": velocity_context.get("txn_velocity_1h", velocity_context.get("txn_burst_count", 0)),
            "identity_trust_score": onboarding_context.get("identity_trust_score", 0),
            "device_trust_score": onboarding_context.get("device_trust_score", 0),
            "sim_binding_ok": onboarding_context.get("sim_binding_ok", 1),
            "sim_swap_flag": onboarding_context.get("sim_swap_flag", 0),
            "vpn_flag": onboarding_context.get("vpn_flag", 0),
            "hosting_flag": onboarding_context.get("hosting_flag", 0),
            "city_mismatch_flag": onboarding_context.get("city_mismatch_flag", 0),
            "device_age_years": onboarding_context.get("device_age_years", 0),
            "graph_score": 0 if graph_context is None else graph_context.get("graph_score", 0),
            "known_fraud_connections": 0 if graph_context is None else graph_context.get("known_fraud_neighbors", 0),
            "mule_cluster_size": 0 if graph_context is None else graph_context.get("cluster_size", 0),
            "inbound_sources": 0 if graph_context is None else graph_context.get("inbound_sources", 0),
            "outbound_dest": 0 if graph_context is None else graph_context.get("outbound_dest", 0),
            "rapid_account_cluster_flag": 0 if graph_context is None else graph_context.get("rapid_account_cluster_flag", 0),
            "mule_cluster_flag": 0 if graph_context is None else graph_context.get("mule_cluster_flag", 0),
            "tx_count_24h": velocity_context.get("txn_count_24h", 0),
            "avg_tx_amount_7d": velocity_context.get("avg_tx_amount_7d", 0),
            "unique_receivers_7d": velocity_context.get("unique_receivers_7d", 0),
            "days_since_last_tx": velocity_context.get("days_since_last_tx", 0),
            "account_age_days": onboarding_context.get("account_age_days", 0),
            "high_value_txn": txn.get("high_value_txn", 0),
            "rapid_movement": velocity_context.get("rapid_movement", 0),
            "pass_through_ratio": velocity_context.get("pass_through_ratio", 0),
            "structuring_pattern": txn.get("structuring_pattern", 0),
            "night_high_value_txn": txn.get("night_high_value_txn", 0),
            "velocity_risk_score": velocity_context.get("velocity_risk_score", 0),
            "network_risk_score": onboarding_context.get("network_risk_score", 0),
            "transaction_type": self._lookup(txn, ["transaction_type", "txn_type", "type"], "UNKNOWN"),
            "channel": self._lookup(txn, ["channel", "payment_channel", "mode"], "UNKNOWN"),
        })

        return validate_behavior_features(pd.DataFrame([row]))

    def predict_behavior_risk(self, features: pd.DataFrame) -> Dict:
        if self.model is None:
            logger.warning("Behavioral model not loaded")
            return {"behavior_score": 0.0, "behavior_label": "UNKNOWN", "top_features": []}

        X = validate_behavior_features(features)
        num_cols = [column for column in BEHAVIOR_NUMERIC_FEATURES if column in X.columns]
        logger.info("[FEATURES] Columns received: %s", list(features.columns))
        logger.info("[SCALER] Expected numeric cols: %s", num_cols)
        logger.info("[MODEL] Predicting with shape: %s", X.shape)

        try:
            if self.scaler is not None and len(num_cols):
                X[num_cols] = self.scaler.transform(X[num_cols])
        except Exception:
            logger.exception("Failed to scale features")

        for column in BEHAVIOR_CATEGORICAL_FEATURES:
            if column in X.columns:
                try:
                    X[column] = X[column].astype("category")
                except Exception:
                    X[column] = pd.Series(["UNKNOWN"] * len(X), dtype="category")

        try:
            prob = float(self.model.predict_proba(X)[0][1])
        except Exception:
            logger.exception("Behavioral model prediction failed")
            prob = 0.0

        # top feature importances
        top_features: List[str] = []
        try:
            feat_names = self.feature_order
            importances = getattr(self.model, "feature_importances_", None)
            if importances is not None and len(importances) == len(feat_names):
                idx = np.argsort(importances)[::-1][:5]
                top_features = [feat_names[i] for i in idx]
        except Exception:
            logger.exception("Failed to extract feature importances")

        score = round(prob, 4)
        label = "SUSPICIOUS" if score >= 0.7 else ("REVIEW" if score >= 0.5 else "ALLOW")

        reasons = [f"ML elevated risk due to {feature}" for feature in top_features]

        return {
            "behavior_score": score,
            "behavior_label": label,
            "top_features": top_features,
            "reasons": reasons,
        }
