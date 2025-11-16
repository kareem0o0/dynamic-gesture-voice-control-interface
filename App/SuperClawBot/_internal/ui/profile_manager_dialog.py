"""
Dialog for managing model profiles.
"""

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QListWidget, QMessageBox, QInputDialog,
                               QGroupBox)
from PySide6.QtCore import Qt


class ProfileManagerDialog(QDialog):
    """Dialog for managing model profiles."""
    
    def __init__(self, profile_manager, backend, parent=None):
        super().__init__(parent)
        self.profile_manager = profile_manager
        self.backend = backend
        
        self.setWindowTitle("Profile Manager")
        self.setMinimumSize(600, 500)
        self._init_ui()
        self._refresh_lists()
    
    def _init_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout()
        
        # Voice profiles section
        voice_group = QGroupBox("Voice Model Profiles")
        voice_layout = QVBoxLayout()
        
        self.voice_list = QListWidget()
        self.voice_list.itemDoubleClicked.connect(lambda: self._load_profile('voice'))
        voice_layout.addWidget(self.voice_list)
        
        voice_btn_layout = QHBoxLayout()
        load_voice_btn = QPushButton("Load Selected")
        load_voice_btn.clicked.connect(lambda: self._load_profile('voice'))
        voice_btn_layout.addWidget(load_voice_btn)
        
        delete_voice_btn = QPushButton("Delete")
        delete_voice_btn.clicked.connect(lambda: self._delete_profile('voice'))
        voice_btn_layout.addWidget(delete_voice_btn)
        
        voice_layout.addLayout(voice_btn_layout)
        voice_group.setLayout(voice_layout)
        layout.addWidget(voice_group)
        
        # Gesture profiles section
        gesture_group = QGroupBox("Gesture Model Profiles")
        gesture_layout = QVBoxLayout()
        
        self.gesture_list = QListWidget()
        self.gesture_list.itemDoubleClicked.connect(lambda: self._load_profile('gesture'))
        gesture_layout.addWidget(self.gesture_list)
        
        gesture_btn_layout = QHBoxLayout()
        load_gesture_btn = QPushButton("Load Selected")
        load_gesture_btn.clicked.connect(lambda: self._load_profile('gesture'))
        gesture_btn_layout.addWidget(load_gesture_btn)
        
        delete_gesture_btn = QPushButton("Delete")
        delete_gesture_btn.clicked.connect(lambda: self._delete_profile('gesture'))
        gesture_btn_layout.addWidget(delete_gesture_btn)
        
        gesture_layout.addLayout(gesture_btn_layout)
        gesture_group.setLayout(gesture_layout)
        layout.addWidget(gesture_group)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
        
        self.setLayout(layout)
    
    def _refresh_lists(self):
        """Refresh profile lists."""
        # Voice profiles
        self.voice_list.clear()
        voice_profiles = self.profile_manager.list_profiles('voice')
        active_voice = self.profile_manager.active_voice_profile
        
        for name in voice_profiles:
            item_text = name
            if name == active_voice:
                item_text += " [ACTIVE]"
            self.voice_list.addItem(item_text)
        
        # Gesture profiles
        self.gesture_list.clear()
        gesture_profiles = self.profile_manager.list_profiles('gesture')
        active_gesture = self.profile_manager.active_gesture_profile
        
        for name in gesture_profiles:
            item_text = name
            if name == active_gesture:
                item_text += " [ACTIVE]"
            self.gesture_list.addItem(item_text)
    
    def _load_profile(self, model_type):
        """Load selected profile."""
        if model_type == 'voice':
            list_widget = self.voice_list
        else:
            list_widget = self.gesture_list
        
        current_item = list_widget.currentItem()
        if not current_item:
            QMessageBox.warning(self, "No Selection","Please select a profile to load.")
            return
        
        # Extract profile name (remove [ACTIVE] if present)
        profile_name = current_item.text().replace(" [ACTIVE]", "")
        
        # Get profile
        profile = self.profile_manager.get_profile(profile_name)
        if not profile:
            QMessageBox.warning(self, "Error", f"Profile '{profile_name}' not found.")
            return
        
        # Load into appropriate controller
        try:
            if model_type == 'voice':
                # Extract model name from path
                model_name = profile.model_path.split('/')[-1].replace('.tflite', '')
                success = self.backend.voice_controller.load_new_model(model_name)
                if success:
                    self.backend.voice_controller.model.set_mapping(profile.class_to_letter)
                    self.profile_manager.set_active_profile(profile_name)
                    QMessageBox.information(self, "Success", f"Loaded voice profile: {profile_name}")
            else:
                # Extract model name from path
                model_name = profile.model_path.split('/')[-1].replace('.tflite', '')
                success = self.backend.gesture_controller.load_new_model(model_name)
                if success:
                    self.backend.gesture_controller.model.set_mapping(profile.class_to_letter)
                    # Load custom gestures
                    if profile.custom_gestures:
                        self.backend.gesture_controller.custom_gesture_manager.from_dict(profile.custom_gestures)
                    self.profile_manager.set_active_profile(profile_name)
                    QMessageBox.information(self, "Success", f"Loaded gesture profile: {profile_name}")
            
            self._refresh_lists()
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load profile: {e}")
    
    def _delete_profile(self, model_type):
        """Delete selected profile."""
        if model_type == 'voice':
            list_widget = self.voice_list
        else:
            list_widget = self.gesture_list
        
        current_item = list_widget.currentItem()
        if not current_item:
            QMessageBox.warning(self, "No Selection", "Please select a profile to delete.")
            return
        
        # Extract profile name
        profile_name = current_item.text().replace(" [ACTIVE]", "")
        
        # Confirm deletion
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete profile '{profile_name}'?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            success = self.profile_manager.delete_profile(profile_name)
            if success:
                QMessageBox.information(self, "Success", f"Profile '{profile_name}' deleted.")
                self._refresh_lists()
            else:
                QMessageBox.critical(self, "Error", f"Failed to delete profile '{profile_name}'.")