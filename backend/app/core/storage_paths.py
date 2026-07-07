from pathlib import Path

# Base directory: repository root TrustVault/
BASE_DIR = Path(__file__).resolve().parents[3]

DATA_DIR = BASE_DIR / "data"

PROCESSED_DIR = DATA_DIR / "processed"

ALERTS_DIR = PROCESSED_DIR / "alerts"

REPORTS_DIR = PROCESSED_DIR / "reports"

CASES_DIR = PROCESSED_DIR / "cases"

AUDIT_DIR = PROCESSED_DIR / "audit"

EXPLAINABILITY_DIR = PROCESSED_DIR / "explainability"

LOGS_DIR = BASE_DIR / "logs"

ALL_STORAGE_DIRS = [
    DATA_DIR,
    PROCESSED_DIR,
    ALERTS_DIR,
    REPORTS_DIR,
    CASES_DIR,
    AUDIT_DIR,
    EXPLAINABILITY_DIR,
    LOGS_DIR,
]


def initialize_storage_directories() -> None:
    for directory in ALL_STORAGE_DIRS:
        try:
            directory.mkdir(parents=True, exist_ok=True)
        except Exception:
            # best-effort, don't raise during initialize
            pass
