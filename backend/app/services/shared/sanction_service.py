# backend/app/services/sanction_service.py

import pandas as pd

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[4]

SANCTION_PATH = (
    BASE_DIR /
    "data" /
    "reference" /
    "sanction_list.csv"
)


class SanctionService:

    def __init__(self):

        try:

            self.df = pd.read_csv(
                SANCTION_PATH
            )

        except:

            self.df = pd.DataFrame()

    def is_sanctioned(
        self,
        full_name
    ):

        if self.df.empty:
            return False

        return (
            full_name.upper()
            in
            self.df["entity_name"]
            .str.upper()
            .values
        )