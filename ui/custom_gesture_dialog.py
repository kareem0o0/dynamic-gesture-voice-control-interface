"""
Dialog for capturing and creating custom gestures.
"""

import time
import cv2
import numpy as np
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QLineEdit, QMessageBox, QProgressBar)
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QImage, QPixmap

from core.embedding_extractor import EmbeddingExtractor


class CustomGestureDialog(QDialog):
    """Dialog for capturing custom gestures."""
    
    def __init__(self, camera, model_path, existing_letters, parent=None):
        super().__init__(parent)
        self.camera = camera
        self.model_path = model_path
        self.existing_letters = existing_letters
        self.embeddings = []
        self.capturing = False
        self.frames_to_capture = 20
        self.frames_captured = 0
        
        self.setWindowTitle("Create Custom Gesture")
        self.setMinimumSize(600, 550)
        
        # Initialize extractor
        try:
            self.extractor = EmbeddingExtractor(model_path)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load model: {e}")
            self.extractor = None
        
        self._init_ui()
        self._start_preview()
    
    def _init_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout()
        
        # Instructions
        instructions = QLabel(
            "1. Enter a name for your gesture\n"
            "2. Assign a unique letter\n"
            "3. Click 'Start Capture' and perform the gesture\n"
            "4. Hold the gesture steady for 2-3 seconds"
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # Name input
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Gesture Name:"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g., wave, peace, thumbs_up")
        name_layout.addWidget(self.name_input)
        layout.addLayout(name_layout)
        
        # Letter input
        letter_layout = QHBoxLayout()
        letter_layout.addWidget(QLabel("Assigned Letter:"))
        self.letter_input = QLineEdit()
        self.letter_input.setMaxLength(1)
        self.letter_input.setPlaceholderText("Single letter")
        letter_layout.addWidget(self.letter_input)
        layout.addLayout(letter_layout)
        
        # Video preview
        self.video_label = QLabel("Camera Preview")
        self.video_label.setFixedSize(480, 360)
        self.video_label.setStyleSheet("border: 2px solid #00ff88; background: #000;")
        self.video_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.video_label, alignment=Qt.AlignCenter)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(self.frames_to_capture)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("Ready to capture")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self.capture_btn = QPushButton("Start Capture")
        self.capture_btn.clicked.connect(self._start_capture)
        btn_layout.addWidget(self.capture_btn)
        
        self.save_btn = QPushButton("Save Gesture")
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.save_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        self.setLayout(layout)
        
        # Timer for video preview
        self.preview_timer = QTimer()
        self.preview_timer.timeout.connect(self._update_preview)
    
    def _start_preview(self):
        """Start video preview."""
        if self.camera:
            self.preview_timer.start(30)  # 30ms = ~33 FPS
    
    def _update_preview(self):
        """Update video preview."""
        if not self.camera:
            return
        
        ret, frame = self.camera.read()
        if not ret or frame is None:
            return
        
        # Add text overlay
        if self.capturing:
            cv2.putText(frame, "CAPTURING...", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(frame, f"Frame: {self.frames_captured}/{self.frames_to_capture}", (10, 70),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # Convert and display
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_image)
        scaled = pixmap.scaled(self.video_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.video_label.setPixmap(scaled)
        
        # Capture frames if active
        if self.capturing and self.extractor:
            try:
                embedding = self.extractor.extract_from_frame(rgb_frame)
                if embedding is not None:
                    self.embeddings.append(embedding)
                    self.frames_captured += 1
                    self.progress_bar.setValue(self.frames_captured)
                    
                    if self.frames_captured >= self.frames_to_capture:
                        self._finish_capture()
            except Exception as e:
                print(f"Error capturing frame: {e}")
    
    def _start_capture(self):
        """Start capturing gesture frames."""
        # Validate inputs
        name = self.name_input.text().strip()
        letter = self.letter_input.text().strip()
        
        if not name:
            QMessageBox.warning(self, "Invalid Input", "Please enter a gesture name.")
            return
        
        if not letter or len(letter) != 1:
            QMessageBox.warning(self, "Invalid Input", "Please enter a single letter.")
            return
        
        if letter in self.existing_letters:
            QMessageBox.warning(self, "Duplicate Letter", 
                              f"Letter '{letter}' is already assigned.\nPlease choose another.")
            return
        
        # Start capture
        self.embeddings = []
        self.frames_captured = 0
        self.capturing = True
        self.capture_btn.setEnabled(False)
        self.status_label.setText("Capturing... Hold your gesture steady!")
        self.progress_bar.setValue(0)
    
    def _finish_capture(self):
        """Finish capturing and enable save."""
        self.capturing = False
        self.capture_btn.setEnabled(True)
        self.save_btn.setEnabled(True)
        self.status_label.setText(f"Captured {self.frames_captured} frames! Click 'Save Gesture' to finish.")
    
    def get_gesture_data(self):
        """Get captured gesture data."""
        return {
            'name': self.name_input.text().strip(),
            'letter': self.letter_input.text().strip(),
            'embeddings': self.embeddings
        }
    
    def closeEvent(self, event):
        """Stop preview on close."""
        self.preview_timer.stop()
        event.accept()