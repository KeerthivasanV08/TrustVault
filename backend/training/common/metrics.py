# training/common/metrics.py

import numpy as np

from sklearn.metrics import (

    accuracy_score,

    precision_score,

    recall_score,

    f1_score,

    roc_auc_score,

    confusion_matrix,

    classification_report,

    average_precision_score
)


def evaluate_binary_model(

    y_true,

    y_pred,

    y_prob=None,

    model_name="MODEL"
):

    print(f"\n========== {model_name} METRICS ==========\n")

    accuracy = accuracy_score(
        y_true,
        y_pred
    )

    precision = precision_score(
        y_true,
        y_pred,
        zero_division=0
    )

    recall = recall_score(
        y_true,
        y_pred,
        zero_division=0
    )

    f1 = f1_score(
        y_true,
        y_pred,
        zero_division=0
    )

    print(f"Accuracy  : {accuracy:.4f}")
    print(f"Precision : {precision:.4f}")
    print(f"Recall    : {recall:.4f}")
    print(f"F1 Score  : {f1:.4f}")

    if y_prob is not None:

        roc_auc = roc_auc_score(
            y_true,
            y_prob
        )

        pr_auc = average_precision_score(
            y_true,
            y_prob
        )

        print(f"ROC AUC   : {roc_auc:.4f}")
        print(f"PR AUC    : {pr_auc:.4f}")

    print("\n========== CLASSIFICATION REPORT ==========\n")

    print(
        classification_report(
            y_true,
            y_pred
        )
    )

    print("\n========== CONFUSION MATRIX ==========\n")

    print(
        confusion_matrix(
            y_true,
            y_pred
        )
    )