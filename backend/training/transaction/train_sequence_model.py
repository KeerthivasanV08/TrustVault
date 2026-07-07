# training/transaction/train_sequence_model.py

import joblib
import numpy as np
import pandas as pd

from pathlib import Path

from sklearn.preprocessing import MinMaxScaler

from sklearn.model_selection import (
    train_test_split
)

from sklearn.metrics import (
    classification_report,
    confusion_matrix
)

from tensorflow.keras.models import Sequential

from tensorflow.keras.layers import (
    Input,
    LSTM,
    Dense,
    Dropout,
    BatchNormalization
)

from tensorflow.keras.callbacks import (
    EarlyStopping
)

ROOT_DIR = Path(__file__).resolve().parents[3]
BACKEND_DIR = Path(__file__).resolve().parents[2]

DATASET_PATH = ROOT_DIR / "data" / "processed" / "final_dataset.csv"

MODEL_DIR = BACKEND_DIR / "app" / "models" / "transaction"

MODEL_DIR.mkdir(parents=True, exist_ok=True)

MODEL_PATH = (
    MODEL_DIR
    / "lstm_sequence_model.keras"
)

LEGACY_MODEL_PATH = (
    MODEL_DIR
    / "lstm_sequence_model.h5"
)

SCALER_PATH = (
    MODEL_DIR
    / "sequence_scaler.pkl"
)

SEQUENCE_METADATA = (
    MODEL_DIR
    / "sequence_model_metadata.pkl"
)

SEQUENCE_LENGTH = 10

FEATURES = [

    "amount",

    "drain_ratio",

    "txn_velocity_1h",

    "forwarding_delay_mins",

    "balance_depletion_speed"
]


def select_sequence_group_column(df):

    candidate_columns = [
        "sender_id",
        "receiver_id"
    ]

    best_column = None
    best_count = 0

    for column in candidate_columns:

        if column not in df.columns:
            continue

        qualifying_groups = (
            df.groupby(column)
            .size()
            .ge(SEQUENCE_LENGTH)
            .sum()
        )

        if qualifying_groups > best_count:
            best_count = qualifying_groups
            best_column = column

    return best_column, best_count


def create_sequences_per_user(

    df,

    scaler,

    group_column
):

    X = []

    y = []

    users_processed = 0

    for entity_id, group in df.groupby(group_column):

        group = group.sort_values(
            by="timestamp"
        )

        if len(group) < SEQUENCE_LENGTH:
            continue

        group_features = group[FEATURES]

        group_scaled = scaler.transform(
            group_features
        )

        labels = (
            group["is_fraud"]
            .values
        )

        for i in range(

            len(group_scaled)
            - SEQUENCE_LENGTH
        ):

            X.append(

                group_scaled[
                    i:i + SEQUENCE_LENGTH
                ]
            )

            y.append(

                labels[
                    i + SEQUENCE_LENGTH
                ]
            )

        users_processed += 1

    print(
        f"✅ Users Processed: {users_processed}"
    )

    return np.array(X), np.array(y)


def train():

    print(
        "\n🚀 TRAINING LSTM SEQUENCE MODEL...\n"
    )

    df = pd.read_csv(
        DATASET_PATH
    )

    df = df.sort_values(
        by="timestamp"
    )

    print(
        f"✅ Dataset Loaded: {len(df)} rows"
    )

    # -----------------------------------
    # CLEAN
    # -----------------------------------

    df = df.dropna(
        subset=FEATURES + ["is_fraud"]
    )

    group_column, qualifying_groups = select_sequence_group_column(
        df
    )

    if group_column is None or qualifying_groups == 0:

        raise ValueError(
            "No sequence grouping column has enough repeated events to build windows."
        )

    print(
        f"✅ Using {group_column} for sequences ({qualifying_groups} groups with >= {SEQUENCE_LENGTH} rows)"
    )

    # -----------------------------------
    # SCALER
    # -----------------------------------

    scaler = MinMaxScaler()

    scaler.fit(
        df[FEATURES]
    )

    joblib.dump(
        scaler,
        SCALER_PATH
    )

    print(
        "✅ sequence_scaler.pkl saved"
    )

    # -----------------------------------
    # CREATE SEQUENCES
    # -----------------------------------

    X, y = create_sequences_per_user(

        df,

        scaler,

        group_column
    )

    if len(X) == 0:

        raise ValueError(
            f"Sequence generation produced 0 samples using {group_column}."
        )

    print(
        f"✅ Sequence Shape: {X.shape}"
    )

    # -----------------------------------
    # SPLIT
    # -----------------------------------

    X_train, X_test, y_train, y_test = train_test_split(

        X,

        y,

        test_size=0.2,

        stratify=y,

        random_state=42
    )

    print(
        "✅ Train/Test Split Completed"
    )

    # -----------------------------------
    # MODEL
    # -----------------------------------

    model = Sequential([

        Input(shape=(X_train.shape[1], X_train.shape[2]), name="transaction_sequence_input"),

        LSTM(

            64,

            return_sequences=True,
        ),

        Dropout(0.3),

        BatchNormalization(),

        LSTM(
            32
        ),

        Dropout(0.3),

        Dense(

            32,

            activation="relu"
        ),

        Dense(

            1,

            activation="sigmoid"
        )
    ])

    model.compile(

        optimizer="adam",

        loss="binary_crossentropy",

        metrics=["accuracy"]
    )

    model.summary()

    # -----------------------------------
    # EARLY STOPPING
    # -----------------------------------

    early_stop = EarlyStopping(

        monitor="val_loss",

        patience=3,

        restore_best_weights=True
    )

    # -----------------------------------
    # TRAIN
    # -----------------------------------

    history = model.fit(

        X_train,

        y_train,

        epochs=10,

        batch_size=64,

        validation_split=0.2,

        callbacks=[early_stop],

        verbose=1
    )

    print(
        "✅ LSTM Training Completed"
    )

    # -----------------------------------
    # EVALUATION
    # -----------------------------------

    preds = (
        model.predict(X_test)
        > 0.5
    ).astype(int)

    print("\n========== CLASSIFICATION REPORT ==========")

    print(
        classification_report(
            y_test,
            preds
        )
    )

    print("\n========== CONFUSION MATRIX ==========")

    print(
        confusion_matrix(
            y_test,
            preds
        )
    )

    # -----------------------------------
    # SAVE MODEL
    # -----------------------------------

    model.save(MODEL_PATH)
    model.save(LEGACY_MODEL_PATH)

    metadata = {

        "sequence_length": SEQUENCE_LENGTH,

        "features": FEATURES
    }

    with open(
        SEQUENCE_METADATA,
        "wb"
    ) as f:

        import pickle

        pickle.dump(
            metadata,
            f
        )

    print(
        "\n✅ lstm_sequence_model.keras saved"
    )

    print(
        "✅ lstm_sequence_model.h5 saved"
    )

    print(
        "✅ sequence_model_metadata.pkl saved"
    )

    print(
        "\n🎯 SEQUENCE MODEL TRAINING COMPLETED"
    )


if __name__ == "__main__":
    train()