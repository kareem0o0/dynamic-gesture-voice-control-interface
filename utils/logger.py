"""
Logging utilities.
"""

from enum import Enum


class LogLevel(Enum):
    """Log level enumeration."""
    ERROR = "error"
    WARNING = "warning"
    SUCCESS = "success"
    INFO = "info"


def get_log_color(level):
    """
    Get HTML color code for log level.
    
    Args:
        level: LogLevel enum value
        
    Returns:
        HTML color code string
    """
    colors = {
        LogLevel.ERROR: "#ff4444",
        LogLevel.WARNING: "#ffaa00",
        LogLevel.SUCCESS: "#00ff88",
        LogLevel.INFO: "#ffffff"
    }
    return colors.get(level, "#ffffff")