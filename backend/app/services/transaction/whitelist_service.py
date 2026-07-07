# backend/app/services/whitelist_service.py

import pandas as pd

from pathlib import Path


# =====================================================
# PATH CONFIG
# =====================================================

BASE_DIR = Path(__file__).resolve().parents[4]

WHITELIST_PATH = (
    BASE_DIR /
    "data" /
    "processed" /
    "whitelist.csv"
)


# =====================================================
# WHITELIST SERVICE
# =====================================================

class WhitelistService:

    def __init__(self):

        # ---------------------------------------------
        # LOAD WHITELIST SAFELY
        # ---------------------------------------------

        try:

            self.df = pd.read_csv(
                WHITELIST_PATH
            )

            if "user_id" not in self.df.columns:

                self.df = pd.DataFrame(
                    columns=["user_id"]
                )

        except Exception:

            self.df = pd.DataFrame(
                columns=["user_id"]
            )

        # ---------------------------------------------
        # PERFORMANCE OPTIMIZATION
        # O(1) LOOKUP SET
        # ---------------------------------------------

        self.whitelist_set = set(

            self.df["user_id"]
            .astype(str)
            .dropna()
            .unique()
        )

    # =================================================
    # CHECK WHITELIST STATUS
    # =================================================

    def is_whitelisted(

        self,
        user_id

    ):

        # ---------------------------------------------
        # EMPTY SAFETY
        # ---------------------------------------------

        if not self.whitelist_set:
            return False

        # ---------------------------------------------
        # NULL SAFETY
        # ---------------------------------------------

        if pd.isna(user_id):
            return False

        # ---------------------------------------------
        # O(1) LOOKUP
        # ---------------------------------------------

        return str(user_id) in self.whitelist_set

    # =================================================
    # OPTIONAL: GET FULL RECORD
    # =================================================

    def get_whitelist_record(

        self,
        user_id

    ):

        if self.df.empty:
            return None

        record = self.df[

            self.df["user_id"]
            .astype(str)

            == str(user_id)
        ]

        if record.empty:
            return None

        return record.iloc[0].to_dict()