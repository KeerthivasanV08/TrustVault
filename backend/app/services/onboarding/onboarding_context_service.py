import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[4]

IP_RISK_PATH = (
    BASE_DIR
    / "data"
    / "reference"
    / "ip_risk_reference.csv"
)

DEVICE_REF_PATH = (
    BASE_DIR
    / "data"
    / "raw"
    / "device_age_reference.csv"
)


class OnboardingContextService:

    _ip_cache = None
    _device_cache = None

    def __init__(self):

        if OnboardingContextService._ip_cache is None:

            OnboardingContextService._ip_cache = (
                self._safe_read(IP_RISK_PATH)
            )

        if OnboardingContextService._device_cache is None:

            OnboardingContextService._device_cache = (
                self._safe_read(DEVICE_REF_PATH)
            )

    def _safe_read(self, path: Path):

        if path.exists():
            return pd.read_csv(path)

        return pd.DataFrame()

    def get_ip_risk(self, ip: str):

        df = self._ip_cache

        if df.empty or "ip" not in df.columns:
            return self._default_ip_risk()

        match = df[df["ip"] == ip]

        if match.empty:
            return self._default_ip_risk()

        row = match.iloc[0]

        return {

            "vpn_flag":
                int(row.get("vpn_flag", 0)),

            "vpn_hosting_flag":
                int(row.get("hosting_flag", 0)),

            "proxy_flag":
                int(row.get("proxy_flag", 0)),

            "tor_flag":
                int(row.get("tor_flag", 0)),

            "ip_risk_score":
                float(row.get("risk_score", 10)),

            "country_risk_score":
                float(row.get("country_risk", 10)),
        }

    def get_device_age(self, device_id: str):

        df = self._device_cache

        if df.empty or "device_id" not in df.columns:

            return {
                "device_age_days": 0
            }

        match = df[df["device_id"] == device_id]

        if match.empty:

            return {
                "device_age_days": 0
            }

        return {

            "device_age_days":
                int(match.iloc[0].get(
                    "device_age_days",
                    0
                ))
        }

    def _default_ip_risk(self):

        return {

            "vpn_flag": 0,
            "vpn_hosting_flag": 0,
            "proxy_flag": 0,
            "tor_flag": 0,
            "ip_risk_score": 10,
            "country_risk_score": 10,
        }