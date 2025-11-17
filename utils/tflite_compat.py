"""
TFLite Interpreter Compatibility Layer

Provides a unified interface for TFLite model loading.
Attempts to use tflite_runtime.interpreter (fast, lightweight, Linux/ARM focus).
Falls back to tensorflow.lite.Interpreter if tflite_runtime is unavailable (e.g., Windows).

Usage:
    from utils.tflite_compat import get_tflite_interpreter
    
    interpreter = get_tflite_interpreter(model_path)
    interpreter.allocate_tensors()
    # ... rest of inference code works the same
"""

import sys

# Try to import tflite_runtime first (fast, lightweight)
try:
    import tflite_runtime.interpreter as tflite_module
    _TFLITE_SOURCE = "tflite_runtime"
except ImportError:
    _TFLITE_SOURCE = None

# Fallback to TensorFlow if tflite_runtime is not available
if _TFLITE_SOURCE is None:
    try:
        import tensorflow as tf
        _TF_AVAILABLE = True
    except ImportError:
        _TF_AVAILABLE = False
else:
    _TF_AVAILABLE = False


def get_tflite_interpreter(model_path):
    """
    Get a TFLite interpreter instance for the given model path.
    
    Args:
        model_path (str): Path to the .tflite model file
        
    Returns:
        An interpreter object with a compatible API:
        - allocate_tensors()
        - get_input_details()
        - get_output_details()
        - set_tensor(index, data)
        - invoke()
        - get_tensor(index)
        
    Raises:
        RuntimeError: If no TFLite runtime is available
        IOError: If the model file cannot be loaded
    """
    if _TFLITE_SOURCE == "tflite_runtime":
        # Use native tflite_runtime (e.g., Linux, ARM)
        return tflite_module.Interpreter(model_path)
    
    elif _TF_AVAILABLE:
        # Fallback to TensorFlow's TFLite (e.g., Windows, macOS)
        return tf.lite.Interpreter(model_path=model_path)
    
    else:
        raise RuntimeError(
            "No TFLite runtime available. "
            "Install 'tflite-runtime' or 'tensorflow' to use TFLite models."
        )


def print_tflite_info():
    """
    Print which TFLite source is being used (for debugging).
    """
    if _TFLITE_SOURCE == "tflite_runtime":
        print("[TFLite] Using tflite_runtime (native, fast)")
    elif _TF_AVAILABLE:
        import tensorflow
        print(f"[TFLite] Using TensorFlow {tensorflow.__version__} (fallback, full ML suite)")
    else:
        print("[TFLite] WARNING: No TFLite runtime available!")
