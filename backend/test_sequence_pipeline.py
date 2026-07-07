"""Test script for sequence model service pipeline."""

import sys
sys.path.insert(0, '.')

import numpy as np
import pandas as pd
from app.services.transaction.sequence_model_service import SequenceModelService

def main():
    # Initialize service
    svc = SequenceModelService()
    print("✅ SequenceModelService initialized")
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
        'timestamp': pd.date_range('2026-01-01', periods=seq_len, freq='H')
    })

    # Test prediction
    result = svc.predict_sequence(last_transactions, behavioral_score=0.5)
    print("\n✅ Sequence prediction successful:")
    print(f"   Score: {result.get('sequence_score'):.4f}")
    print(f"   Pattern: {result.get('sequence_pattern')}")
    
    # Test with high-risk behavior
    high_risk_txns = pd.DataFrame({
        'amount': [50000, 55000, 52000, 58000, 60000, 62000, 65000, 68000, 70000, 72000],
        'drain_ratio': [0.5] * seq_len,
        'txn_velocity_1h': [15000, 16000, 14000, 17000, 18000, 19000, 20000, 21000, 22000, 23000],
        'forwarding_delay_mins': [1] * seq_len,
        'balance_depletion_speed': [0.1] * seq_len,
        'timestamp': pd.date_range('2026-01-01', periods=seq_len, freq='H')
    })
    
    result_high_risk = svc.predict_sequence(high_risk_txns, behavioral_score=0.9)
    print("\n✅ High-risk prediction successful:")
    print(f"   Score: {result_high_risk.get('sequence_score'):.4f}")
    print(f"   Pattern: {result_high_risk.get('sequence_pattern')}")
    
    print("\n✅ SEQUENCE PIPELINE VALIDATION COMPLETE")

if __name__ == "__main__":
    main()
