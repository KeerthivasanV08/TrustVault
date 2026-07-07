"""Complete end-to-end AML pipeline test with sequence model."""

import sys
sys.path.insert(0, '.')

import numpy as np
import pandas as pd
import json
from pathlib import Path

print("\n" + "=" * 80)
print("TRUSTVALUT AML PLATFORM - END-TO-END VERIFICATION")
print("=" * 80)

# Step 1: Model Loading
print("\n[STEP 1] Model Loading & Initialization")
print("-" * 80)

from app.core.model_loader import initialize_model_runtime

health = initialize_model_runtime()
runtime_mode = health.get("runtime_mode")
print(f"[OK] Runtime Mode: {runtime_mode}")

models_status = {
    'Behavioral': health.get('behavioral_model'),
    'Sequence': health.get('sequence_model'),
    'Graph': health.get('graph_engine'),
}

for model_name, status in models_status.items():
    icon = "[OK]" if status == "healthy" else "[FAIL]"
    print(f"   {icon} {model_name} Model: {status}")

if health.get('sequence_self_test', {}).get('state') == 'healthy':
    pred = health['sequence_self_test'].get('prediction', 'N/A')
    print(f"   [OK] Sequence Self-Test: PASSED (prediction={pred:.4f})")
else:
    print(f"   [FAIL] Sequence Self-Test: FAILED")

# Step 2: Sequence Model Service
print("\n[STEP 2] Sequence Model Service")
print("-" * 80)

from app.services.transaction.sequence_model_service import SequenceModelService

seq_service = SequenceModelService()
print(f"[OK] Service initialized")
print(f"   Model: {seq_service.model is not None}")
print(f"   Scaler: {seq_service.scaler is not None}")
print(f"   Metadata loaded: {len(seq_service.metadata) > 0 if seq_service.metadata else False}")

# Step 3: Sample Inference
print("\n[STEP 3] Sample Inference")
print("-" * 80)

normal_txns = pd.DataFrame({
    'amount': [1000, 1200, 1100, 1050, 1150] * 2,
    'drain_ratio': [0.1] * 10,
    'txn_velocity_1h': [50, 60, 55, 52, 58] * 2,
    'forwarding_delay_mins': [5] * 10,
    'balance_depletion_speed': [0.01] * 10,
})

result_normal = seq_service.predict_sequence(normal_txns, behavioral_score=0.2)
print(f"Normal Pattern:")
print(f"   Score: {result_normal['sequence_score']:.4f}")
print(f"   Pattern: {result_normal['sequence_pattern']}")

suspicious_txns = pd.DataFrame({
    'amount': [50000, 55000, 52000, 58000, 60000] * 2,
    'drain_ratio': [0.5] * 10,
    'txn_velocity_1h': [15000, 16000, 14000, 17000, 18000] * 2,
    'forwarding_delay_mins': [1] * 10,
    'balance_depletion_speed': [0.1] * 10,
})

result_suspicious = seq_service.predict_sequence(suspicious_txns, behavioral_score=0.8)
print(f"\nSuspicious Pattern:")
print(f"   Score: {result_suspicious['sequence_score']:.4f}")
print(f"   Pattern: {result_suspicious['sequence_pattern']}")

# Step 4: Environment Info
print("\n[STEP 4] Environment & Dependencies")
print("-" * 80)

versions = health.get('versions', {})
critical_versions = {
    'TensorFlow': versions.get('tensorflow', 'unknown'),
    'Keras': versions.get('keras', 'unknown'),
    'NumPy': versions.get('numpy', 'unknown'),
    'Pandas': versions.get('pandas', 'unknown'),
}

for dep, version in critical_versions.items():
    print(f"   {dep}: {version}")

# Step 5: Model Artifacts
print("\n[STEP 5] Model Artifacts")
print("-" * 80)

from app.core.model_loader import get_model_loader
loader = get_model_loader()

models_dir = Path("app/models/transaction")
keras_model_path = models_dir / "lstm_sequence_model.keras"
h5_model_path = models_dir / "lstm_sequence_model.h5"

print(f"   Sequence Model (modern): {keras_model_path.exists()}")
if keras_model_path.exists():
    size_mb = keras_model_path.stat().st_size / 1e6
    print(f"      [OK] exists ({size_mb:.2f} MB)")

print(f"   Sequence Model (legacy): {h5_model_path.exists()}")
if h5_model_path.exists():
    size_mb = h5_model_path.stat().st_size / 1e6
    print(f"      [WARN] exists ({size_mb:.2f} MB) - should be migrated")

# Final Summary
print("\n" + "=" * 80)
print("VERIFICATION SUMMARY")
print("=" * 80)

all_healthy = (
    runtime_mode == "FULL" and
    all(status == "healthy" for status in models_status.values()) and
    health.get('sequence_self_test', {}).get('state') == 'healthy' and
    keras_model_path.exists()
)

if all_healthy:
    print("[OK] SYSTEM STATUS: OPERATIONAL")
    print("\n[OK] Sequence Model: ACTIVE")
    print("[OK] Sequence Intelligence: ENABLED")
    print("[OK] AML Fusion Scoring: READY")
    print("[OK] End-to-End Pipeline: VERIFIED")
else:
    print("[FAIL] SYSTEM STATUS: DEGRADED")
    issues = []
    if runtime_mode != "FULL":
        issues.append(f"- Runtime mode: {runtime_mode} (expected: FULL)")
    for model_name, status in models_status.items():
        if status != "healthy":
            issues.append(f"- {model_name} model: {status}")
    if health.get('sequence_self_test', {}).get('state') != 'healthy':
        issues.append("- Sequence self-test failed")
    if not keras_model_path.exists():
        issues.append("- Modern sequence model format missing")
    for issue in issues:
        print(issue)

print("\n" + "=" * 80)
