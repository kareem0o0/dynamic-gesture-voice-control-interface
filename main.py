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
import os


def get_resource_path(relative_path: str) -> str:
    """
    Return absolute path to resource, works for dev and PyInstaller bundle.
    Usage: get_resource_path("resources/icons/icon.png")
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base_path, relative_path)


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