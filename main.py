"""
Robot Controller - Main Entry Point

Unified control system for robot with keyboard, voice, and gesture control.

Author: Unified Control System
Version: 2.0 - Modular Architecture with Profiles and Themes
"""

import sys
from PySide6.QtWidgets import QApplication

from ui import SignalEmitter, RobotControlUI
from core import RobotControllerBackend


def main():
    """Main application entry point."""
    # Create Qt application
    app = QApplication(sys.argv)
    
    # Create signal emitter (for thread-safe communication)
    signals = SignalEmitter()
    
    # Create backend controller
    backend = RobotControllerBackend(signals)
    
    # Apply saved theme
    backend.theme_manager.apply_theme(app, backend.theme_manager.current_theme)
    
    # Create and show main window
    window = RobotControlUI(backend)
    window.show()
    
    # Run application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()