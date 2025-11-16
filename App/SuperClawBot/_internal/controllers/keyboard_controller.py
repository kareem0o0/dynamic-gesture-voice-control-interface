"""
Keyboard control implementation.
This is a placeholder/helper module for keyboard control logic.
The actual keyboard control is implemented directly in the UI (main_window.py)
via keyPressEvent and keyReleaseEvent methods.
"""

from .base_controller import BaseController


class KeyboardController(BaseController):
    """
    Keyboard control mode.
    
    Note: Unlike voice and gesture controllers, keyboard control is handled
    directly in the UI layer (main_window.py) through Qt's keyPressEvent
    and keyReleaseEvent methods for better responsiveness.
    
    This class exists for consistency in the architecture but doesn't
    need active start/stop methods since keyboard events are always captured
    by the UI when keyboard mode is active.
    """
    
    def __init__(self, command_executor, signal_emitter):
        super().__init__(command_executor, signal_emitter)
        self.active = True  # Always available
    
    def start(self):
        """
        Start keyboard control.
        
        Keyboard control doesn't require initialization since Qt
        automatically handles keyboard events.
        """
        self.active = True
        self.signals.log_signal.emit("Keyboard control active", "success")
    
    def stop(self):
        """
        Stop keyboard control.
        
        This just updates the state flag. The UI will check the current
        mode before processing keyboard events.
        """
        self.active = False
        self.signals.log_signal.emit("Keyboard control stopped", "info")
    
    def is_available(self):
        """Keyboard control is always available."""
        return True