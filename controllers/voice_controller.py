"""
Voice control implementation.
"""

import threading
import numpy as np
import sounddevice as sd

from .base_controller import BaseController
from models import VoiceModel
from config import VOICE_SAMPLE_RATE, VOICE_OVERLAP, VOICE_CONFIDENCE_THRESHOLD, COOLDOWN_TIME
from core.model_manager import ModelManager
from core.voice_trainer import CustomVoiceManager


class VoiceController(BaseController):
    """Voice recognition control mode with dynamic model support."""
    
    def __init__(self, command_executor, signal_emitter):
        super().__init__(command_executor, signal_emitter)

        self.custom_voice_manager = CustomVoiceManager()
        self.custom_voice_threshold = 0.75
        self.model_manager = ModelManager(signal_emitter)
        self.model = None
        self.buffer = None
        self.current_model_name = None
        
        # Try to load default model
        try:
            self._load_model("soundclassifier_with_metadata")
        except Exception as e:
            self.signals.log_signal.emit(f"Default voice model not found - load one via Models menu", "warning")
        
        self.stream = None
        self.position = 0
        self.action_lock = threading.Lock()
        self.stop_event = threading.Event()
        self.cooldown_active = False
    
    def _load_model(self, model_name):
        """Load a voice model by name."""
        try:
            self.model = VoiceModel(model_name)
            
            # Check if model actually loaded
            if not self.model.is_loaded():
                self.model = None
                return False
            
            self.current_model_name = model_name
            self.buffer = np.zeros(self.model.buffer_size, dtype=np.float32)
            
            # Load or create mapping
            mapping = self.model_manager.load_mapping(model_name, "voice")
            if mapping is None:
                # Create default mapping
                labels = self.model.get_labels()
                mapping = self.model_manager.create_default_mapping(labels)
                self.model_manager.save_mapping(model_name, "voice", mapping)
            
            self.model.set_mapping(mapping)
            self.signals.log_signal.emit(f"Voice model loaded: {model_name}", "success")
            
            # Check if mapping is complete
            if not self.model.is_mapping_complete():
                self.signals.log_signal.emit("Warning: Model mapping incomplete - configure letters first", "warning")
            
            return True
        except Exception as e:
            self.signals.log_signal.emit(f"Failed to load voice model: {e}", "error")
            self.model = None
            return False
    
    def load_new_model(self, model_name):
        """Load a different voice model."""
        # Stop if active
        was_active = self.active
        if was_active:
            self.stop()
        
        success = self._load_model(model_name)
        
        # Restart if was active
        if was_active and success:
            self.start()
        
        return success
    
    def get_current_mapping(self):
        """Get current class-to-letter mapping."""
        if self.model:
            mapping = self.model.class_to_letter.copy()
            # Add custom voice commands
            for name in self.custom_voice_manager.get_all_voices():
                letter = self.custom_voice_manager.get_voice_letter(name)
                mapping[f"[CUSTOM] {name}"] = letter
            return mapping
        return {}
    
    def update_mapping(self, mapping):
        """Update class-to-letter mapping."""
        if self.model:
            # Separate custom voices from regular classes
            regular_mapping = {}
            for key, value in mapping.items():
                if key.startswith("[CUSTOM] "):
                    # Update custom voice letter
                    custom_name = key.replace("[CUSTOM] ", "")
                    self.custom_voice_manager.update_letter(custom_name, value)
                else:
                    regular_mapping[key] = value
            
            self.model.set_mapping(regular_mapping)
            self.model_manager.save_mapping(self.current_model_name, "voice", regular_mapping)
            self.signals.log_signal.emit("Voice mapping updated", "success")
            return True
        return False
    
    def is_available(self):
        """Check if voice control is available."""
        return (self.model is not None and 
                self.model.is_loaded() and 
                self.model.is_mapping_complete())
    
    def start(self):
        """Start voice recognition."""
        if not self.model or not self.model.is_loaded():
            self.signals.log_signal.emit("Voice model not loaded", "error")
            return
        
        if not self.model.is_mapping_complete():
            self.signals.log_signal.emit("Voice mapping incomplete - configure letters first", "error")
            return
        
        self.active = True
        self.position = 0
        self.buffer.fill(0)
        self.cooldown_active = False
        
        try:
            self.stream = sd.InputStream(
                samplerate=VOICE_SAMPLE_RATE,
                channels=1,
                dtype='float32',
                blocksize=int(VOICE_SAMPLE_RATE * 0.1),
                callback=self._audio_callback
            )
            self.stream.start()
            self.signals.log_signal.emit("Voice recognition active", "success")
        except Exception as e:
            self.signals.log_signal.emit(f"Voice stream error: {e}", "error")
            self.active = False
    
    def stop(self):
        """Stop voice recognition."""
        self.active = False
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        self.stop_event.set()
        self.signals.log_signal.emit("Voice recognition stopped", "info")
    
    def _audio_callback(self, indata, frames, time_info, status):
        """Process audio stream."""
        if not self.active or not self.model:
            return
        
        chunk = indata[:, 0].copy()
        samples = self.model.buffer_size
        
        n = min(len(chunk), samples - self.position)
        self.buffer[self.position:self.position + n] = chunk[:n]
        self.position += n
        
        if self.position >= samples:
            audio = self.buffer.copy()
            
            # Check custom voice commands first (higher priority)
            detected_class = None
            detected_letter = None
            confidence = 0
            is_custom = False
            
            # Try to get embedding for custom voice matching
            try:
                from core.voice_trainer import VoiceTrainer
                trainer = VoiceTrainer()
                embedding = trainer.audio_to_embedding(audio, self.model)
                
                if embedding is not None:
                    custom_name, custom_letter, custom_conf = self.custom_voice_manager.predict(
                        embedding, self.custom_voice_threshold
                    )
                    
                    if custom_name:
                        detected_class = f"[CUSTOM] {custom_name}"
                        detected_letter = custom_letter
                        confidence = custom_conf
                        is_custom = True
            except Exception as e:
                print(f"Custom voice error: {e}")
            
            # If no custom voice, use regular model
            if not is_custom:
                class_name, letter, conf = self.model.predict(audio)
                detected_class = class_name
                detected_letter = letter
                confidence = conf
            
            if confidence > VOICE_CONFIDENCE_THRESHOLD and detected_letter:
                self._handle_command(detected_class, detected_letter, confidence, is_custom)
            
            # Slide buffer
            shift = int(samples * (1 - VOICE_OVERLAP))
            self.buffer[:shift] = self.buffer[-shift:]
            self.position = shift
    
    def _handle_command(self, class_name, letter, confidence, is_custom=False):
        """Execute voice command."""
        display_text = f"{class_name}→{letter}"
        if is_custom:
            display_text = f"[CUSTOM] {display_text}"
        
        self.signals.voice_command_signal.emit(display_text, confidence)
        
        if self.cooldown_active or self.action_lock.locked():
            return
        
        # Send the letter as command
        self.executor.send_command(letter)
        
        self.signals.log_signal.emit(f"Voice: {class_name} → {letter}", "info")
    def _start_cooldown(self):
        """Start cooldown after command."""
        self.cooldown_active = True
        threading.Thread(target=self._cooldown_timer, daemon=True).start()
    
    def _cooldown_timer(self):
        """Cooldown timer."""
        import time
        time.sleep(COOLDOWN_TIME)
        self.cooldown_active = False

    def add_custom_voice(self, name, embeddings, letter):
        """Add a new custom voice command."""
        self.custom_voice_manager.add_voice(name, embeddings, letter)
        self.signals.log_signal.emit(f"Custom voice command added: {name} → {letter}", "success")
    
    def remove_custom_voice(self, name):
        """Remove a custom voice command."""
        self.custom_voice_manager.remove_voice(name)
        self.signals.log_signal.emit(f"Custom voice command removed: {name}", "info")
    
    def get_custom_voices(self):
        """Get all custom voice command names."""
        return self.custom_voice_manager.get_all_voices()