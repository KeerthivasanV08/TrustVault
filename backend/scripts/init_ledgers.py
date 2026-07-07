# backend/scripts/init_ledgers.py

import pandas as pd
from pathlib import Path


# ---------------------------------------------------
# PATH CONFIG
# ---------------------------------------------------
BASE_DIR = Path(__file__).resolve().parents[2]

PROCESSED_DIR = BASE_DIR / "data" / "processed"


def init():

    # ---------------------------------------------------
    # CREATE DIRECTORY
    # ---------------------------------------------------
    PROCESSED_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # ---------------------------------------------------
    # 1. SIM REGISTRY
    # ---------------------------------------------------
    pd.DataFrame(columns=[

        "user_id",

        "registered_imsi",

        "device_id",

        "first_seen_ts",

        "last_seen_ts",

        "trust_score",

        "is_verified",

        "binding_expiry",

        "updated_at"

    ]).to_csv(
        PROCESSED_DIR / "sim_registry.csv",
        index=False
    )

    # ---------------------------------------------------
    # 2. CONTROL DECISIONS
    # ---------------------------------------------------
    pd.DataFrame(columns=[

        "decision_id",

        "entity_id",

        "entity_type",

        "risk_score",

        "requires_block",

        "requires_edd",

        "control_reason",

        "status",

        "created_at",

        "updated_at"

    ]).to_csv(
        PROCESSED_DIR / "control_decisions.csv",
        index=False
    )

    # ---------------------------------------------------
    # 3. WHITELIST
    # ---------------------------------------------------
    pd.DataFrame(columns=[

        "user_id",

        "entity_type",

        "added_at",

        "reason_for_whitelist"

    ]).to_csv(
        PROCESSED_DIR / "whitelist.csv",
        index=False
    )

    # ---------------------------------------------------
    # 4. ONBOARDING RESULTS
    # ---------------------------------------------------
    pd.DataFrame(columns=[

        "user_id",

        "onboarding_ml_risk",

        "final_risk_score",

        "risk_level",

        "requires_review",

        "control_reason",

        "created_at"

    ]).to_csv(
        PROCESSED_DIR / "onboarding_results.csv",
        index=False
    )

    # ---------------------------------------------------
    # 5. ALERTS
    # ---------------------------------------------------
    pd.DataFrame(columns=[

        "alert_id",

        "user_id",

        "entity_type",

        "risk_score",

        "alert_priority",

        "status"

    ]).to_csv(
        PROCESSED_DIR / "alerts.csv",
        index=False
    )

    # ---------------------------------------------------
    # 6. EXPLAINABILITY LOG
    # ---------------------------------------------------
    pd.DataFrame(columns=[

        "entity_id",

        "ml_score",

        "graph_score",

        "identity_score",

        "flags",

        "reasons",

        "created_at"

    ]).to_csv(
        PROCESSED_DIR / "explainability_log.csv",
        index=False
    )

    print("✅ All AML Persistence Ledgers Initialized")

    print(
        f"📍 Storage Location: {PROCESSED_DIR.absolute()}"
    )


if __name__ == "__main__":
    init()