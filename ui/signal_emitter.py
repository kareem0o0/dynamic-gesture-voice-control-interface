"""
Qt signal emitter for thread-safe UI updates.
"""

from PySide6.QtCore import QObject, Signal


class SignalEmitter(QObject):
    """Qt signal emitter for thread-safe UI updates between threads."""
    
    log_signal = Signal(str, str)  # message, level
    frame_signal = Signal(object)  # video frame
    mode_signal = Signal(str)  # control mode
    status_signal = Signal(str)  # connection status
    voice_command_signal = Signal(str, float)  # command, confidence
    gesture_command_signal = Signal(str, float)  # gesture, confidence