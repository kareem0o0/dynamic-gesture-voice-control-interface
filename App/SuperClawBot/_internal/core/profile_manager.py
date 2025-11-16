"""
Profile management system for models.
Handles saving/loading different model configurations.
"""

import json
import os
from pathlib import Path


class ModelProfile:
    """Represents a single model profile."""
    
    def __init__(self, name, model_type):
        self.name = name
        self.model_type = model_type  # 'voice' or 'gesture'
        self.model_path = ""
        self.labels_path = ""
        self.classes = []
        self.class_to_letter = {}
        self.custom_gestures = {}  # For gesture models only
        self.confidence_threshold = 0.7
        self.settings = {}
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            'name': self.name,
            'model_type': self.model_type,
            'model_path': self.model_path,
            'labels_path': self.labels_path,
            'classes': self.classes,
            'class_to_letter': self.class_to_letter,
            'custom_gestures': self.custom_gestures,
            'confidence_threshold': self.confidence_threshold,
            'settings': self.settings
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create profile from dictionary."""
        profile = cls(data['name'], data['model_type'])
        profile.model_path = data.get('model_path', '')
        profile.labels_path = data.get('labels_path', '')
        profile.classes = data.get('classes', [])
        profile.class_to_letter = data.get('class_to_letter', {})
        profile.custom_gestures = data.get('custom_gestures', {})
        profile.confidence_threshold = data.get('confidence_threshold', 0.7)
        profile.settings = data.get('settings', {})
        return profile


class ProfileManager:
    """Manages model profiles."""
    
    def __init__(self, profiles_file="model_profiles.json"):
        self.profiles_file = profiles_file
        self.profiles = {}  # {profile_name: ModelProfile}
        self.active_voice_profile = None
        self.active_gesture_profile = None
        self.last_used_voice = None
        self.last_used_gesture = None
        self.load_profiles()
    
    def create_profile(self, name, model_type):
        """Create a new profile."""
        if name in self.profiles:
            return None
        
        profile = ModelProfile(name, model_type)
        self.profiles[name] = profile
        return profile
    
    def delete_profile(self, name):
        """Delete a profile."""
        if name in self.profiles:
            del self.profiles[name]
            # Clear active if deleted
            if self.active_voice_profile == name:
                self.active_voice_profile = None
            if self.active_gesture_profile == name:
                self.active_gesture_profile = None
            self.save_profiles()
            return True
        return False
    
    def get_profile(self, name):
        """Get a profile by name."""
        return self.profiles.get(name)
    
    def set_active_profile(self, name):
        """Set a profile as active."""
        if name not in self.profiles:
            return False
        
        profile = self.profiles[name]
        if profile.model_type == 'voice':
            self.active_voice_profile = name
            self.last_used_voice = name
        elif profile.model_type == 'gesture':
            self.active_gesture_profile = name
            self.last_used_gesture = name
        
        self.save_profiles()
        return True
    
    def get_active_profile(self, model_type):
        """Get the active profile for a model type."""
        if model_type == 'voice':
            return self.profiles.get(self.active_voice_profile)
        elif model_type == 'gesture':
            return self.profiles.get(self.active_gesture_profile)
        return None
    
    def list_profiles(self, model_type=None):
        """List all profiles, optionally filtered by type."""
        if model_type:
            return [name for name, prof in self.profiles.items() 
                   if prof.model_type == model_type]
        return list(self.profiles.keys())
    
    def save_profiles(self):
        """Save all profiles to JSON file."""
        try:
            data = {
                'profiles': {name: prof.to_dict() for name, prof in self.profiles.items()},
                'active_voice': self.active_voice_profile,
                'active_gesture': self.active_gesture_profile,
                'last_used_voice': self.last_used_voice,
                'last_used_gesture': self.last_used_gesture
            }
            
            with open(self.profiles_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            return True
        except Exception as e:
            print(f"Error saving profiles: {e}")
            return False
    
    def load_profiles(self):
        """Load profiles from JSON file."""
        if not os.path.exists(self.profiles_file):
            return
        
        try:
            with open(self.profiles_file, 'r') as f:
                data = json.load(f)
            
            # Load profiles
            for name, prof_data in data.get('profiles', {}).items():
                self.profiles[name] = ModelProfile.from_dict(prof_data)
            
            # Load active profiles
            self.active_voice_profile = data.get('active_voice')
            self.active_gesture_profile = data.get('active_gesture')
            self.last_used_voice = data.get('last_used_voice')
            self.last_used_gesture = data.get('last_used_gesture')
        
        except Exception as e:
            print(f"Error loading profiles: {e}")
    
    def update_profile(self, name, **kwargs):
        """Update profile attributes."""
        if name not in self.profiles:
            return False
        
        profile = self.profiles[name]
        for key, value in kwargs.items():
            if hasattr(profile, key):
                setattr(profile, key, value)
        
        self.save_profiles()
        return True