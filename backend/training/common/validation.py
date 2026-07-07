# training/common/validation.py

import pandas as pd


def validate_dataframe(df):

    if df.empty:
        raise ValueError(
            "Dataset is empty"
        )

    duplicate_count = df.duplicated().sum()

    print(
        f"Duplicates: {duplicate_count}"
    )

    missing = df.isnull().sum().sum()

    print(
        f"Missing Values: {missing}"
    )

    return True