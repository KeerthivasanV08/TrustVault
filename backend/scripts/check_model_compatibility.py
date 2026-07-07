from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.feature_schema import BEHAVIOR_FEATURE_ORDER, BEHAVIOR_NUMERIC_FEATURES, SEQUENCE_FEATURES
from app.core.model_loader import get_model_loader


def _print_header() -> None:
    print("====================================")
    print("MODEL COMPATIBILITY REPORT")
    print("====================================")


def _format_state(name: str, state: str, reason: str | None = None) -> None:
    icon = "✔" if state == "healthy" else "❌"
    print(f"{name}: {icon} {state.upper()}")
    if reason:
        print(f"  Reason: {reason}")


def _behavioral_probe(loader) -> str:
    model, scaler, schema = loader.get_behavioral_model()
    if model is None or scaler is None:
        return "unavailable"

    columns = BEHAVIOR_FEATURE_ORDER
    frame = pd.DataFrame([{column: 0 for column in columns}])
    frame["transaction_type"] = pd.Series(["UPI"], dtype="category")
    frame["channel"] = pd.Series(["Web"], dtype="category")
    num_cols = [col for col in BEHAVIOR_NUMERIC_FEATURES if col in frame.columns]
    frame[num_cols] = scaler.transform(frame[num_cols])
    prediction = model.predict_proba(frame)[0][1]
    return f"prediction_ok ({float(prediction):.4f})"


def _sequence_probe(loader) -> str:
    model, scaler, metadata = loader.get_sequence_model()
    if model is None or scaler is None:
        return "unavailable"

    seq_len = int((metadata or {}).get("sequence_length", 10))
    rows = []
    for _ in range(seq_len):
        rows.append({feature: 1.0 for feature in SEQUENCE_FEATURES})
    frame = pd.DataFrame(rows)
    frame[SEQUENCE_FEATURES] = scaler.transform(frame[SEQUENCE_FEATURES])
    import numpy as np

    tensor = np.expand_dims(frame.values[-seq_len:], 0)
    prediction = model.predict(tensor, verbose=0)
    return f"prediction_ok ({float(prediction[0][0]):.4f})"


def main() -> int:
    _print_header()
    loader = get_model_loader()
    health = loader.initialize_runtime()

    print()
    _format_state("Behavioral Model", health.get("behavioral_model", "failed"), health.get("artifacts", {}).get("behavioral_model", {}).get("reason"))
    _format_state("Sequence Model", health.get("sequence_model", "failed"), health.get("artifacts", {}).get("sequence_model", {}).get("reason"))
    _format_state("Graph Engine", health.get("graph_engine", "failed"), health.get("artifacts", {}).get("graph_engine", {}).get("reason"))
    _format_state("Scalers", health.get("scalers", "failed"))
    _format_state("Encoders", health.get("encoders", "failed"))

    print()
    print("Runtime Versions:")
    print(json.dumps(health.get("versions", {}), indent=2))

    print()
    print("Validation Probes:")
    print(f"Behavioral: {_behavioral_probe(loader)}")
    print(f"Sequence: {_sequence_probe(loader)}")

    print()
    print(f"Runtime mode: {health.get('runtime_mode')}")
    return 0 if health.get("runtime_mode") == "FULL" else 2


if __name__ == "__main__":
    raise SystemExit(main())