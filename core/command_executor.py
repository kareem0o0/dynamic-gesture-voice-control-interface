"""
Command execution logic.
"""

import threading

from config import (STOP_ALL, STOP_DRIVE, STOP_ARM1, STOP_ARM2, STOP_ARM3,
                   COMMAND_DURATION, COOLDOWN_TIME)


class CommandExecutor:
    """Handles command execution and timing."""
    
    def __init__(self, bluetooth_manager, signal_emitter):
        self.bluetooth = bluetooth_manager
        self.signals = signal_emitter
        self.active_cmds = {
            'drive': None,
            'arm1': None,
            'arm2': None,
            'arm3': None
        }
    
    def send_command(self, command):
        """Send command via Bluetooth."""
        self.bluetooth.send(command)
    
    def stop_all_motors(self):
        """Stop all motors immediately."""
        self.send_command(STOP_ALL)
        self.active_cmds = {k: None for k in self.active_cmds}
        self.signals.log_signal.emit("All motors stopped", "info")
    
    def execute_timed_command(self, command, stop_command, stop_event):
        """
        Execute command for fixed duration or until stopped.
        
        Args:
            command: Command to execute
            stop_command: Command to stop
            stop_event: Threading event for early stop
        """
        self.send_command(command)
        
        if stop_event.wait(COMMAND_DURATION):
            # Stopped early
            pass
        else:
            # Duration elapsed
            if stop_command:
                self.send_command(stop_command)