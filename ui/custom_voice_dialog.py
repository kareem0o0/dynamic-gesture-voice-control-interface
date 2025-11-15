"""
Dialog for recording and creating custom voice commands.
"""

import time
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QLineEdit, QMessageBox, QProgressBar,
                               QListWidget, QSpinBox)
from PySide6.QtCore import QTimer, Qt, Signal, QThread
from PySide6.QtGui import QFont

from core.voice_trainer import VoiceTrainer
from config import VOICE_TRAINING_SAMPLES_RECOMMENDED


class RecordingThread(QThread):
    """Thread for recording audio without blocking UI."""
    finished = Signal(object)  # Emits audio data when done
    
    def __init__(self, trainer):
        super().__init__()
        self.trainer = trainer
    
    def run(self):
        audio_data = self.trainer.record_sample()
        self.finished.emit(audio_data)


class CustomVoiceDialog(QDialog):
    """Dialog for recording custom voice commands."""
    
    def __init__(self, voice_model, existing_letters, parent=None):
        super().__init__(parent)
        self.voice_model = voice_model
        self.existing_letters = existing_letters
        self.trainer = VoiceTrainer()
        self.embeddings = []
        self.recording_thread = None
        
        self.setWindowTitle("Create Custom Voice Command")
        self.setMinimumSize(500, 550)
        
        self._init_ui()
    
    def _init_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout()
        
        # Instructions
        instructions = QLabel(
            "1. Enter a name for your voice command\n"
            "2. Assign a unique letter\n"
            f"3. Record {VOICE_TRAINING_SAMPLES_RECOMMENDED} samples (2 seconds each)\n"
            "4. Say the command clearly during each recording"
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet("background-color: #2a2a2a; padding: 10px; border-radius: 5px;")
        layout.addWidget(instructions)
        
        # Name input
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Command Name:"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g., hello, go, faster")
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
        
        # Sample count control
        sample_layout = QHBoxLayout()
        sample_layout.addWidget(QLabel("Samples to Record:"))
        self.sample_count_spin = QSpinBox()
        self.sample_count_spin.setRange(5, 30)
        self.sample_count_spin.setValue(VOICE_TRAINING_SAMPLES_RECOMMENDED)
        sample_layout.addWidget(self.sample_count_spin)
        sample_layout.addWidget(QLabel(f"(Recommended: {VOICE_TRAINING_SAMPLES_RECOMMENDED})"))
        sample_layout.addStretch()
        layout.addLayout(sample_layout)
        
        # Recording button
        self.record_btn = QPushButton("🎤 Record Sample (2s)")
        self.record_btn.setStyleSheet("background-color: #d9534f; font-size: 14px; padding: 10px;")
        self.record_btn.clicked.connect(self._start_recording)
        layout.addWidget(self.record_btn)
        
        # Progress
        progress_layout = QHBoxLayout()
        self.progress_label = QLabel("Samples recorded: 0")
        self.progress_label.setFont(QFont("Arial", 10, QFont.Bold))
        progress_layout.addWidget(self.progress_label)
        progress_layout.addStretch()
        layout.addLayout(progress_layout)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(VOICE_TRAINING_SAMPLES_RECOMMENDED)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # Samples list
        self.samples_list = QListWidget()
        self.samples_list.setMaximumHeight(150)
        layout.addWidget(QLabel("Recorded Samples:"))
        layout.addWidget(self.samples_list)
        
        # Remove sample button
        remove_btn = QPushButton("Remove Selected Sample")
        remove_btn.clicked.connect(self._remove_sample)
        layout.addWidget(remove_btn)
        
        # Status label
        self.status_label = QLabel("Ready to record")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #5cb85c; font-weight: bold;")
        layout.addWidget(self.status_label)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("Save Voice Command")
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.save_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        self.setLayout(layout)
    
    def _start_recording(self):
        """Start recording a sample."""
        # Validate inputs
        name = self.name_input.text().strip()
        letter = self.letter_input.text().strip()
        
        if not name:
            QMessageBox.warning(self, "Invalid Input", "Please enter a command name.")
            return
        
        if not letter or len(letter) != 1:
            QMessageBox.warning(self, "Invalid Input", "Please enter a single letter.")
            return
        
        if letter in self.existing_letters:
            QMessageBox.warning(self, "Duplicate Letter", 
                              f"Letter '{letter}' is already assigned.\nPlease choose another.")
            return
        
        # Disable button during recording
        self.record_btn.setEnabled(False)
        self.status_label.setText("🔴 Recording... Speak now!")
        self.status_label.setStyleSheet("color: #d9534f; font-weight: bold;")
        
        # Start recording in background thread
        self.recording_thread = RecordingThread(self.trainer)
        self.recording_thread.finished.connect(self._on_recording_finished)
        self.recording_thread.start()
    
    def _on_recording_finished(self, audio_data):
        """Handle completed recording."""
        self.record_btn.setEnabled(True)
        
        if audio_data is None:
            self.status_label.setText("❌ Recording failed!")
            self.status_label.setStyleSheet("color: #d9534f; font-weight: bold;")
            return
        
        # Convert to embedding
        embedding = self.trainer.audio_to_embedding(audio_data, self.voice_model)
        
        if embedding is None:
            self.status_label.setText("❌ Failed to process audio!")
            self.status_label.setStyleSheet("color: #d9534f; font-weight: bold;")
            return
        
        # Store embedding
        self.embeddings.append(embedding)
        
        # Update UI
        sample_num = len(self.embeddings)
        self.samples_list.addItem(f"Sample {sample_num} - {time.strftime('%H:%M:%S')}")
        self.progress_bar.setValue(sample_num)
        self.progress_label.setText(f"Samples recorded: {sample_num}")
        
        target_samples = self.sample_count_spin.value()
        
        if sample_num >= target_samples:
            self.status_label.setText(f"✅ {sample_num} samples recorded! Ready to save.")
            self.status_label.setStyleSheet("color: #5cb85c; font-weight: bold;")
            self.save_btn.setEnabled(True)
        else:
            remaining = target_samples - sample_num
            self.status_label.setText(f"✅ Sample {sample_num} recorded! {remaining} more recommended.")
            self.status_label.setStyleSheet("color: #5cb85c; font-weight: bold;")
            
            # Enable save if we have at least 5 samples
            if sample_num >= 5:
                self.save_btn.setEnabled(True)
    
    def _remove_sample(self):
        """Remove selected sample."""
        current_row = self.samples_list.currentRow()
        if current_row >= 0:
            self.samples_list.takeItem(current_row)
            del self.embeddings[current_row]
            
            # Update progress
            sample_num = len(self.embeddings)
            self.progress_bar.setValue(sample_num)
            self.progress_label.setText(f"Samples recorded: {sample_num}")
            
            # Update save button
            if sample_num < 5:
                self.save_btn.setEnabled(False)
    
    def get_voice_data(self):
        """Get recorded voice data."""
        return {
            'name': self.name_input.text().strip(),
            'letter': self.letter_input.text().strip(),
            'embeddings': self.embeddings
        }