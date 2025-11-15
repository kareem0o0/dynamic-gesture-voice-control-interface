"""
Base controller interface.
"""

from abc import ABC, abstractmethod


class BaseController(ABC):
    """Base class for all control modes."""
    
    def __init__(self, command_executor, signal_emitter):
        self.executor = command_executor
        self.signals = signal_emitter
        self.active = False
    
    @abstractmethod
    def start(self):
        """Start the controller."""
        pass
    
    @abstractmethod
    def stop(self):
        """Stop the controller."""
        pass
    
    @abstractmethod
    def is_available(self):
        """Check if controller is available."""
        pass