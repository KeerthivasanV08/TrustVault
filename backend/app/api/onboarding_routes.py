from fastapi import APIRouter, HTTPException
from pathlib import Path
import pandas as pd

from app.core import storage_paths

from schemas.onboarding_schema import OnboardingRequest
from app.services.onboarding.onboarding_service import OnboardingService
from app.services.onboarding.onboarding_explainability_service import OnboardingExplainabilityService
from app.realtime.transaction_memory_store import LIVE_ALERTS

router = APIRouter(tags=["Onboarding"])

service = OnboardingService()
explain_service = OnboardingExplainabilityService()


ONBOARDING_RESULTS_FILE = storage_paths.AUDIT_DIR / "onboarding_results.csv"


@router.post("/onboarding")
def onboard_user(request: OnboardingRequest):
    return service.process(request.model_dump())


@router.post("/evaluate")
def evaluate_onboarding(request: OnboardingRequest):
    return service.process(request.model_dump())


@router.get("/explain/{user_id}")
def explain_onboarding(user_id: str):
    if ONBOARDING_RESULTS_FILE.exists():
        try:
            df = pd.read_csv(ONBOARDING_RESULTS_FILE)
            if "user_id" in df.columns:
                rows = df[df["user_id"].astype(str) == str(user_id)]
                if not rows.empty:
                    latest = rows.tail(1).iloc[0].to_dict()
                    reasons = str(latest.get("reasons", "")).split("|") if latest.get("reasons") else []
                    return {
                        "user_id": user_id,
                        "decision": latest.get("decision"),
                        "identity_risk": latest.get("identity_risk"),
                        "confidence": latest.get("confidence"),
                        "officer_recommendation": latest.get("officer_recommendation"),
                        "reasons": [reason for reason in reasons if reason],
                        "raw": latest,
                    }
        except Exception:
            pass

    raise HTTPException(status_code=404, detail="Onboarding explanation not found")


@router.get("/alerts")
def onboarding_alerts():
    return [alert for alert in list(LIVE_ALERTS) if str(alert.get("alert_id", "")).startswith("ONB-") or "ONBOARDING" in str(alert.get("alert_type", "")).upper()]


@router.get("/alerts/p1")
def onboarding_p1_alerts():
    return [alert for alert in onboarding_alerts() if alert.get("priority") == "P1"]


@router.get("/alerts/p2")
def onboarding_p2_alerts():
    return [alert for alert in onboarding_alerts() if alert.get("priority") == "P2"]