from pathlib import Path

# Base directory: repository root TrustVault/
BASE_DIR = Path(__file__).resolve().parents[3]

DATA_DIR = BASE_DIR / "data"

PROCESSED_DIR = DATA_DIR / "processed"

TRAINING_DIR = PROCESSED_DIR / "training"

RUNTIME_DIR = PROCESSED_DIR / "runtime"

ALERTS_DIR = PROCESSED_DIR / "alerts"

REPORTS_DIR = PROCESSED_DIR / "reports"

CASES_DIR = PROCESSED_DIR / "cases"

AUDIT_DIR = PROCESSED_DIR / "audit"

EXPLAINABILITY_DIR = PROCESSED_DIR / "explainability"

REFERENCE_DIR = DATA_DIR / "reference"

ARCHIVE_DIR = DATA_DIR / "archive"

CASE_REGISTRY_PATH = CASES_DIR / "case_registry.csv"

TRAINING_VELOCITY_PATH = TRAINING_DIR / "user_velocity.csv"

RUNTIME_VELOCITY_STATE_PATH = RUNTIME_DIR / "user_velocity_state.csv"

ONBOARDING_RISK_SNAPSHOT_PATH = PROCESSED_DIR / "onboarding" / "account_risk_snapshot.csv"

ONBOARDING_DECISIONS_AUDIT_PATH = AUDIT_DIR / "onboarding_decisions.csv"

TRAINING_GRAPH_FEATURES_PATH = TRAINING_DIR / "graph_features.csv"

POLICY_RULES_PATH = REFERENCE_DIR / "policy_rules.json"

LOGS_DIR = BASE_DIR / "logs"

ALL_STORAGE_DIRS = [
    DATA_DIR,
    PROCESSED_DIR,
    TRAINING_DIR,
    RUNTIME_DIR,
    ALERTS_DIR,
    REPORTS_DIR,
    CASES_DIR,
    AUDIT_DIR,
    EXPLAINABILITY_DIR,
    REFERENCE_DIR,
    ARCHIVE_DIR,
    LOGS_DIR,
]


def initialize_storage_directories() -> None:
    for directory in ALL_STORAGE_DIRS:
        try:
            directory.mkdir(parents=True, exist_ok=True)
        except Exception:
            # best-effort, don't raise during initialize
            pass
