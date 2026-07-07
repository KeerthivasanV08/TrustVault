from .onboarding_context_service import OnboardingContextService
from .onboarding_control_service import OnboardingControlService
from .onboarding_inference_service import OnboardingInferenceService
from .onboarding_decision_engine import OnboardingDecisionEngine
from .onboarding_explainability_service import OnboardingExplainabilityService
from .onboarding_audit_service import OnboardingAuditService
from .onboarding_feature_builder import OnboardingFeatureBuilder
from app.services.alerts.onboarding_alert_service import create_onboarding_alert


class OnboardingService:
    def __init__(self):
        self.context = OnboardingContextService()
        self.control = OnboardingControlService()
        self.feature_builder = OnboardingFeatureBuilder()
        self.ml = OnboardingInferenceService()
        self.decision = OnboardingDecisionEngine()
        self.explain = OnboardingExplainabilityService()
        self.audit = OnboardingAuditService()

    def process(self, request_data: dict):
        ip_context = self.context.get_ip_risk(request_data["ip_address"])
        device_context = self.context.get_device_age(request_data["device_id"])

        context = {
            **request_data,
            **ip_context,
            **device_context,
        }

        control_result = self.control.evaluate(context)

        features = self.feature_builder.build_features(context)

        ml_output = self.ml.predict_onboarding_risk(features)

        if "top_features" not in ml_output:
            ml_output["top_features"] = []

        ml_output = {
            **ml_output,
            "identity_risk": round(float(ml_output.get("ml_probability", 0.0)) * 100, 2),
            "confidence": round(1.0 - float(ml_output.get("ml_probability", 0.0)), 4),
            "model_version": ml_output.get("model_version", "onboarding_v1"),
        }

        reasons = self.explain.explain(
            context=context,
            control=control_result,
            ml_output=ml_output,
        )

        decision_output = self.decision.decide(
            control=control_result,
            ml_output=ml_output,
            context=context,
            evidence=reasons,
        )

        audit_record = {
            "user_id": request_data.get("user_id"),
            "decision": decision_output["decision"],
            "identity_risk": ml_output["identity_risk"],
            "confidence": ml_output["confidence"],
            "model_version": ml_output.get("model_version"),
            "control_status": control_result["status"],
            "requires_review": decision_output["requires_review"],
            "requires_block": decision_output["requires_block"],
            "requires_edd": decision_output["requires_edd"],
            "officer_recommendation": decision_output["officer_recommendation"],
            "reasons": "|".join(reasons),
        }

        self.audit.log(audit_record)

        if decision_output["decision"] in {"BLOCK", "REVIEW"} or decision_output.get("requires_review"):
            try:
                create_onboarding_alert({
                    "user_id": request_data.get("user_id"),
                    "decision": decision_output["decision"],
                    "final_score": ml_output["identity_risk"] / 100.0,
                    "risk_score": ml_output["identity_risk"],
                    "requires_edd": decision_output.get("requires_edd", False),
                    "alert_type": "ONBOARDING_RISK",
                    "metadata": {
                        "context": context,
                        "control": control_result,
                        "ml": ml_output,
                    },
                })
            except Exception:
                pass

        return {
            "user_id": request_data.get("user_id"),
            "decision": decision_output["decision"],
            "identity_risk": ml_output["identity_risk"],
            "confidence": ml_output["confidence"],
            "model_version": ml_output.get("model_version"),
            "control": control_result,
            "requires_review": decision_output["requires_review"],
            "requires_block": decision_output["requires_block"],
            "requires_edd": decision_output["requires_edd"],
            "officer_recommendation": decision_output["officer_recommendation"],
            "reasons": reasons,
        }