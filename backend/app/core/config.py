import os
from pathlib import Path
from typing import List


def _split_origins(val: str) -> List[str]:
    return [s.strip() for s in val.split(",") if s.strip()]


REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings:
    PROJECT_NAME = "TrustVault AML"

    DATA_DIR = REPO_ROOT / "data"
    RAW_DIR = DATA_DIR / "raw"
    PROCESSED_DIR = DATA_DIR / "processed"

    MODEL_DIR = BACKEND_DIR / "app" / "models"

    ONBOARDING_MODEL_PATH = MODEL_DIR / "onboarding" / "onboarding_lightgbm.pkl"
    TRANSACTION_MODEL_PATH = MODEL_DIR / "transaction" / "behavioral_lightgbm.pkl"

    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    def __init__(self) -> None:
        raw = os.environ.get("FRONTEND_ORIGINS")
        if raw:
            self.FRONTEND_ORIGINS = _split_origins(raw)
        else:
            # sensible local defaults for development
            self.FRONTEND_ORIGINS = [
                "http://localhost:8080",
                "http://127.0.0.1:8080",
                "http://localhost:5173",
                "http://127.0.0.1:5173",
            ]


settings = Settings()