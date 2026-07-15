# backend/app/services/device_intelligence_service.py

import pandas as pd

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[4]

ONBOARDING_RESULTS = BASE_DIR / "data" / "processed" / "onboarding" / "account_risk_snapshot.csv"


class DeviceIntelligenceService:

    def __init__(self):

        try:

            self.df = pd.read_csv(
                ONBOARDING_RESULTS
            )

        except:

            self.df = pd.DataFrame()

    def is_device_mule_hub(
        self,
        device_id
    ):

        if self.df.empty:
            return False

        suspicious = self.df[
            self.df["risk_level"]
            .isin([
                "REJECT",
                "REVIEW"
            ])
        ]

        count = len(
            suspicious[
                suspicious["device_id"]
                == device_id
            ]
        )

        return count >= 3