"""
Legacy TensorFlow/Keras model repair for LSTM sequence models.

This script handles migration of legacy H5 models saved with older keras
to modern TensorFlow 2.13+ format (.keras).

Enterprise-grade features:
- Manual architecture reconstruction
- Config patching for compatibility
- Weights reloading with validation
- Self-test before saving
- Comprehensive logging
"""

from __future__ import annotations

import json
import logging
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict

import h5py
import numpy as np

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

LEGACY_MODEL_PATH = BACKEND_DIR / "app" / "models" / "transaction" / "lstm_sequence_model.h5"
FIXED_MODEL_PATH = BACKEND_DIR / "app" / "models" / "transaction" / "lstm_sequence_model.keras"


def _strip_unsupported_fields(payload: Any) -> Any:
    """Recursively remove fields unsupported by modern Keras."""
    if isinstance(payload, dict):
        cleaned = {}
        for key, value in payload.items():
            # Remove time_major (deprecated in modern Keras)
            if key == "time_major":
                logger.debug(f"Removing unsupported field: {key}")
                continue
            # Remove batch_input_shape in old format (use input_shape instead)
            if key == "batch_input_shape":
                logger.debug(f"Removing unsupported field: {key}")
                continue
            cleaned[key] = _strip_unsupported_fields(value)
        return cleaned
    if isinstance(payload, list):
        return [_strip_unsupported_fields(item) for item in payload]
    return payload


def _read_model_config(path: Path) -> dict:
    """Read model_config from legacy H5 file."""
    logger.info(f"Reading model config from {path}")
    try:
        with h5py.File(path, "r") as handle:
            raw = handle.attrs.get("model_config")
            if raw is None:
                raise ValueError(f"Missing model_config attribute in {path}")
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            config = json.loads(raw)
            logger.info("✅ Model config successfully read from H5")
            return config
    except Exception as exc:
        logger.error(f"❌ Failed to read model config: {exc}")
        raise


def _reconstruct_model_manually() -> Any:
    """
    Manually reconstruct the known LSTM architecture.
    
    Architecture:
    - Input: (10, 5) [sequence_length=10, num_features=5]
    - LSTM(64, return_sequences=True)
    - Dropout(0.3)
    - BatchNormalization()
    - LSTM(32)
    - Dropout(0.3)
    - Dense(32, activation='relu')
    - Dense(1, activation='sigmoid')
    """
    import tensorflow as tf

    logger.info("Reconstructing LSTM architecture manually...")
    
    try:
        model = tf.keras.models.Sequential([
            tf.keras.layers.Input(shape=(10, 5), name="transaction_sequence_input"),
            tf.keras.layers.LSTM(
                64,
                return_sequences=True,
            ),
            tf.keras.layers.Dropout(0.3),
            tf.keras.layers.BatchNormalization(),
            tf.keras.layers.LSTM(32),
            tf.keras.layers.Dropout(0.3),
            tf.keras.layers.Dense(32, activation='relu'),
            tf.keras.layers.Dense(1, activation='sigmoid'),
        ])
        
        model.compile(
            optimizer='adam',
            loss='binary_crossentropy',
            metrics=['accuracy']
        )
        
        logger.info("✅ Manual model reconstruction successful")
        logger.info(f"Model architecture:")
        model.summary()
        return model
        
    except Exception as exc:
        logger.error(f"❌ Failed to reconstruct model: {exc}")
        raise


def _load_weights_from_h5(model: Any, path: Path) -> None:
    """Load weights from legacy H5 file into reconstructed model."""
    logger.info(f"Loading weights from {path}...")
    try:
        model.load_weights(path)
        logger.info("✅ Weights loaded successfully")
    except Exception as exc:
        logger.error(f"❌ Failed to load weights: {exc}")
        raise


def _self_test_model(model: Any) -> bool:
    """
    Run a dummy inference to validate model health.
    
    Returns:
        True if inference successful, False otherwise
    """
    logger.info("Running model self-test...")
    try:
        # Create dummy input: batch_size=1, seq_len=10, num_features=5
        dummy_input = np.random.randn(1, 10, 5).astype(np.float32)
        
        # Run inference
        prediction = model.predict(dummy_input, verbose=0)
        
        # Validate output
        if prediction.shape != (1, 1):
            raise ValueError(f"Unexpected prediction shape: {prediction.shape}, expected (1, 1)")
        
        if not (0.0 <= float(prediction[0, 0]) <= 1.0):
            raise ValueError(f"Prediction outside [0, 1]: {prediction[0, 0]}")
        
        logger.info(f"✅ Self-test passed. Sample prediction: {float(prediction[0, 0]):.4f}")
        return True
        
    except Exception as exc:
        logger.error(f"❌ Self-test failed: {exc}")
        return False


def _try_direct_load(path: Path) -> Any:
    """
    Try direct H5 load with tensorflow.keras first.
    
    Returns model if successful, None if fails.
    """
    import tensorflow as tf
    
    logger.info("Attempting direct model load...")
    try:
        model = tf.keras.models.load_model(path, compile=False)
        logger.info("✅ Direct load successful")
        return model
    except Exception as exc:
        logger.warning(f"⚠️ Direct load failed (expected for legacy models): {exc}")
        return None


def _try_patched_json_load(path: Path) -> Any:
    """
    Try loading via model_from_json with config patching.
    
    Returns model if successful, None if fails.
    """
    import tensorflow as tf
    
    logger.info("Attempting JSON config load with patching...")
    try:
        config = _read_model_config(path)
        patched_config = _strip_unsupported_fields(config)
        
        model = tf.keras.models.model_from_json(json.dumps(patched_config))
        _load_weights_from_h5(model, path)
        
        logger.info("✅ Patched JSON load successful")
        return model
    except Exception as exc:
        logger.warning(f"⚠️ Patched JSON load failed: {exc}")
        return None


def repair_and_migrate(source_path: Path, target_path: Path) -> bool:
    """
    Complete legacy model repair and migration pipeline.
    
    Args:
        source_path: Path to legacy H5 model
        target_path: Path to save modernized .keras model
        
    Returns:
        True if successful, False otherwise
    """
    import tensorflow as tf
    
    logger.info("=" * 70)
    logger.info("LEGACY LSTM MODEL REPAIR AND MIGRATION")
    logger.info("=" * 70)
    logger.info(f"Source: {source_path}")
    logger.info(f"Target: {target_path}")
    logger.info(f"TensorFlow Version: {tf.__version__}")
    
    # Step 1: Verify source exists
    if not source_path.exists():
        logger.error(f"❌ Source model not found: {source_path}")
        return False
    
    logger.info(f"✅ Source model exists ({source_path.stat().st_size / 1e6:.2f} MB)")
    
    # Step 2: Try direct load first (cheapest option)
    model = _try_direct_load(source_path)
    
    # Step 3: Try patched JSON load (config extraction + patching)
    if model is None:
        model = _try_patched_json_load(source_path)
    
    # Step 4: Manual reconstruction if all else fails
    if model is None:
        logger.warning("⚠️ Falling back to manual model reconstruction...")
        model = _reconstruct_model_manually()
        _load_weights_from_h5(model, source_path)
    
    if model is None:
        logger.error("❌ All loading strategies failed")
        return False
    
    # Step 5: Self-test
    if not _self_test_model(model):
        logger.error("❌ Model failed self-test")
        return False
    
    # Step 6: Save in modern format
    logger.info(f"Saving modernized model to {target_path}...")
    try:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=f".{target_path.stem}.", suffix=target_path.suffix, dir=str(target_path.parent))
        import os

        os.close(fd)
        temp_path = Path(temp_name)
        if temp_path.exists():
            temp_path.unlink()

        model.save(temp_path)
        temp_path.replace(target_path)
        logger.info(f"✅ Model saved successfully ({target_path.stat().st_size / 1e6:.2f} MB)")
    except Exception as exc:
        logger.error(f"❌ Failed to save model: {exc}")
        return False
    
    # Step 7: Verify saved model loads
    logger.info("Verifying saved model...")
    try:
        verify_model = tf.keras.models.load_model(target_path, compile=False)
        logger.info("✅ Saved model loads successfully")
        
        if _self_test_model(verify_model):
            logger.info("✅ Saved model passes self-test")
        else:
            logger.warning("⚠️ Saved model self-test failed")
            return False
            
    except Exception as exc:
        logger.error(f"❌ Failed to verify saved model: {exc}")
        return False
    
    logger.info("=" * 70)
    logger.info("✅ LEGACY MODEL REPAIR COMPLETED SUCCESSFULLY")
    logger.info("=" * 70)
    return True


def main() -> int:
    """Main entry point."""
    try:
        success = repair_and_migrate(LEGACY_MODEL_PATH, FIXED_MODEL_PATH)
        return 0 if success else 1
    except Exception as exc:
        logger.error(f"❌ Unhandled exception: {exc}", exc_info=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
