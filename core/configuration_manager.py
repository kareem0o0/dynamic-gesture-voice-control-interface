"""
Configuration manager for saving/loading custom gestures and voices.
"""

import json
import os
from datetime import datetime


class ConfigurationManager:
    """Manages saving and loading of custom configurations."""
    
    def __init__(self, config_dir="saved_configurations"):
        self.config_dir = config_dir
        self.recent_file = os.path.join(config_dir, "recent.json")
        self._ensure_config_dir()
    
    def _ensure_config_dir(self):
        """Ensure configuration directory exists."""
        os.makedirs(self.config_dir, exist_ok=True)
    
    def save_configuration(self, name, gesture_controller, voice_controller):
        """
        Save current custom gestures and voices.
        
        Args:
            name: Configuration name
            gesture_controller: Gesture controller instance
            voice_controller: Voice controller instance
            
        Returns:
            True if successful, False otherwise
        """
        try:
            config_data = {
                'name': name,
                'created': datetime.now().isoformat(),
                'custom_gestures': gesture_controller.custom_gesture_manager.to_dict(),
                'custom_voices': voice_controller.custom_voice_manager.to_dict(),
                'gesture_model': gesture_controller.current_model_name,
                'voice_model': voice_controller.current_model_name
            }
            
            # Save configuration file
            filename = f"{name.replace(' ', '_')}.json"
            filepath = os.path.join(self.config_dir, filename)
            
            with open(filepath, 'w') as f:
                json.dump(config_data, f, indent=2)
            
            # Update recent list
            self._add_to_recent(name, filepath)
            
            return True
        
        except Exception as e:
            print(f"Error saving configuration: {e}")
            return False
    
    def load_configuration(self, filepath, gesture_controller, voice_controller):
        """
        Load a saved configuration.
        
        Args:
            filepath: Path to configuration file
            gesture_controller: Gesture controller instance
            voice_controller: Voice controller instance
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(filepath, 'r') as f:
                config_data = json.load(f)
            
            # Load custom gestures
            gesture_controller.custom_gesture_manager.from_dict(
                config_data.get('custom_gestures', {})
            )
            
            # Load custom voices
            voice_controller.custom_voice_manager.from_dict(
                config_data.get('custom_voices', {})
            )
            
            # Update recent list
            self._add_to_recent(config_data['name'], filepath)
            
            return True
        
        except Exception as e:
            print(f"Error loading configuration: {e}")
            return False
    
    def _add_to_recent(self, name, filepath):
        """Add configuration to recent list."""
        try:
            # Load existing recent list
            recent = []
            if os.path.exists(self.recent_file):
                with open(self.recent_file, 'r') as f:
                    recent = json.load(f)
            
            # Add new entry (remove if already exists)
            recent = [r for r in recent if r['filepath'] != filepath]
            recent.insert(0, {
                'name': name,
                'filepath': filepath,
                'accessed': datetime.now().isoformat()
            })
            
            # Keep only last 10
            recent = recent[:10]
            
            # Save
            with open(self.recent_file, 'w') as f:
                json.dump(recent, f, indent=2)
        
        except Exception as e:
            print(f"Error updating recent list: {e}")
    
    def get_recent_configurations(self):
        """
        Get list of recent configurations.
        
        Returns:
            List of recent configuration dictionaries
        """
        if not os.path.exists(self.recent_file):
            return []
        
        try:
            with open(self.recent_file, 'r') as f:
                recent = json.load(f)
            
            # Filter out non-existent files
            recent = [r for r in recent if os.path.exists(r['filepath'])]
            
            return recent
        
        except Exception as e:
            print(f"Error loading recent configurations: {e}")
            return []
    
    def get_all_configurations(self):
        """
        Get list of all saved configurations.
        
        Returns:
            List of configuration file paths
        """
        if not os.path.exists(self.config_dir):
            return []
        
        configs = []
        for file in os.listdir(self.config_dir):
            if file.endswith('.json') and file != 'recent.json':
                filepath = os.path.join(self.config_dir, file)
                configs.append(filepath)
        
        return configs