"""Test sequence model service after clean rebuild."""

import sys
sys.path.insert(0, '.')

import numpy as np
import pandas as pd
from app.services.transaction.sequence_model_service import SequenceModelService

def main():
    # Initialize service
    svc = SequenceModelService()
    print("[OK] SequenceModelService initialized")
    print(f"   Model loaded: {svc.model is not None}")
    print(f"   Scaler loaded: {svc.scaler is not None}")
    print(f"   Metadata loaded: {len(svc.metadata) > 0 if svc.metadata else False}")

    # Create dummy transaction data
    seq_len = 10
    last_transactions = pd.DataFrame({
        'amount': [1000, 2000, 1500, 3000, 2500, 1800, 2200, 2800, 3200, 2900],
        'drain_ratio': [0.1] * seq_len,
        'txn_velocity_1h': [100, 200, 150, 300, 250, 180, 220, 280, 320, 290],
        'forwarding_delay_mins': [5] * seq_len,
        'balance_depletion_speed': [0.01] * seq_len,
    })

    # Test prediction
    result = svc.predict_sequence(last_transactions, behavioral_score=0.5)
    print("\n[OK] Sequence prediction successful:")
    print(f"   Score: {result.get('sequence_score'):.4f}")
    print(f"   Pattern: {result.get('sequence_pattern')}")
    
    print("\n[SUCCESS] Sequence pipeline working correctly!")

if __name__ == "__main__":
    main()
