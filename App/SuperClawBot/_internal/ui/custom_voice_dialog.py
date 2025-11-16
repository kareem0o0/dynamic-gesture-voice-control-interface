"""
Dialog for recording and creating custom voice commands.
"""

import time
import sounddevice as sd
import numpy as np
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QLineEdit, QMessageBox, QProgressBar,
                               QListWidget, QSpinBox)
from PySide6.QtCore import QTimer, Qt, Signal, QThread
from PySide6.QtGui import QFont

from core.voice_trainer import VoiceTrainer
from config import VOICE_TRAINING_SAMPLES_RECOMMENDED, VOICE_TRAINING_DURATION, DEBUG


class RecordingThread(QThread):
    """Thread for recording audio without blocking UI."""
    finished = Signal(object)  # Emits audio data when done
    error = Signal(str)  # Emits error message if recording fails
    
    def __init__(self, trainer):
        super().__init__()
        self.trainer = trainer
    
    def run(self):
        """Run recording in background thread."""
        if DEBUG:
            print("DEBUG: RecordingThread.run() started")
        try:
            audio_data = self.trainer.record_sample()
            if DEBUG:
                print(f"DEBUG: record_sample() returned: {type(audio_data)}, length: {len(audio_data) if audio_data is not None else 'None'}")
            
            if audio_data is None:
                error_msg = "Recording failed: No audio data received. Check microphone connection and permissions."
                if DEBUG:
                    print(f"DEBUG: {error_msg}")
                self.error.emit(error_msg)
                self.finished.emit(None)
            else:
                if DEBUG:
                    print("DEBUG: Emitting finished signal with audio data")
                self.finished.emit(audio_data)
        except Exception as e:
            error_msg = f"Recording error: {str(e)}"
            if DEBUG:
                print(f"DEBUG: Exception in run(): {error_msg}")
                import traceback
                traceback.print_exc()
            self.error.emit(error_msg)
            self.finished.emit(None)  # Emit None to indicate failure


class CustomVoiceDialog(QDialog):
    """Dialog for recording custom voice commands."""
    
    def __init__(self, voice_model, existing_letters, existing_names, parent=None):
        super().__init__(parent)
        self.voice_model = voice_model
        
        # Ensure existing_letters is a set or list
        if isinstance(existing_letters, (set, list)):
            self.existing_letters = existing_letters if isinstance(existing_letters, set) else set(existing_letters)
        else:
            self.existing_letters = set()
        
        # Ensure existing_names is a list
        if isinstance(existing_names, list):
            self.existing_names = existing_names
        elif isinstance(existing_names, (set, tuple)):
            self.existing_names = list(existing_names)
        else:
            # If it's not a list, treat as empty (defensive programming)
            print(f"WARNING: existing_names should be a list, got {type(existing_names)}. Using empty list.")
            self.existing_names = []
        
        self.trainer = VoiceTrainer()
        self.embeddings = []
        self.audio_samples = []  # Store raw audio for playback
        self.recording_thread = None
        
        self.setWindowTitle("Create Custom Voice Command")
        self.setMinimumSize(500, 650)
        
        self._init_ui()
    
    def _init_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout()
        
        # Instructions
        self.instructions_label = QLabel()
        self._update_instructions()
        self.instructions_label.setWordWrap(True)
        self.instructions_label.setStyleSheet("background-color: #2a2a2a; padding: 10px; border-radius: 5px;")
        layout.addWidget(self.instructions_label)
        
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
        self.sample_count_spin.valueChanged.connect(self._on_sample_count_changed)
        sample_layout.addWidget(self.sample_count_spin)
        sample_layout.addWidget(QLabel(f"(Recommended: {VOICE_TRAINING_SAMPLES_RECOMMENDED})"))
        sample_layout.addStretch()
        layout.addLayout(sample_layout)
        
        # Recording button
        self.record_btn = QPushButton(f"🎤 Record Sample ({VOICE_TRAINING_DURATION}s)")
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
        self.progress_bar.setMaximum(self.sample_count_spin.value())
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # Samples list with playback
        samples_header = QHBoxLayout()
        samples_header.addWidget(QLabel("Recorded Samples:"))
        samples_header.addStretch()
        layout.addLayout(samples_header)
        
        self.samples_list = QListWidget()
        self.samples_list.setMaximumHeight(150)
        layout.addWidget(self.samples_list)
        
        # Sample control buttons
        sample_btn_layout = QHBoxLayout()
        
        self.play_btn = QPushButton("▶️ Play Selected")
        self.play_btn.setEnabled(False)
        self.play_btn.clicked.connect(self._play_sample)
        sample_btn_layout.addWidget(self.play_btn)
        
        self.remove_btn = QPushButton("🗑️ Remove Selected")
        self.remove_btn.setEnabled(False)
        self.remove_btn.clicked.connect(self._remove_sample)
        sample_btn_layout.addWidget(self.remove_btn)
        
        layout.addLayout(sample_btn_layout)
        
        # Connect list selection to enable buttons
        self.samples_list.itemSelectionChanged.connect(self._on_sample_selected)
        
        # Status label
        self.status_label = QLabel("Ready to record")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #5cb85c; font-weight: bold;")
        layout.addWidget(self.status_label)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("Save Voice Command")
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self._validate_and_save)
        btn_layout.addWidget(self.save_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        self.setLayout(layout)
    
    def _update_instructions(self):
        """Update instructions based on current settings."""
        sample_count = self.sample_count_spin.value() if hasattr(self, 'sample_count_spin') else VOICE_TRAINING_SAMPLES_RECOMMENDED
        duration = VOICE_TRAINING_DURATION
        
        instructions_text = (
            "1. Enter a name for your voice command\n"
            "2. Assign a unique letter\n"
            f"3. Record exactly {sample_count} samples ({duration}s each)\n"
            "4. Say the command clearly during each recording"
        )
        
        if hasattr(self, 'instructions_label'):
            self.instructions_label.setText(instructions_text)
    
    def _on_sample_count_changed(self, value):
        """Handle sample count change."""
        self.progress_bar.setMaximum(value)
        self._update_instructions()
    
    def _on_sample_selected(self):
        """Handle sample selection."""
        has_selection = len(self.samples_list.selectedItems()) > 0
        self.play_btn.setEnabled(has_selection)
        self.remove_btn.setEnabled(has_selection)
    
    def _start_recording(self):
        """Start recording a sample."""
        if DEBUG:
            print("DEBUG: _start_recording called")
        
        # Check if we've reached the limit
        target_samples = self.sample_count_spin.value()
        if len(self.embeddings) >= target_samples:
            QMessageBox.warning(
                self, 
                "Limit Reached", 
                f"You have already recorded {target_samples} samples.\n"
                "Remove some samples if you want to record new ones."
            )
            return
        
        # Validate inputs
        name = self.name_input.text().strip()
        letter = self.letter_input.text().strip()
        
        if DEBUG:
            print(f"DEBUG: name='{name}', letter='{letter}'")
        
        if not name:
            QMessageBox.warning(self, "Invalid Input", "Please enter a command name.")
            return
        
        # Check for duplicate name
        if name.lower() in [n.lower() for n in self.existing_names]:
            QMessageBox.warning(
                self, 
                "Duplicate Name", 
                f"Command name '{name}' already exists.\nPlease choose a different name."
            )
            return
        
        if not letter or len(letter) != 1:
            QMessageBox.warning(self, "Invalid Input", "Please enter a single letter.")
            return
        
        if letter in self.existing_letters:
            QMessageBox.warning(
                self, 
                "Duplicate Letter", 
                f"Letter '{letter}' is already assigned.\nPlease choose another."
            )
            return
        
        # Check if previous thread is still running
        if self.recording_thread and self.recording_thread.isRunning():
            QMessageBox.warning(self, "Recording in Progress", "Please wait for the current recording to finish.")
            return
        
        if DEBUG:
            print("DEBUG: Starting recording thread...")
        
        # Disable button during recording
        self.record_btn.setEnabled(False)
        self.status_label.setText("🔴 Recording... Speak now!")
        self.status_label.setStyleSheet("color: #d9534f; font-weight: bold;")
        
        # Start recording in background thread
        self.recording_thread = RecordingThread(self.trainer)
        self.recording_thread.finished.connect(self._on_recording_finished)
        self.recording_thread.error.connect(self._on_recording_error)
        if DEBUG:
            print("DEBUG: Thread created, starting...")
        self.recording_thread.start()
        if DEBUG:
            print("DEBUG: Thread started")
    
    def _on_recording_error(self, error_msg):
        """Handle recording error."""
        self.record_btn.setEnabled(True)
        self.status_label.setText(f"❌ Error: {error_msg}")
        self.status_label.setStyleSheet("color: #d9534f; font-weight: bold;")
        QMessageBox.critical(
            self, 
            "Recording Error", 
            f"Failed to record audio:\n\n{error_msg}\n\nPlease check your microphone settings."
        )
    
    def _on_recording_finished(self, audio_data):
        """Handle completed recording."""
        if DEBUG:
            print(f"DEBUG: _on_recording_finished called with audio_data: {audio_data is not None}")
        self.record_btn.setEnabled(True)
        
        if audio_data is None:
            # Error was already handled by _on_recording_error, but update status if needed
            if "Error:" not in self.status_label.text():
                self.status_label.setText("❌ Recording failed!")
                self.status_label.setStyleSheet("color: #d9534f; font-weight: bold;")
            return
        
        # Convert to embedding
        embedding = self.trainer.audio_to_embedding(audio_data, self.voice_model)
        
        if embedding is None:
            self.status_label.setText("❌ Failed to process audio!")
            self.status_label.setStyleSheet("color: #d9534f; font-weight: bold;")
            return
        
        # Store both embedding and raw audio
        self.embeddings.append(embedding)
        self.audio_samples.append(audio_data)
        
        # Update UI
        sample_num = len(self.embeddings)
        self.samples_list.addItem(f"Sample {sample_num} - {time.strftime('%H:%M:%S')}")
        self.progress_bar.setValue(sample_num)
        self.progress_label.setText(f"Samples recorded: {sample_num}")
        
        target_samples = self.sample_count_spin.value()
        
        if sample_num >= target_samples:
            self.status_label.setText(f"✅ All {sample_num} samples recorded! Ready to save.")
            self.status_label.setStyleSheet("color: #5cb85c; font-weight: bold;")
            self.save_btn.setEnabled(True)
            self.record_btn.setEnabled(False)  # Disable further recording
        else:
            remaining = target_samples - sample_num
            self.status_label.setText(f"✅ Sample {sample_num} recorded! {remaining} more needed.")
            self.status_label.setStyleSheet("color: #5cb85c; font-weight: bold;")
    
    def _play_sample(self):
        """Play the selected audio sample."""
        current_row = self.samples_list.currentRow()
        if current_row >= 0 and current_row < len(self.audio_samples):
            audio_data = self.audio_samples[current_row]
            
            try:
                self.status_label.setText("▶️ Playing sample...")
                self.status_label.setStyleSheet("color: #5bc0de; font-weight: bold;")
                
                # Play audio
                sd.play(audio_data, self.trainer.sample_rate)
                sd.wait()
                
                self.status_label.setText("Ready to record")
                self.status_label.setStyleSheet("color: #5cb85c; font-weight: bold;")
            except Exception as e:
                QMessageBox.warning(self, "Playback Error", f"Failed to play sample: {e}")
    
    def _remove_sample(self):
        """Remove selected sample."""
        current_row = self.samples_list.currentRow()
        if current_row >= 0:
            self.samples_list.takeItem(current_row)
            del self.embeddings[current_row]
            del self.audio_samples[current_row]
            
            # Update progress
            sample_num = len(self.embeddings)
            self.progress_bar.setValue(sample_num)
            self.progress_label.setText(f"Samples recorded: {sample_num}")
            
            # Re-enable recording if below target
            target_samples = self.sample_count_spin.value()
            if sample_num < target_samples:
                self.record_btn.setEnabled(True)
                self.save_btn.setEnabled(False)
    
    def _validate_and_save(self):
        """Validate before saving."""
        target_samples = self.sample_count_spin.value()
        actual_samples = len(self.embeddings)
        
        if actual_samples != target_samples:
            QMessageBox.warning(
                self,
                "Incomplete Recording",
                f"You need exactly {target_samples} samples.\n"
                f"You currently have {actual_samples} samples."
            )
            return
        
        self.accept()
    
    def get_voice_data(self):
        """Get recorded voice data."""
        return {
            'name': self.name_input.text().strip(),
            'letter': self.letter_input.text().strip(),
            'embeddings': self.embeddings
        }