# backend/app/core/policy_engine.py

POLICY_RULES = {

    # RBI / NPCI
    "NEW_USER_UPI_LIMIT": 5000,
    "DAILY_UPI_LIMIT": 100000,

    # Income Tax / PAN
    "PAN_MANDATORY_LIMIT": 50000,

    # SFT / CTR
    "SAVINGS_SFT_LIMIT": 1000000,
    "CURRENT_SFT_LIMIT": 5000000,
    "CTR_LIMIT": 1000000,

    # I4C
    "MULE_HUB_THRESHOLD": 3,

    # Dormancy
    "DORMANCY_DAYS": 180,

    # Geo Risk
    "GEO_LIMIT": 25000,

    # International
    "LRS_LIMIT": 250000
}