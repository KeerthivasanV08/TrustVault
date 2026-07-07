"""
Enterprise LSTM model rebuild and conversion.

Approach:
1. Load the legacy H5 model that still carries the original architecture.
2. Save a native .keras artifact with the current TensorFlow/Keras runtime.
3. Verify the migrated model with a dummy inference.
"""

import logging
import sys
import tempfile
from pathlib import Path

import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).resolve().parents[1]
KERAS_PATH = BACKEND_DIR / "app" / "models" / "transaction" / "lstm_sequence_model.keras"
LEGACY_H5_PATH = BACKEND_DIR / "app" / "models" / "transaction" / "lstm_sequence_model.h5"


def _save_native_keras(model, target_path: Path) -> Path:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{target_path.stem}.", suffix=target_path.suffix, dir=str(target_path.parent))
    import os

    os.close(fd)
    temp_path = Path(temp_name)
    if temp_path.exists():
        temp_path.unlink()

    model.save(temp_path)
    temp_path.replace(target_path)
    return target_path


def main():
    import tensorflow as tf
    
    logger.info("=" * 80)
    logger.info("ENTERPRISE LSTM MODEL CONVERSION")
    logger.info("=" * 80)
    source_path = LEGACY_H5_PATH if LEGACY_H5_PATH.exists() else KERAS_PATH
    logger.info(f"Source: {source_path}")
    logger.info(f"TensorFlow: {tf.__version__}")
    
    # Step 1: Load legacy model
    logger.info("\nStep 1: Loading legacy model...")
    try:
        model = tf.keras.models.load_model(source_path, compile=False)
        logger.info("[OK] Model loaded")
    except Exception as e:
        logger.error(f"[FAILED] Could not load: {e}")
        return 1
    
    # Step 2: Self-test
    logger.info("\nStep 2: Self-testing loaded model...")
    try:
        dummy = np.random.randn(1, 10, 5).astype(np.float32)
        pred = model.predict(dummy, verbose=0)
        logger.info(f"[OK] Inference works (prediction: {float(pred[0, 0]):.4f})")
    except Exception as e:
        logger.error(f"[FAILED] Inference error: {e}")
        return 1
    
    # Step 3: Re-compile model for proper serialization
    logger.info("\nStep 3: Recompiling model for serialization...")
    try:
        model.compile(
            optimizer='adam',
            loss='binary_crossentropy',
            metrics=['accuracy']
        )
        logger.info("[OK] Model recompiled")
    except Exception as e:
        logger.warning(f"Recompile warning: {e}")
    
    # Step 4: Save as native .keras
    logger.info(f"\nStep 4: Saving native .keras to {KERAS_PATH}...")
    try:
        if KERAS_PATH.exists():
            backup_path = KERAS_PATH.with_name(f"{KERAS_PATH.stem}.backup{KERAS_PATH.suffix}")
            if backup_path.exists():
                backup_path.unlink()
            KERAS_PATH.replace(backup_path)
            logger.info(f"[OK] Original backed up to {backup_path}")

        _save_native_keras(model, KERAS_PATH)
        logger.info(f"[OK] Saved to {KERAS_PATH} ({KERAS_PATH.stat().st_size / 1e6:.2f} MB)")
    except Exception as e:
        logger.error(f"[FAILED] Conversion failed: {e}")
        return 1
    
    # Step 5: Final verification
    logger.info("\nStep 5: Final verification...")
    try:
        final_model = tf.keras.models.load_model(KERAS_PATH, compile=False)
        dummy = np.random.randn(1, 10, 5).astype(np.float32)
        pred = final_model.predict(dummy, verbose=0)
        logger.info(f"[OK] Final model loads and works (prediction: {float(pred[0, 0]):.4f})")
    except Exception as e:
        logger.error(f"[FAILED] Final verification failed: {e}")
        return 1
    
    logger.info("\n" + "=" * 80)
    logger.info("[SUCCESS] LSTM model conversion complete")
    logger.info("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(main())
