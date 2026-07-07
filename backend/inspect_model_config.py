"""Inspect keras model config to find legacy arguments."""

import zipfile
import json
from pathlib import Path

keras_path = Path('app/models/transaction/lstm_sequence_model.keras')

print(f"Checking: {keras_path}")
print(f"Exists: {keras_path.exists()}")
print(f"Size: {keras_path.stat().st_size if keras_path.exists() else 'N/A'} bytes")

try:
    with zipfile.ZipFile(keras_path, 'r') as z:
        print("\nKeras model structure:")
        for name in z.namelist():
            print(f"  {name}")
        
        # Read model config
        config_file = 'config.json'
        if config_file in z.namelist():
            print(f"\nReading {config_file}...")
            with z.open(config_file) as f:
                config = json.load(f)
                print(f"Config keys: {list(config.keys())}")
                
                if 'config' in config:
                    layers = config['config'].get('layers', [])
                    print(f"Number of layers: {len(layers)}")
                    
                    # Check first few layers for problematic config
                    for i, layer in enumerate(layers[:5]):
                        layer_config = layer.get('config', {})
                        layer_name = layer.get('class_name', 'Unknown')
                        
                        print(f"\nLayer {i}: {layer_name}")
                        print(f"  Config keys: {list(layer_config.keys())}")
                        
                        # Check for problematic args
                        problematic = ['batch_input_shape', 'time_major', 'batch_size']
                        for key in problematic:
                            if key in layer_config:
                                print(f"  >>> PROBLEMATIC: {key} = {layer_config[key]}")
        else:
            print(f"{config_file} not found in archive")
            
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
