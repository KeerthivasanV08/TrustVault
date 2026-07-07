# training/common/imbalance_handler.py

from imblearn.over_sampling import SMOTE


def apply_smote(X, y):

    smote = SMOTE(
        sampling_strategy=0.3,
        random_state=42
    )

    X_resampled, y_resampled = smote.fit_resample(
        X,
        y
    )

    return X_resampled, y_resampled