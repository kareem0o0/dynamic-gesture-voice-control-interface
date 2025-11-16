"""
Theme management for UI.
Supports dark and light themes with easy switching.
"""

from PySide6.QtGui import QPalette, QColor
from PySide6.QtWidgets import QApplication
import json
import os


class Theme:
    """Represents a UI theme."""
    
    def __init__(self, name, colors):
        self.name = name
        self.colors = colors


class ThemeManager:
    """Manages application themes."""
    
    THEMES = {
        'dark': Theme('Dark', {
            'window': QColor(30, 30, 30),
            'window_text': QColor(255, 255, 255),
            'base': QColor(45, 45, 45),
            'alternate_base': QColor(35, 35, 35),
            'text': QColor(255, 255, 255),
            'button': QColor(50, 50, 50),
            'button_text': QColor(255, 255, 255),
            'highlight': QColor(0, 120, 215),
            'highlighted_text': QColor(255, 255, 255),
            'accent': '#00ff88',
            'error': '#ff4444',
            'warning': '#ffaa00',
            'success': '#00ff88',
            'info': '#ffffff'
        }),
        'light': Theme('Light', {
            'window': QColor(240, 240, 240),
            'window_text': QColor(0, 0, 0),
            'base': QColor(255, 255, 255),
            'alternate_base': QColor(245, 245, 245),
            'text': QColor(0, 0, 0),
            'button': QColor(225, 225, 225),
            'button_text': QColor(0, 0, 0),
            'highlight': QColor(0, 120, 215),
            'highlighted_text': QColor(255, 255, 255),
            'accent': '#00aa66',
            'error': '#cc0000',
            'warning': '#ff8800',
            'success': '#00aa66',
            'info': '#000000'
        })
    }
    
    def __init__(self, config_file="theme_config.json"):
        self.config_file = config_file
        self.current_theme = 'dark'
        self.load_theme_preference()
    
    def apply_theme(self, app, theme_name='dark'):
        """Apply theme to QApplication."""
        if theme_name not in self.THEMES:
            theme_name = 'dark'
        
        theme = self.THEMES[theme_name]
        self.current_theme = theme_name
        
        # Apply Fusion style
        app.setStyle("Fusion")
        
        # Create and apply palette
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, theme.colors['window'])
        palette.setColor(QPalette.ColorRole.WindowText, theme.colors['window_text'])
        palette.setColor(QPalette.ColorRole.Base, theme.colors['base'])
        palette.setColor(QPalette.ColorRole.AlternateBase, theme.colors['alternate_base'])
        palette.setColor(QPalette.ColorRole.Text, theme.colors['text'])
        palette.setColor(QPalette.ColorRole.Button, theme.colors['button'])
        palette.setColor(QPalette.ColorRole.ButtonText, theme.colors['button_text'])
        palette.setColor(QPalette.ColorRole.Highlight, theme.colors['highlight'])
        palette.setColor(QPalette.ColorRole.HighlightedText, theme.colors['highlighted_text'])
        
        app.setPalette(palette)
        
        # Save preference
        self.save_theme_preference(theme_name)
    
    def get_color(self, color_name):
        """Get a specific color from current theme."""
        theme = self.THEMES.get(self.current_theme, self.THEMES['dark'])
        return theme.colors.get(color_name, '#ffffff')
    
    def save_theme_preference(self, theme_name):
        """Save theme preference to config file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump({'theme': theme_name}, f)
        except Exception as e:
            print(f"Error saving theme preference: {e}")
    
    def load_theme_preference(self):
        """Load theme preference from config file."""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    self.current_theme = data.get('theme', 'dark')
            except Exception as e:
                print(f"Error loading theme preference: {e}")
                self.current_theme = 'dark'
        else:
            self.current_theme = 'dark'
    
    def get_available_themes(self):
        """Get list of available theme names."""
        return list(self.THEMES.keys())
    
    def toggle_theme(self, app):
        """Toggle between available themes."""
        themes = self.get_available_themes()
        current_index = themes.index(self.current_theme)
        next_index = (current_index + 1) % len(themes)
        next_theme = themes[next_index]
        self.apply_theme(app, next_theme)
        return next_theme