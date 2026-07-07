"""
Clean rebuild of LSTM model to remove unsupported Keras 3 config arguments.

The .keras file contains legacy layer arguments:
  - batch_input_shape (only valid in H5, not in modern format)
  - time_major (deprecated in LSTM)

Solution: Reconstruct the model manually, then save clean.
"""

import logging
import sys
from pathlib import Path

import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

LEGACY_KERAS_PATH = BACKEND_DIR / "app" / "models" / "transaction" / "lstm_sequence_model.keras"
CLEAN_KERAS_PATH = BACKEND_DIR / "app" / "models" / "transaction" / "lstm_sequence_model_clean.keras"


def rebuild_model_clean():
    """
    Rebuild the LSTM model with clean configuration.
    
    Architecture:
    - Input: (10, 5) [seq_length=10, features=5]
    - LSTM(64, return_sequences=True)
    - Dropout(0.3)
    - BatchNormalization()
    - LSTM(32)
    - Dropout(0.3)
    - Dense(32, activation='relu')
    - Dense(1, activation='sigmoid')
    """
    import tensorflow as tf
    
    logger.info("Rebuilding LSTM model with clean Keras 3 configuration...")
    
    model = tf.keras.Sequential([
        tf.keras.layers.LSTM(64, return_sequences=True, input_shape=(10, 5)),
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
    
    logger.info("✓ Model architecture reconstructed")
    return model


def load_weights_from_legacy(model, legacy_path):
    """Load weights from the legacy .keras model."""
    import tensorflow as tf
    
    logger.info(f"Loading weights from legacy model: {legacy_path}")
    
    try:
        # Load the legacy model to extract weights
        legacy_model = tf.keras.models.load_model(legacy_path, compile=False)
        
        # Copy weights layer by layer
        for src_layer, dst_layer in zip(legacy_model.layers, model.layers):
            if src_layer.weights:
                try:
                    dst_layer.set_weights(src_layer.get_weights())
                    logger.debug(f"Copied weights: {src_layer.name} -> {dst_layer.name}")
                except Exception as e:
                    logger.warning(f"Could not copy weights for {src_layer.name}: {e}")
        
        logger.info("✓ Weights loaded successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to load weights: {e}")
        return False


def self_test_model(model):
    """Run inference self-test."""
    logger.info("Running model self-test...")
    
    try:
        dummy_input = np.random.randn(1, 10, 5).astype(np.float32)
        prediction = model.predict(dummy_input, verbose=0)
        
        if prediction.shape != (1, 1):
            raise ValueError(f"Unexpected shape: {prediction.shape}")
        
        if not (0.0 <= float(prediction[0, 0]) <= 1.0):
            raise ValueError(f"Prediction out of range: {prediction[0, 0]}")
        
        logger.info(f"✓ Self-test passed (prediction: {float(prediction[0, 0]):.4f})")
        return True
    except Exception as e:
        logger.error(f"Self-test failed: {e}")
        return False


def main():
    logger.info("=" * 80)
    logger.info("CLEAN LSTM MODEL REBUILD")
    logger.info("=" * 80)
    logger.info(f"Legacy model: {LEGACY_KERAS_PATH}")
    logger.info(f"Clean model:  {CLEAN_KERAS_PATH}")
    
    # Step 1: Rebuild clean architecture
    model = rebuild_model_clean()
    
    # Step 2: Load weights from legacy
    if not load_weights_from_legacy(model, LEGACY_KERAS_PATH):
        logger.warning("Could not load weights from legacy model")
    
    # Step 3: Self-test
    if not self_test_model(model):
        logger.error("Model failed self-test")
        return 1
    
    # Step 4: Save clean model
    logger.info(f"Saving clean model to {CLEAN_KERAS_PATH}...")
    try:
        CLEAN_KERAS_PATH.parent.mkdir(parents=True, exist_ok=True)
        model.save(CLEAN_KERAS_PATH)
        logger.info(f"✓ Model saved ({CLEAN_KERAS_PATH.stat().st_size / 1e6:.2f} MB)")
    except Exception as e:
        logger.error(f"Failed to save model: {e}")
        return 1
    
    # Step 5: Verify saved model
    logger.info("Verifying saved model...")
    try:
        import tensorflow as tf
        verify_model = tf.keras.models.load_model(CLEAN_KERAS_PATH, compile=False)
        if self_test_model(verify_model):
            logger.info("✓ Saved model loads and works correctly")
        else:
            logger.error("Saved model failed self-test")
            return 1
    except Exception as e:
        logger.error(f"Failed to verify saved model: {e}")
        return 1
    
    # Step 6: Replace original
    logger.info(f"Replacing legacy model with clean version...")
    try:
        LEGACY_KERAS_PATH.unlink()
        CLEAN_KERAS_PATH.rename(LEGACY_KERAS_PATH)
        logger.info(f"✓ Clean model is now primary: {LEGACY_KERAS_PATH}")
    except Exception as e:
        logger.error(f"Failed to replace: {e}")
        return 1
    
    logger.info("=" * 80)
    logger.info("✓ CLEAN LSTM MODEL REBUILD SUCCESSFUL")
    logger.info("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(main())
