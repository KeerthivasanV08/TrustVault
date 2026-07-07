import joblib
import pandas as pd

from pathlib import Path

from app.services.transaction.sequence_service import (
    detect_sequence_patterns
)

from app.services.transaction.structuring_service import (
    detect_structuring
)

from app.services.shared.confidence_service import (
    calculate_confidence
)

BASE_DIR = Path(__file__).resolve().parents[2]

MODEL_PATH = (
    BASE_DIR /
    "models" /
    "transaction" /
    "behavioral_lightgbm.pkl"
)


class BehavioralEngine:

    def __init__(self):

        self.model = joblib.load(
            MODEL_PATH
        )

    def evaluate_behavior(
        self,
        txn,
        user_vel,
        onboarding_risk
    ):

        risk_score = 0

        reasons = []

        # ============================================
        # ML FEATURE VECTOR
        # ============================================

        features = pd.DataFrame([{
            "rolling_24h_sum":
                user_vel["rolling_24h_sum"],

            "drain_ratio":
                user_vel["drain_ratio"],

            "fragmentation_score":
                user_vel["fragmentation_score"],

            "txn_burst_count":
                user_vel["txn_count_24h"]
        }])

        # ============================================
        # ML PREDICTION
        # ============================================

        ml_probability = (
            self.model
            .predict_proba(features)[0][1]
        )

        risk_score += ml_probability * 100

        # ============================================
        # SEQUENCE INTELLIGENCE
        # ============================================

        patterns = detect_sequence_patterns(
            txn
        )

        if "RAPID_RELAY" in patterns:

            risk_score += 30

            reasons.append(
                "RAPID_IN_OUT_RELAY"
            )

        if "INSTANT_FORWARDING" in patterns:

            risk_score += 20

            reasons.append(
                "INSTANT_FORWARDING"
            )

        # ============================================
        # STRUCTURING
        # ============================================

        if detect_structuring(
            txn["amount"]
        ):

            risk_score += 25

            reasons.append(
                "NEAR_THRESHOLD_STRUCTURING"
            )

        # ============================================
        # GATHER-SCATTER
        # ============================================

        if (
            user_vel["drain_ratio"] > 0.95 and
            user_vel["unique_counterparties_24h"] > 3 and
            user_vel["avg_holding_time_mins"] < 10
        ):

            risk_score += 35

            reasons.append(
                "GATHER_SCATTER_PATTERN"
            )

        # ============================================
        # SLOW BLEED
        # ============================================

        if (
            user_vel["rolling_24h_sum"] > 80000
        ):

            risk_score += 20

            reasons.append(
                "SLOW_BLEED_PATTERN"
            )

        # ============================================
        # BALANCE DEPLETION
        # ============================================

        if (
            txn["balance_depletion_speed"] > 100
        ):

            risk_score += 15

            reasons.append(
                "RAPID_BALANCE_DRAIN"
            )

        # ============================================
        # CROSS-GATE ESCALATION
        # ============================================

        if (
            onboarding_risk.get(
                "vpn_hosting_flag",
                0
            ) == 1
        ):

            risk_score *= 1.5

            reasons.append(
                "VPN_ESCALATION"
            )

        # ============================================
        # FINAL CONFIDENCE
        # ============================================

        confidence = calculate_confidence(
            feature_count=8,
            anomaly_count=len(reasons)
        )

        # ============================================
        # RETURN
        # ============================================

        return {

            "risk_score": min(
                round(risk_score, 2),
                100
            ),

            "confidence": round(
                confidence,
                2
            ),

            "reasons": reasons
        }