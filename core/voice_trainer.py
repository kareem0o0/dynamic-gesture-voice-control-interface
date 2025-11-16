"""
Voice auto-training using spectrogram embeddings.
"""

import numpy as np
import sounddevice as sd
from scipy import signal
import io
from PIL import Image

from config import VOICE_TRAINING_DURATION, VOICE_SAMPLE_RATE, DEBUG


class VoiceTrainer:
    """Handles voice sample recording and spectrogram generation."""
    
    def __init__(self):
        self.sample_rate = VOICE_SAMPLE_RATE
        self.duration = VOICE_TRAINING_DURATION
        self.recording = False
        self.current_recording = None
    
    def record_sample(self):
        """
        Record a voice sample.
        
        Returns:
            Numpy array of audio data, or None on error
        """
        try:
            if DEBUG:
                print(f"DEBUG: record_sample() - Recording {self.duration} seconds of audio at {self.sample_rate} Hz...")
            
            # Check if audio device is available
            try:
                devices = sd.query_devices()
                default_input = sd.default.device[0]
                if default_input is None:
                    raise Exception("No default input device found. Please configure your microphone.")
                if DEBUG:
                    print(f"DEBUG: Using input device: {devices[default_input]['name']}")
            except Exception as e:
                if DEBUG:
                    print(f"DEBUG: Audio device check failed: {e}")
                raise
            
            if DEBUG:
                print("DEBUG: Starting sd.rec()...")
            audio_data = sd.rec(
                int(self.duration * self.sample_rate),
                samplerate=self.sample_rate,
                channels=1,
                dtype='float32'
            )
            if DEBUG:
                print("DEBUG: Waiting for recording to finish...")
            sd.wait()  # Wait until recording is finished
            if DEBUG:
                print("DEBUG: Recording complete")
            
            if audio_data is None or len(audio_data) == 0:
                raise Exception("No audio data recorded. Check microphone connection.")
            
            flattened = audio_data.flatten()
            if DEBUG:
                print(f"DEBUG: Audio data shape: {audio_data.shape}, flattened length: {len(flattened)}")
            return flattened
        
        except Exception as e:
            error_msg = f"Error recording audio: {e}"
            if DEBUG:
                print(f"DEBUG: {error_msg}")
                import traceback
                traceback.print_exc()
            raise  # Re-raise so thread can catch it
    
    def generate_spectrogram(self, audio_data):
        """
        Generate spectrogram from audio data.
        
        Args:
            audio_data: Numpy array of audio samples
            
        Returns:
            Spectrogram as numpy array (image-like format)
        """
        try:
            # Generate spectrogram using scipy
            frequencies, times, spectrogram = signal.spectrogram(
                audio_data,
                fs=self.sample_rate,
                nperseg=256,
                noverlap=128
            )
            
            # Convert to log scale for better visualization
            spectrogram_db = 10 * np.log10(spectrogram + 1e-10)
            
            # Normalize to 0-255 range
            spec_min = spectrogram_db.min()
            spec_max = spectrogram_db.max()
            
            if spec_max > spec_min:
                normalized = ((spectrogram_db - spec_min) / (spec_max - spec_min) * 255)
            else:
                normalized = np.zeros_like(spectrogram_db)
            
            # Convert to uint8
            spectrogram_image = normalized.astype(np.uint8)
            
            return spectrogram_image
        
        except Exception as e:
            print(f"Error generating spectrogram: {e}")
            return None
    
    def audio_to_embedding(self, audio_data, voice_model):
        """
        Convert audio to embedding using the voice model.
        
        Args:
            audio_data: Numpy array of audio samples
            voice_model: VoiceModel instance
            
        Returns:
            Embedding vector
        """
        try:
            if voice_model is None or not voice_model.is_loaded():
                return None
            
            # Pad or trim to match model's expected input size
            expected_size = voice_model.buffer_size
            
            if len(audio_data) < expected_size:
                # Pad with zeros
                padded = np.zeros(expected_size, dtype=np.float32)
                padded[:len(audio_data)] = audio_data
                audio_data = padded
            elif len(audio_data) > expected_size:
                # Trim
                audio_data = audio_data[:expected_size]
            
            # Normalize
            max_val = np.max(np.abs(audio_data))
            if max_val > 0:
                audio_data = audio_data / max_val
            
            # Get embedding from model (before final classification layer)
            # We'll use the model's predict but extract intermediate output
            input_data = audio_data.reshape(1, -1).astype(np.float32)
            
            inp = voice_model.interpreter.get_input_details()[0]
            voice_model.interpreter.set_tensor(inp['index'], input_data)
            voice_model.interpreter.invoke()
            
            # Get output (this is already an embedding-like representation)
            out = voice_model.interpreter.get_output_details()[0]
            embedding = voice_model.interpreter.get_tensor(out['index'])[0]
            
            return embedding
        
        except Exception as e:
            print(f"Error converting audio to embedding: {e}")
            return None


class CustomVoiceManager:
    """Manages custom voice commands."""
    
    def __init__(self):
        self.custom_voices = {}  # name -> {'embeddings': [], 'letter': str}
    
    def add_voice(self, name, embeddings, letter):
        """
        Add a new custom voice command.
        
        Args:
            name: Voice command name
            embeddings: List of embedding vectors
            letter: Assigned letter
        """
        self.custom_voices[name] = {
            'embeddings': [emb.tolist() for emb in embeddings],
            'letter': letter
        }
    
    def remove_voice(self, name):
        """Remove a custom voice command."""
        if name in self.custom_voices:
            del self.custom_voices[name]
    
    def get_voice_letter(self, name):
        """Get letter assigned to a voice command."""
        if name in self.custom_voices:
            return self.custom_voices[name]['letter']
        return None
    
    def update_letter(self, name, new_letter):
        """Update letter for a custom voice command."""
        if name in self.custom_voices:
            self.custom_voices[name]['letter'] = new_letter
    
    def predict(self, embedding, threshold=0.75):
        """
        Find matching custom voice command.
        
        Args:
            embedding: Current audio embedding
            threshold: Similarity threshold (0-1)
            
        Returns:
            Tuple of (command_name, letter, similarity) or (None, None, 0)
        """
        if embedding is None:
            return None, None, 0
        
        best_match = None
        best_similarity = 0
        
        for name, data in self.custom_voices.items():
            similarities = []
            for stored_emb in data['embeddings']:
                stored_emb_np = np.array(stored_emb)
                similarity = self._cosine_similarity(embedding, stored_emb_np)
                similarities.append(similarity)
            
            avg_similarity = np.mean(similarities)
            
            if avg_similarity > best_similarity:
                best_similarity = avg_similarity
                best_match = name
        
        if best_similarity > threshold:
            return best_match, self.custom_voices[best_match]['letter'], best_similarity
        
        return None, None, 0
    
    def _cosine_similarity(self, a, b):
        """Calculate cosine similarity between two vectors."""
        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        
        if norm_a == 0 or norm_b == 0:
            return 0
        
        return dot_product / (norm_a * norm_b)
    
    def to_dict(self):
        """Convert to dictionary for serialization."""
        return self.custom_voices.copy()
    
    def from_dict(self, data):
        """Load from dictionary."""
        self.custom_voices = data.copy()
    
    def get_all_voices(self):
        """Get list of all custom voice command names."""
        return list(self.custom_voices.keys())