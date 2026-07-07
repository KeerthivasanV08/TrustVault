"""
Strip legacy Keras arguments from model config.json.

Modern TensorFlow 2.13+ doesn't pass batch_input_shape and time_major
to layer constructors during deserialization, but it still serializes them
in the config. We strip them for maximum compatibility.
"""

import json
import logging
import shutil
import sys
import zipfile
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).resolve().parents[1]
KERAS_PATH = BACKEND_DIR / "app" / "models" / "transaction" / "lstm_sequence_model.keras"


def strip_legacy_args_from_config(config):
    """Recursively strip unsupported arguments from layer configs."""
    
    unsupported_keys = {'batch_input_shape', 'time_major', 'batch_size'}
    
    if isinstance(config, dict):
        # Strip from this level
        for key in list(config.keys()):
            if key in unsupported_keys:
                logger.debug(f"Stripping: {key}")
                del config[key]
        
        # Recurse into nested dicts
        for value in config.values():
            if isinstance(value, (dict, list)):
                strip_legacy_args_from_config(value)
    
    elif isinstance(config, list):
        for item in config:
            if isinstance(item, (dict, list)):
                strip_legacy_args_from_config(item)
    
    return config


def main():
    logger.info("=" * 80)
    logger.info("STRIP LEGACY ARGUMENTS FROM MODEL CONFIG")
    logger.info("=" * 80)
    logger.info(f"Model: {KERAS_PATH}")
    
    if not KERAS_PATH.exists():
        logger.error(f"Model not found: {KERAS_PATH}")
        return 1
    
    # Step 1: Extract and read config
    logger.info("Extracting config from model...")
    temp_dir = KERAS_PATH.parent / ".keras_temp"
    temp_dir.mkdir(exist_ok=True)
    
    try:
        with zipfile.ZipFile(KERAS_PATH, 'r') as z:
            z.extractall(temp_dir)
        logger.info(f"Extracted to: {temp_dir}")
    except Exception as e:
        logger.error(f"Failed to extract: {e}")
        return 1
    
    # Step 2: Load and patch config
    config_path = temp_dir / "config.json"
    logger.info("Reading config.json...")
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        logger.info(f"Original config keys: {list(config.keys())}")
        
        # Strip problematic args
        logger.info("Stripping legacy arguments...")
        config = strip_legacy_args_from_config(config)
        
        # Save patched config
        with open(config_path, 'w') as f:
            json.dump(config, f)
        
        logger.info("Config patched successfully")
    except Exception as e:
        logger.error(f"Failed to patch config: {e}")
        return 1
    
    # Step 3: Re-create model archive
    logger.info("Re-creating model archive...")
    temp_model = KERAS_PATH.with_stem(f"{KERAS_PATH.stem}.tmp")
    
    try:
        with zipfile.ZipFile(temp_model, 'w', zipfile.ZIP_DEFLATED) as z:
            for file_path in temp_dir.rglob('*'):
                if file_path.is_file():
                    arcname = file_path.relative_to(temp_dir)
                    z.write(file_path, arcname)
        
        logger.info(f"Archive created: {temp_model}")
    except Exception as e:
        logger.error(f"Failed to create archive: {e}")
        return 1
    
    # Step 4: Replace original
    logger.info(f"Replacing original model...")
    try:
        KERAS_PATH.unlink()
        temp_model.rename(KERAS_PATH)
        logger.info(f"Model replaced: {KERAS_PATH}")
    except Exception as e:
        logger.error(f"Failed to replace: {e}")
        return 1
    
    # Step 5: Cleanup
    logger.info("Cleaning up...")
    try:
        shutil.rmtree(temp_dir)
    except Exception as e:
        logger.warning(f"Failed to cleanup temp: {e}")
    
    # Step 6: Verify
    logger.info("Verifying cleaned model...")
    try:
        import tensorflow as tf
        model = tf.keras.models.load_model(KERAS_PATH, compile=False)
        import numpy as np
        dummy = np.random.randn(1, 10, 5).astype(np.float32)
        pred = model.predict(dummy, verbose=0)
        logger.info(f"[OK] Model loads and works (prediction: {float(pred[0, 0]):.4f})")
    except Exception as e:
        logger.error(f"Verification failed: {e}")
        return 1
    
    logger.info("=" * 80)
    logger.info("[SUCCESS] Model config cleaned successfully")
    logger.info("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(main())
