"""
Robot Controller - Main Entry Point

Unified control system for robot with keyboard, voice, and gesture control.

Author: Unified Control System
Version: 2.0 - Modular Architecture
"""

import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPalette, QColor

from ui import SignalEmitter, RobotControlUI
from core import RobotControllerBackend


def setup_dark_theme(app):
    """Configure dark theme for the application."""
    app.setStyle("Fusion")
    
    palette = QPalette()
    
    # Set dark theme colors
    palette.setColor(QPalette.ColorRole.Window, QColor(30, 30, 30))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Base, QColor(45, 45, 45))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(35, 35, 35))
    palette.setColor(QPalette.ColorRole.Text, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Button, QColor(50, 50, 50))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(0, 120, 215))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    
    app.setPalette(palette)


def main():
    """Main application entry point."""
    # Create Qt application
    app = QApplication(sys.argv)
    
    # Setup dark theme
    setup_dark_theme(app)
    
    # Create signal emitter (for thread-safe communication)
    signals = SignalEmitter()
    
    # Create backend controller
    backend = RobotControllerBackend(signals)
    
    # Create and show main window
    window = RobotControlUI(backend)
    window.show()
    
    # Run application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()