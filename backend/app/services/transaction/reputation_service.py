# backend/app/services/onboarding_reputation_service.py

import pandas as pd
from pathlib import Path


# ---------------------------------------------------
# PATH SETUP
# ---------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[4]

ONBOARDING_PATH = BASE_DIR / "data" / "processed" / "onboarding" / "account_risk_snapshot.csv"


# ---------------------------------------------------
# SERVICE
# ---------------------------------------------------

class OnboardingReputationService:

    def __init__(self):

        try:

            self.df = pd.read_csv(ONBOARDING_PATH)

            # High-speed lookup
            self.df = self.df.drop_duplicates(
                subset=["user_id"],
                keep="last"
            )

            self.df = self.df.set_index("user_id")

            print("✅ Onboarding Reputation Service Loaded")

        except Exception as e:

            print(f"❌ Failed loading account_risk_snapshot.csv: {e}")

            self.df = pd.DataFrame()

    # ---------------------------------------------------
    # MAIN VALIDATION METHOD
    # ---------------------------------------------------

    def validate_sender(self, sender_id, amount):

        """
        Gate 2 pre-validation.

        Returns:
            {
                decision,
                reason,
                cooling_period_active
            }
        """

        # ---------------------------------------------------
        # USER EXISTS?
        # ---------------------------------------------------

        if sender_id not in self.df.index:

            return {
                "decision": "BLOCK",
                "reason": "UNKNOWN_ONBOARDING_PROFILE",
                "cooling_period_active": 0
            }

        user = self.df.loc[sender_id]

        # ---------------------------------------------------
        # HARD BLOCK
        # ---------------------------------------------------

        if user["decision"] == "REJECT":

            return {
                "decision": "BLOCK",
                "reason": "ONBOARDING_REJECTED_USER",
                "cooling_period_active": int(
                    user.get("cooling_period_active", 0)
                )
            }

        # ---------------------------------------------------
        # RBI COOLING PERIOD RULE
        # ---------------------------------------------------

        cooling_active = int(
            user.get("cooling_period_active", 0)
        )

        if cooling_active == 1 and amount > 5000:

            return {
                "decision": "BLOCK",
                "reason": "RBI_COOLING_PERIOD_LIMIT_EXCEEDED",
                "cooling_period_active": 1
            }

        # ---------------------------------------------------
        # MANUAL REVIEW PROPAGATION
        # ---------------------------------------------------

        if user["decision"] == "REVIEW":

            return {
                "decision": "REVIEW",
                "reason": "HIGH_RISK_ONBOARDING_PROFILE",
                "cooling_period_active": cooling_active
            }

        # ---------------------------------------------------
        # CLEAN PASS
        # ---------------------------------------------------

        return {
            "decision": "PASS",
            "reason": "ONBOARDING_PROFILE_CLEAN",
            "cooling_period_active": cooling_active
        }