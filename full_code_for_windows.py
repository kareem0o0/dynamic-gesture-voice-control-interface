"""
Unified Robot Controller with UI - Windows Version
Complete integration of Keyboard, Voice, and Gesture control modes
with a modern PySide6 interface.

Author: Unified Control System
Version: 2.0 - Windows Edition
"""

import sys
import cv2
import numpy as np
from PIL import Image, ImageOps
import tflite_runtime.interpreter as tflite
import sounddevice as sd
import threading
import time
import os
import serial
import serial.tools.list_ports
from PySide6.QtWidgets import *
from PySide6.QtCore import Qt, QTimer, Signal, QObject
from PySide6.QtGui import QImage, QPixmap, QFont, QColor, QPalette
import asyncio
from bleak import BleakScanner, BleakClient
import subprocess

# ============================================================
#                    CONFIGURATION SECTION
# ============================================================
def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

# Bluetooth Configuration
BAUD = 9600

# Voice Control Configuration
VOICE_MODEL = resource_path("sound_classifier/soundclassifier_with_metadata.tflite")
VOICE_LABELS = resource_path("sound_classifier/labels.txt")
VOICE_SAMPLE_RATE = 44100
VOICE_OVERLAP = 0.5
VOICE_CONFIDENCE_THRESHOLD = 0.7

# Gesture Control Configuration
GESTURE_MODEL = resource_path("gesture_classifier/model.tflite")
GESTURE_LABELS = resource_path("gesture_classifier/labels.txt")
GESTURE_CONFIDENCE_THRESHOLD = 0.7
GESTURE_COOLDOWN = 1.0

# Action Timing Configuration
COMMAND_DURATION = 2.0
COOLDOWN_TIME = 1.0

# ============================================================
#                    COMMAND MAPPINGS
# ============================================================

# Drive and control commands
STOP_DRIVE = '0'
STOP_ARM1 = 'a'
STOP_ARM2 = 's'
STOP_ARM3 = 'c'
STOP_ALL = '!'
TOGGLE_LED = 'Q'

# Voice command mappings
VOICE_COMMANDS = {
    "forward": ('F', STOP_DRIVE),
    "backward": ('B', STOP_DRIVE),
    "left": ('L', STOP_DRIVE),
    "right": ('R', STOP_DRIVE),
    "up": ('Z', STOP_ARM1),
    "down": ('A', STOP_ARM1),
    "2up": ('S', STOP_ARM2),
    "2down": ('X', STOP_ARM2),
    "clockwise": ('C', STOP_ARM3),
    "anti": ('V', STOP_ARM3),
    "clap": ('Q', None),
    "stop": (STOP_ALL, None),
}

# Gesture command mappings
GESTURE_COMMANDS = {
    "start": 'F',
    "stop": STOP_ALL,
}

# ============================================================
#                    SIGNAL EMITTER
# ============================================================

class SignalEmitter(QObject):
    """Qt signal emitter for thread-safe UI updates."""
    log_signal = Signal(str, str)
    frame_signal = Signal(object)
    mode_signal = Signal(str)
    status_signal = Signal(str)
    voice_command_signal = Signal(str, float)
    gesture_command_signal = Signal(str, float)

# ============================================================
#                    UTILITY FUNCTIONS
# ============================================================

def find_camera(max_tries=5):
    """Auto-detect available camera."""
    for i in range(max_tries):
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)  # DirectShow for Windows
        if cap.isOpened():
            return cap
        cap.release()
    return None

def get_com_ports():
    """Get list of available COM ports."""
    ports = serial.tools.list_ports.comports()
    return [(port.device, port.description) for port in ports]

# ============================================================
#                    ROBOT CONTROLLER BACKEND
# ============================================================

class RobotControllerBackend:
    """Backend controller managing robot communication and AI models."""
    
    def __init__(self, signal_emitter):
        self.signals = signal_emitter
        
        # Serial/Bluetooth
        self.bt = None
        self.bt_lock = threading.Lock()
        self.current_port = None
        
        # Mode control
        self.current_mode = "KEYBOARD"
        self.mode_lock = threading.Lock()
        self.running = True
        
        # Voice components
        self.voice_active = False
        self.voice_stream = None
        self.voice_interpreter = None
        self.voice_labels = []
        self.voice_buffer = None
        self.voice_position = 0
        self.voice_action_lock = threading.Lock()
        self.voice_stop_event = threading.Event()
        self.voice_cooldown_active = False
        
        # Gesture components
        self.gesture_active = False
        self.gesture_thread = None
        self.camera = None
        self.gesture_interpreter = None
        self.gesture_labels = []
        self.last_gesture = None
        self.last_gesture_time = 0
        self.gesture_current_cmd = None
        
        # Active commands for keyboard
        self.active_cmds = {
            'drive': None,
            'arm1': None,
            'arm2': None,
            'arm3': None
        }
        
        # Initialize
        self._init_voice_model()
        self._init_gesture_model()
        self._init_camera()
    
    # ========================================================
    #                  INITIALIZATION
    # ========================================================
    
    def _init_voice_model(self):
        """Initialize voice recognition model."""
        if not os.path.exists(VOICE_MODEL):
            self.signals.log_signal.emit("Voice model not found - Voice control DISABLED", "warning")
            return
        
        try:
            self.voice_interpreter = tflite.Interpreter(VOICE_MODEL)
            self.voice_interpreter.allocate_tensors()
            
            inp = self.voice_interpreter.get_input_details()[0]
            samples = inp['shape'][1]
            self.voice_buffer = np.zeros(samples, dtype=np.float32)
            
            with open(VOICE_LABELS) as f:
                lines = f.readlines()
                self.voice_labels = []
                for line in lines:
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        self.voice_labels.append(parts[-1])
                    elif len(parts) == 1:
                        self.voice_labels.append(parts[0])
            
            self.signals.log_signal.emit(f"Voice model loaded: {len(self.voice_labels)} commands", "success")
        except Exception as e:
            self.signals.log_signal.emit(f"Voice model error: {e}", "error")
            self.voice_interpreter = None
    
    def _init_gesture_model(self):
        """Initialize gesture recognition model."""
        if not os.path.exists(GESTURE_MODEL):
            self.signals.log_signal.emit("Gesture model not found - Gesture control DISABLED", "warning")
            return
        
        try:
            self.gesture_interpreter = tflite.Interpreter(GESTURE_MODEL)
            self.gesture_interpreter.allocate_tensors()
            
            with open(GESTURE_LABELS, "r") as f:
                lines = f.readlines()
                self.gesture_labels = []
                for line in lines:
                    parts = line.strip().split(" ", 1)
                    if len(parts) == 2:
                        self.gesture_labels.append(parts[1])
                    else:
                        self.gesture_labels.append(parts[0])
            
            self.signals.log_signal.emit(f"Gesture model loaded: {len(self.gesture_labels)} gestures", "success")
        except Exception as e:
            self.signals.log_signal.emit(f"Gesture model error: {e}", "error")
            self.gesture_interpreter = None
    
    def _init_camera(self):
        """Initialize camera for gesture control."""
        self.camera = find_camera()
        if not self.camera:
            self.signals.log_signal.emit("No camera found - Gesture control DISABLED", "warning")
        else:
            w, h = int(self.camera.get(3)), int(self.camera.get(4))
            self.signals.log_signal.emit(f"Camera ready: {w}x{h}", "success")
    
    # ========================================================
    #                  SERIAL/BLUETOOTH CONTROL
    # ========================================================
    
    def connect_serial(self, port, baud=9600):
        """Connect to a COM port."""
        try:
            if self.bt and self.bt.is_open:
                self.bt.close()

            self.bt = serial.Serial(port, baud, timeout=1)
            self.current_port = port
            time.sleep(2)
            self.signals.log_signal.emit(f"Connected to {port}", "success")
            self.signals.status_signal.emit("Connected")
            return True
        except Exception as e:
            self.signals.log_signal.emit(f"Connection error: {e}", "error")
            self.signals.status_signal.emit("Disconnected")
            return False
    
    def disconnect(self):
        """Disconnect from current port."""
        with self.bt_lock:
            if self.bt and self.bt.is_open:
                self.bt.close()
                self.bt = None
                self.current_port = None
                self.signals.log_signal.emit("Disconnected", "info")
                self.signals.status_signal.emit("Disconnected")
    
    def send_command(self, cmd):
        """Send command to robot."""
        with self.bt_lock:
            if self.bt and self.bt.is_open:
                try:
                    self.bt.write(cmd.encode())
                    self.signals.log_signal.emit(f"Sent: {cmd}", "info")
                except Exception as e:
                    self.signals.log_signal.emit(f"Send error: {e}", "error")
            else:
                self.signals.log_signal.emit("Not connected - command not sent", "warning")
    
    def stop_all_motors(self):
        """Stop all motors."""
        self.send_command(STOP_ALL)
        self.active_cmds = {k: None for k in self.active_cmds}
        self.gesture_current_cmd = None
        self.signals.log_signal.emit("All motors stopped", "info")
    
    # ========================================================
    #                  MODE SWITCHING
    # ========================================================
    
    def switch_mode(self, new_mode):
        """Switch control mode."""
        with self.mode_lock:
            if self.current_mode == new_mode:
                return
            
            self.signals.log_signal.emit(f"Switching: {self.current_mode} → {new_mode}", "info")
            
            # Stop all motors
            self.stop_all_motors()
            
            # Cleanup old mode
            if self.current_mode == "VOICE":
                self._stop_voice_mode()
            elif self.current_mode == "GESTURE":
                self._stop_gesture_mode()
            
            # Start new mode
            self.current_mode = new_mode
            self.signals.mode_signal.emit(new_mode)
            
            if new_mode == "VOICE":
                self._start_voice_mode()
            elif new_mode == "GESTURE":
                self._start_gesture_mode()
            
            self.signals.log_signal.emit(f"Now in {new_mode} mode", "success")
    
    # ========================================================
    #                  VOICE CONTROL
    # ========================================================
    
    def _start_voice_mode(self):
        """Start voice recognition."""
        if not self.voice_interpreter:
            self.signals.log_signal.emit("Voice mode unavailable", "error")
            return
        
        self.voice_active = True
        self.voice_position = 0
        self.voice_buffer.fill(0)
        self.voice_cooldown_active = False
        
        inp = self.voice_interpreter.get_input_details()[0]
        
        try:
            self.voice_stream = sd.InputStream(
                samplerate=VOICE_SAMPLE_RATE,
                channels=1,
                dtype='float32',
                blocksize=int(VOICE_SAMPLE_RATE * 0.1),
                callback=self._voice_callback
            )
            self.voice_stream.start()
            self.signals.log_signal.emit("Voice recognition active", "success")
        except Exception as e:
            self.signals.log_signal.emit(f"Voice stream error: {e}", "error")
            self.voice_active = False
    
    def _stop_voice_mode(self):
        """Stop voice recognition."""
        self.voice_active = False
        if self.voice_stream:
            self.voice_stream.stop()
            self.voice_stream.close()
            self.voice_stream = None
        self.voice_stop_event.set()
        self.signals.log_signal.emit("Voice recognition stopped", "info")
    
    def _voice_callback(self, indata, frames, time_info, status):
        """Process audio for voice recognition."""
        if not self.voice_active:
            return
        
        chunk = indata[:, 0].copy()
        inp = self.voice_interpreter.get_input_details()[0]
        samples = inp['shape'][1]
        
        n = min(len(chunk), samples - self.voice_position)
        self.voice_buffer[self.voice_position:self.voice_position + n] = chunk[:n]
        self.voice_position += n
        
        if self.voice_position >= samples:
            audio = self.voice_buffer.copy()
            
            max_val = np.max(np.abs(audio))
            if max_val > 0:
                audio /= max_val
            
            x = audio.reshape(1, samples).astype(np.float32)
            self.voice_interpreter.set_tensor(inp['index'], x)
            self.voice_interpreter.invoke()
            
            out = self.voice_interpreter.get_output_details()[0]
            scores = self.voice_interpreter.get_tensor(out['index'])[0]
            
            idx = np.argmax(scores)
            label = self.voice_labels[idx]
            confidence = scores[idx]
            
            if confidence > VOICE_CONFIDENCE_THRESHOLD and label in VOICE_COMMANDS:
                self._handle_voice_command(label, confidence)
            
            shift = int(samples * (1 - VOICE_OVERLAP))
            self.voice_buffer[:shift] = self.voice_buffer[-shift:]
            self.voice_position = shift
    
    def _handle_voice_command(self, label, confidence):
        """Execute voice command."""
        self.signals.voice_command_signal.emit(label, confidence)
        
        if label not in VOICE_COMMANDS:
            return
        
        if label == "stop":
            self.voice_stop_event.set()
            self.send_command(STOP_ALL)
            if self.voice_action_lock.locked():
                self.voice_action_lock.release()
            self.voice_stop_event = threading.Event()
            self._start_voice_cooldown()
            return
        
        if self.voice_cooldown_active or self.voice_action_lock.locked():
            return
        
        self.voice_action_lock.acquire()
        self.voice_stop_event.set()
        self.voice_stop_event = threading.Event()
        
        cmd, stop_cmd = VOICE_COMMANDS[label]
        threading.Thread(
            target=self._execute_voice_action,
            args=(cmd, stop_cmd),
            daemon=True
        ).start()
    
    def _execute_voice_action(self, cmd, stop_cmd):
        """Execute timed voice action."""
        self.send_command(cmd)
        
        if self.voice_stop_event.wait(COMMAND_DURATION):
            pass
        else:
            if stop_cmd:
                self.send_command(stop_cmd)
        
        if self.voice_action_lock.locked():
            self.voice_action_lock.release()
    
    def _start_voice_cooldown(self):
        """Start cooldown after stop."""
        self.voice_cooldown_active = True
        threading.Thread(target=self._voice_cooldown_timer, daemon=True).start()
    
    def _voice_cooldown_timer(self):
        """Cooldown timer."""
        time.sleep(COOLDOWN_TIME)
        self.voice_cooldown_active = False
        self.signals.log_signal.emit("Cooldown complete", "info")
    
    # ========================================================
    #                  GESTURE CONTROL
    # ========================================================
    
    def _start_gesture_mode(self):
        """Start gesture recognition."""
        if not self.gesture_interpreter or not self.camera:
            self.signals.log_signal.emit("Gesture mode unavailable", "error")
            return
        
        self.gesture_active = True
        self.last_gesture = None
        self.last_gesture_time = 0
        self.gesture_current_cmd = None
        
        self.gesture_thread = threading.Thread(
            target=self._gesture_loop,
            daemon=True
        )
        self.gesture_thread.start()
        self.signals.log_signal.emit("Gesture recognition active", "success")
    
    def _stop_gesture_mode(self):
        """Stop gesture recognition."""
        self.gesture_active = False
        
        if self.gesture_current_cmd:
            self.send_command(STOP_ALL)
            self.gesture_current_cmd = None
        
        if self.gesture_thread and self.gesture_thread.is_alive():
            self.gesture_thread.join(timeout=1)
        
        self.signals.log_signal.emit("Gesture recognition stopped", "info")
    
    def _gesture_loop(self):
        """Gesture recognition loop."""
        while self.gesture_active and self.running:
            ret, frame = self.camera.read()
            if not ret or frame is None:
                time.sleep(0.1)
                continue
            
            try:
                # Preprocess
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                image = Image.fromarray(rgb_frame)
                image = ImageOps.fit(image, (224, 224), Image.Resampling.LANCZOS)
                image_array = np.asarray(image, dtype=np.float32)
                normalized = (image_array / 127.5) - 1
                input_data = np.expand_dims(normalized, axis=0)
                
                # Inference
                inp = self.gesture_interpreter.get_input_details()[0]
                out = self.gesture_interpreter.get_output_details()[0]
                
                self.gesture_interpreter.set_tensor(inp['index'], input_data)
                self.gesture_interpreter.invoke()
                prediction = self.gesture_interpreter.get_tensor(out['index'])[0]
                
                idx = np.argmax(prediction)
                gesture = self.gesture_labels[idx]
                confidence = prediction[idx]
                
                # Annotate frame
                cv2.putText(frame, f"Gesture: {gesture}", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                cv2.putText(frame, f"Confidence: {confidence:.2f}", (10, 70),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                if self.gesture_current_cmd:
                    cv2.putText(frame, f"Active: {self.gesture_current_cmd}", (10, 110),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                
                # Send to UI
                self.signals.frame_signal.emit(frame)
                
                # Process command
                if confidence > GESTURE_CONFIDENCE_THRESHOLD:
                    self._handle_gesture_command(gesture, confidence)
                
            except Exception as e:
                self.signals.log_signal.emit(f"Gesture error: {e}", "error")
                continue
    
    def _handle_gesture_command(self, gesture, confidence):
        """Execute gesture command."""
        current_time = time.time()
        
        if current_time - self.last_gesture_time < GESTURE_COOLDOWN:
            return
        
        if gesture == self.last_gesture:
            return
        
        if gesture not in GESTURE_COMMANDS:
            return
        
        cmd = GESTURE_COMMANDS[gesture]
        
        self.signals.gesture_command_signal.emit(gesture, confidence)
        
        if cmd == STOP_ALL:
            self.send_command(STOP_ALL)
            self.gesture_current_cmd = None
        else:
            self.send_command(cmd)
            self.gesture_current_cmd = gesture
        
        self.last_gesture = gesture
        self.last_gesture_time = current_time
    
    # ========================================================
    #                  CLEANUP
    # ========================================================
    
    def cleanup(self):
        """Cleanup resources."""
        self.running = False
        self.stop_all_motors()
        
        if self.current_mode == "VOICE":
            self._stop_voice_mode()
        elif self.current_mode == "GESTURE":
            self._stop_gesture_mode()
        
        if self.camera:
            self.camera.release()
        
        if self.bt and self.bt.is_open:
            self.bt.close()

# ============================================================
#                    MAIN UI WINDOW
# ============================================================

class RobotControlUI(QMainWindow):
    """Main UI window for robot control."""
    
    def __init__(self):
        super().__init__()
        
        # Setup signal emitter and backend
        self.signals = SignalEmitter()
        self.backend = RobotControllerBackend(self.signals)
        
        # Connect signals
        self.signals.log_signal.connect(self.add_log)
        self.signals.frame_signal.connect(self.update_video)
        self.signals.mode_signal.connect(self.update_mode_display)
        self.signals.status_signal.connect(self.update_status)
        self.signals.voice_command_signal.connect(self.show_voice_command)
        self.signals.gesture_command_signal.connect(self.show_gesture_command)
        
        # Bluetooth scanning
        self.bt_devices = []
        self.selected_port = None
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize UI components."""
        self.setWindowTitle("🤖 Unified Robot Controller v2.0 - Windows Edition")
        self.setGeometry(100, 100, 1400, 800)
        
        # Main widget
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        
        # ===== LEFT PANEL: Video + Status =====
        left_panel = QVBoxLayout()
        
        # Video display
        video_group = QGroupBox("📹 Live Camera Feed")
        video_layout = QVBoxLayout()
        
        self.video_label = QLabel("Waiting for camera...")
        self.video_label.setFixedSize(800, 600)
        self.video_label.setStyleSheet("""
            background: #000; 
            border: 3px solid #0078D4; 
            color: white;
            border-radius: 5px;
        """)
        self.video_label.setAlignment(Qt.AlignCenter)
        video_layout.addWidget(self.video_label)
        
        video_group.setLayout(video_layout)
        left_panel.addWidget(video_group)
        
        # Status bar
        status_group = QGroupBox("📊 Status")
        status_layout = QHBoxLayout()
        
        self.connection_status = QLabel("🔴 Disconnected")
        self.connection_status.setFont(QFont("Segoe UI", 11, QFont.Bold))
        status_layout.addWidget(self.connection_status)
        
        self.mode_display = QLabel("Mode: KEYBOARD")
        self.mode_display.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.mode_display.setStyleSheet("color: #0078D4;")
        status_layout.addWidget(self.mode_display)
        
        self.voice_indicator = QLabel("")
        self.voice_indicator.setFont(QFont("Segoe UI", 10))
        status_layout.addWidget(self.voice_indicator)
        
        self.gesture_indicator = QLabel("")
        self.gesture_indicator.setFont(QFont("Segoe UI", 10))
        status_layout.addWidget(self.gesture_indicator)
        
        status_layout.addStretch()
        status_group.setLayout(status_layout)
        left_panel.addWidget(status_group)
        
        main_layout.addLayout(left_panel, 2)
        
        # ===== RIGHT PANEL: Controls =====
        right_panel = QVBoxLayout()
        
        # Bluetooth/Serial Connection Panel
        bt_group = self.create_connection_panel()
        right_panel.addWidget(bt_group)
        
        # Mode selection
        mode_group = QGroupBox("🎮 Control Mode")
        mode_layout = QVBoxLayout()
        
        self.keyboard_btn = QPushButton("⌨️ Keyboard Control")
        self.keyboard_btn.setCheckable(True)
        self.keyboard_btn.setChecked(True)
        self.keyboard_btn.clicked.connect(lambda: self.backend.switch_mode("KEYBOARD"))
        mode_layout.addWidget(self.keyboard_btn)
        
        self.voice_btn = QPushButton("🎤 Voice Control")
        self.voice_btn.setCheckable(True)
        self.voice_btn.clicked.connect(lambda: self.backend.switch_mode("VOICE"))
        mode_layout.addWidget(self.voice_btn)
        
        self.gesture_btn = QPushButton("👋 Gesture Control")
        self.gesture_btn.setCheckable(True)
        self.gesture_btn.clicked.connect(lambda: self.backend.switch_mode("GESTURE"))
        mode_layout.addWidget(self.gesture_btn)
        
        mode_group.setLayout(mode_layout)
        right_panel.addWidget(mode_group)
        
        # Manual controls
        manual_group = QGroupBox("🕹️ Manual Controls")
        manual_layout = QGridLayout()
        
        # Drive controls
        drive_label = QLabel("Drive:")
        drive_label.setFont(QFont("Segoe UI", 10, QFont.Bold))
        manual_layout.addWidget(drive_label, 0, 0, 1, 3)
        
        btn_forward = QPushButton("⬆️ Forward")
        btn_forward.pressed.connect(lambda: self.backend.send_command('F'))
        btn_forward.released.connect(lambda: self.backend.send_command(STOP_DRIVE))
        manual_layout.addWidget(btn_forward, 1, 1)
        
        btn_left = QPushButton("⬅️ Left")
        btn_left.pressed.connect(lambda: self.backend.send_command('L'))
        btn_left.released.connect(lambda: self.backend.send_command(STOP_DRIVE))
        manual_layout.addWidget(btn_left, 2, 0)
        
        btn_stop = QPushButton("⏹️ STOP")
        btn_stop.setStyleSheet("background: #D13438; color: white; font-weight: bold;")
        btn_stop.clicked.connect(lambda: self.backend.send_command(STOP_ALL))
        manual_layout.addWidget(btn_stop, 2, 1)
        
        btn_right = QPushButton("➡️ Right")
        btn_right.pressed.connect(lambda: self.backend.send_command('R'))
        btn_right.released.connect(lambda: self.backend.send_command(STOP_DRIVE))
        manual_layout.addWidget(btn_right, 2, 2)
        
        btn_backward = QPushButton("⬇️ Backward")
        btn_backward.pressed.connect(lambda: self.backend.send_command('B'))
        btn_backward.released.connect(lambda: self.backend.send_command(STOP_DRIVE))
        manual_layout.addWidget(btn_backward, 3, 1)
        
        # Arm controls
        arm_label = QLabel("Arms:")
        arm_label.setFont(QFont("Segoe UI", 10, QFont.Bold))
        manual_layout.addWidget(arm_label, 4, 0, 1, 3)
        
        arm_btns = [
            ("Arm1 Up", 'Z', STOP_ARM1),
            ("Arm1 Down", 'A', STOP_ARM1),
            ("Arm2 Up", 'S', STOP_ARM2),
            ("Arm2 Down", 'X', STOP_ARM2),
            ("Arm3 CW", 'C', STOP_ARM3),
            ("Arm3 CCW", 'V', STOP_ARM3),
        ]
        
        for i, (text, cmd, stop) in enumerate(arm_btns):
            btn = QPushButton(text)
            btn.pressed.connect(lambda c=cmd: self.backend.send_command(c))
            btn.released.connect(lambda s=stop: self.backend.send_command(s))
            manual_layout.addWidget(btn, 5 + i // 3, i % 3)
        
        # LED toggle
        btn_led = QPushButton("💡 Toggle LED")
        btn_led.clicked.connect(lambda: self.backend.send_command(TOGGLE_LED))
        manual_layout.addWidget(btn_led, 8, 0, 1, 3)
        
        manual_group.setLayout(manual_layout)
        right_panel.addWidget(manual_group)
        
        # Command info
        info_group = QGroupBox("ℹ️ Quick Reference")
        info_layout = QVBoxLayout()
        
        info_text = QTextEdit()
        info_text.setReadOnly(True)
        info_text.setMaximumHeight(120)
        info_text.setHtml("""
        <b>Voice Commands:</b><br>
        forward, backward, left, right, stop, up, down, 2up, 2down, clockwise, anti, clap<br><br>
        <b>Gesture Commands:</b><br>
        start (forward), stop (emergency stop)<br><br>
        <b>Keyboard (WASD + Numpad):</b><br>
        W: Forward | S: Backward | A: Left | D: Right | 1/4: Arm1 | 3/6: Arm2 | 0/2: Arm3 | Q: LED
        """)
        info_layout.addWidget(info_text)
        
        info_group.setLayout(info_layout)
        right_panel.addWidget(info_group)
        
        # Log display
        log_group = QGroupBox("📝 Activity Log")
        log_layout = QVBoxLayout()
        
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setMaximumHeight(180)
        log_layout.addWidget(self.log_display)
        
        log_group.setLayout(log_layout)
        right_panel.addWidget(log_group)
        
        right_panel.addStretch()
        main_layout.addLayout(right_panel, 1)
        
        # Add initial log
        self.add_log("UI initialized - Windows Edition", "success")
    
    # ========================================================
    #                  CONNECTION PANEL
    # ========================================================
    
    def create_connection_panel(self):
        """Create the connection setup panel for Windows."""
        conn_group = QGroupBox("📡 Connection Setup")
        conn_layout = QVBoxLayout()
        
        # Status
        self.conn_status = QLabel("Status: Not connected")
        self.conn_status.setStyleSheet("color: #D13438; font-weight: bold;")
        conn_layout.addWidget(self.conn_status)
        
        # Scan buttons
        btn_layout = QHBoxLayout()
        
        scan_serial_btn = QPushButton("🔍 Scan COM Ports")
        scan_serial_btn.clicked.connect(self.scan_serial_ports)
        btn_layout.addWidget(scan_serial_btn)
        
        scan_bt_btn = QPushButton("🔵 Scan Bluetooth (BLE)")
        scan_bt_btn.clicked.connect(self.scan_bluetooth_ble)
        btn_layout.addWidget(scan_bt_btn)
        
        conn_layout.addLayout(btn_layout)
        
        # Device/Port list
        self.port_list = QListWidget()
        self.port_list.itemClicked.connect(self.select_port)
        conn_layout.addWidget(self.port_list)
        
        # Connection controls
        connect_layout = QHBoxLayout()
        
        self.connect_btn = QPushButton("🔌 Connect")
        self.connect_btn.setEnabled(False)
        self.connect_btn.clicked.connect(self.connect_to_device)
        connect_layout.addWidget(self.connect_btn)
        
        self.disconnect_btn = QPushButton("🔌 Disconnect")
        self.disconnect_btn.setEnabled(False)
        self.disconnect_btn.clicked.connect(self.disconnect_device)
        connect_layout.addWidget(self.disconnect_btn)
        
        conn_layout.addLayout(connect_layout)
        
        # Baud rate selector
        baud_layout = QHBoxLayout()
        baud_layout.addWidget(QLabel("Baud Rate:"))
        self.baud_combo = QComboBox()
        self.baud_combo.addItems(["9600", "19200", "38400", "57600", "115200"])
        self.baud_combo.setCurrentText("9600")
        baud_layout.addWidget(self.baud_combo)
        conn_layout.addLayout(baud_layout)
        
        conn_group.setLayout(conn_layout)
        return conn_group
    
    # ========================================================
    #                  CONNECTION METHODS
    # ========================================================
    
    def scan_serial_ports(self):
        """Scan for available COM ports."""
        self.port_list.clear()
        self.conn_status.setText("Scanning COM ports...")
        self.conn_status.setStyleSheet("color: #FF8C00; font-weight: bold;")
        self.add_log("Scanning COM ports...", "info")
        
        ports = get_com_ports()
        
        if not ports:
            self.conn_status.setText("No COM ports found")
            self.conn_status.setStyleSheet("color: #D13438; font-weight: bold;")
            self.add_log("No COM ports detected", "warning")
            return
        
        for port, desc in ports:
            self.port_list.addItem(f"{port} - {desc}")
        
        self.conn_status.setText(f"Found {len(ports)} COM port(s)")
        self.conn_status.setStyleSheet("color: #0078D4; font-weight: bold;")
        self.add_log(f"Found {len(ports)} COM port(s)", "success")
    
    def scan_bluetooth_ble(self):
        """Scan for Bluetooth BLE devices."""
        self.port_list.clear()
        self.conn_status.setText("Scanning Bluetooth devices...")
        self.conn_status.setStyleSheet("color: #FF8C00; font-weight: bold;")
        self.add_log("Starting Bluetooth BLE scan...", "info")
        
        threading.Thread(target=self._scan_ble_thread, daemon=True).start()
    
    def _scan_ble_thread(self):
        """Thread for BLE scanning."""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            devices = loop.run_until_complete(self._discover_ble_devices())
            loop.close()
            
            QTimer.singleShot(0, lambda: self._update_ble_results(devices))
        except Exception as e:
            QTimer.singleShot(0, lambda: self._scan_ble_error(str(e)))
    
    async def _discover_ble_devices(self):
        """Discover BLE devices."""
        devices = await BleakScanner.discover(timeout=10.0)
        return devices
    
    def _update_ble_results(self, devices):
        """Update UI with BLE scan results."""
        self.port_list.clear()
        
        if not devices:
            self.conn_status.setText("No Bluetooth devices found")
            self.conn_status.setStyleSheet("color: #D13438; font-weight: bold;")
            self.add_log("No Bluetooth devices found", "warning")
            return
        
        self.bt_devices = devices
        for device in devices:
            name = device.name or "Unknown Device"
            self.port_list.addItem(f"BLE: {name} ({device.address})")
        
        self.conn_status.setText(f"Found {len(devices)} Bluetooth device(s)")
        self.conn_status.setStyleSheet("color: #0078D4; font-weight: bold;")
        self.add_log(f"Found {len(devices)} Bluetooth device(s)", "success")
        self.add_log("Note: BLE devices may require pairing in Windows Settings", "info")
    
    def _scan_ble_error(self, error):
        """Handle BLE scan error."""
        self.conn_status.setText("Bluetooth scan failed")
        self.conn_status.setStyleSheet("color: #D13438; font-weight: bold;")
        self.add_log(f"Bluetooth scan error: {error}", "error")
        self.add_log("Make sure Bluetooth is enabled in Windows Settings", "warning")
    
    def select_port(self, item):
        """Select a port/device from the list."""
        text = item.text()
        
        if text.startswith("BLE:"):
            # BLE device selected
            self.selected_port = None
            self.add_log("BLE connection not yet implemented - use paired COM port", "warning")
            self.add_log("Pair device in Windows Settings, then scan COM ports", "info")
            self.connect_btn.setEnabled(False)
        else:
            # COM port selected
            self.selected_port = text.split(" - ")[0]
            self.connect_btn.setEnabled(True)
            self.conn_status.setText(f"Selected: {self.selected_port}")
            self.conn_status.setStyleSheet("color: #0078D4; font-weight: bold;")
            self.add_log(f"Selected: {text}", "info")
    
    def connect_to_device(self):
        """Connect to selected device."""
        if not self.selected_port:
            self.add_log("No port selected!", "error")
            return
        
        baud = int(self.baud_combo.currentText())
        self.conn_status.setText(f"Connecting to {self.selected_port}...")
        self.conn_status.setStyleSheet("color: #FF8C00; font-weight: bold;")
        
        threading.Thread(
            target=self._connect_thread,
            args=(self.selected_port, baud),
            daemon=True
        ).start()
    
    def _connect_thread(self, port, baud):
        """Connection thread."""
        success = self.backend.connect_serial(port, baud)
        
        if success:
            QTimer.singleShot(0, lambda: self._connection_success(port))
        else:
            QTimer.singleShot(0, lambda: self._connection_failed("Connection failed"))
    
    def _connection_success(self, port):
        """Handle successful connection."""
        self.conn_status.setText(f"Connected to {port}")
        self.conn_status.setStyleSheet("color: #107C10; font-weight: bold;")
        self.connect_btn.setEnabled(False)
        self.disconnect_btn.setEnabled(True)
        self.add_log(f"Successfully connected to {port}", "success")
    
    def _connection_failed(self, msg):
        """Handle connection failure."""
        self.conn_status.setText("Connection failed")
        self.conn_status.setStyleSheet("color: #D13438; font-weight: bold;")
        self.add_log(f"Connection failed: {msg}", "error")
        self.add_log("Check: Device paired, correct COM port, driver installed", "warning")
    
    def disconnect_device(self):
        """Disconnect from device."""
        self.backend.disconnect()
        self.connect_btn.setEnabled(True)
        self.disconnect_btn.setEnabled(False)
        self.conn_status.setText("Disconnected")
        self.conn_status.setStyleSheet("color: #D13438; font-weight: bold;")
    
    # ========================================================
    #                  UI UPDATE METHODS
    # ========================================================
    
    def add_log(self, message, level="info"):
        """Add log message with color coding."""
        colors = {
            "error": "#D13438",
            "warning": "#FF8C00",
            "success": "#107C10",
            "info": "#0078D4"
        }
        color = colors.get(level, "#0078D4")
        
        timestamp = time.strftime("%H:%M:%S")
        self.log_display.append(
            f'<span style="color:{color};">[{timestamp}] {message}</span>'
        )
        self.log_display.ensureCursorVisible()
    
    def update_video(self, frame):
        """Update live video feed in the UI."""
        if frame is None:
            return
        
        # Convert BGR to RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        height, width, _ = frame_rgb.shape
        bytes_per_line = 3 * width
        q_img = QImage(frame_rgb.data, width, height, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(q_img)
        scaled = pixmap.scaled(self.video_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.video_label.setPixmap(scaled)
    
    def update_mode_display(self, mode):
        """Update current control mode display."""
        self.mode_display.setText(f"Mode: <b>{mode}</b>")
        # Update button checked state
        self.keyboard_btn.setChecked(mode == "KEYBOARD")
        self.voice_btn.setChecked(mode == "VOICE")
        self.gesture_btn.setChecked(mode == "GESTURE")
    
    def update_status(self, status):
        """Update connection status indicator."""
        if status == "Connected":
            self.connection_status.setText("🟢 Connected")
            self.connection_status.setStyleSheet("color: #107C10; font-weight: bold;")
        else:
            self.connection_status.setText("🔴 Disconnected")
            self.connection_status.setStyleSheet("color: #D13438; font-weight: bold;")
    
    def show_voice_command(self, command, confidence):
        """Show recognized voice command with confidence."""
        self.voice_indicator.setText(f"🎤 {command} ({confidence:.2f})")
        QTimer.singleShot(2000, lambda: self.voice_indicator.setText(""))
    
    def show_gesture_command(self, gesture, confidence):
        """Show recognized gesture command."""
        self.gesture_indicator.setText(f"👋 {gesture} ({confidence:.2f})")
        QTimer.singleShot(2000, lambda: self.gesture_indicator.setText(""))
    
    # ========================================================
    #                  KEYBOARD CONTROL
    # ========================================================
    
    def keyPressEvent(self, event):
        """Handle keyboard press for robot control."""
        if self.backend.current_mode != "KEYBOARD":
            return super().keyPressEvent(event)
        
        key = event.key()
        cmd = None
        stop_cmd = None
        
        # Drive controls (WASD)
        if key == Qt.Key_W:
            cmd = 'F'
            stop_cmd = STOP_DRIVE
        elif key == Qt.Key_S:
            cmd = 'B'
            stop_cmd = STOP_DRIVE
        elif key == Qt.Key_A:
            cmd = 'L'
            stop_cmd = STOP_DRIVE
        elif key == Qt.Key_D:
            cmd = 'R'
            stop_cmd = STOP_DRIVE
        
        # Arm 1 (1 / 4)
        elif key == Qt.Key_1:
            cmd = 'Z'
            stop_cmd = STOP_ARM1
        elif key == Qt.Key_4:
            cmd = 'A'
            stop_cmd = STOP_ARM1
        
        # Arm 2 (3 / 6)
        elif key == Qt.Key_3:
            cmd = 'S'
            stop_cmd = STOP_ARM2
        elif key == Qt.Key_6:
            cmd = 'X'
            stop_cmd = STOP_ARM2
        
        # Arm 3 (0 / 2)
        elif key == Qt.Key_0:
            cmd = 'C'
            stop_cmd = STOP_ARM3
        elif key == Qt.Key_2:
            cmd = 'V'
            stop_cmd = STOP_ARM3
        
        # LED toggle
        elif key == Qt.Key_Q:
            self.backend.send_command(TOGGLE_LED)
            return
        
        # Emergency stop
        elif key == Qt.Key_Escape:
            self.backend.stop_all_motors()
            return
        
        if cmd:
            self.backend.active_cmds['drive' if cmd in 'FBLR' else 'arm1' if cmd in 'ZA' else 'arm2' if cmd in 'SX' else 'arm3'] = cmd
            self.backend.send_command(cmd)
    
    def keyReleaseEvent(self, event):
        """Handle key release to stop motors."""
        if self.backend.current_mode != "KEYBOARD":
            return super().keyReleaseEvent(event)
        
        key = event.key()
        stop_cmd = None
        
        if key in (Qt.Key_W, Qt.Key_S, Qt.Key_A, Qt.Key_D):
            stop_cmd = STOP_DRIVE
        elif key in (Qt.Key_1, Qt.Key_4):
            stop_cmd = STOP_ARM1
        elif key in (Qt.Key_3, Qt.Key_6):
            stop_cmd = STOP_ARM2
        elif key in (Qt.Key_0, Qt.Key_2):
            stop_cmd = STOP_ARM3
        
        if stop_cmd:
            # Only stop if this was the active command
            active = self.backend.active_cmds.get('drive' if stop_cmd == STOP_DRIVE else
                                                'arm1' if stop_cmd == STOP_ARM1 else
                                                'arm2' if stop_cmd == STOP_ARM2 else 'arm3')
            if active:
                self.backend.send_command(stop_cmd)
                self.backend.active_cmds['drive' if stop_cmd == STOP_DRIVE else
                                     'arm1' if stop_cmd == STOP_ARM1 else
                                     'arm2' if stop_cmd == STOP_ARM2 else 'arm3'] = None
    
    # ========================================================
    #                  CLEANUP
    # ========================================================
    
    def closeEvent(self, event):
        """Handle window close - clean shutdown."""
        reply = QMessageBox.question(
            self, "Exit", "Are you sure you want to quit?\nAll motors will be stopped.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.backend.cleanup()
            event.accept()
        else:
            event.ignore()


# ============================================================
#                  APPLICATION ENTRY POINT
# ============================================================

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # Modern look
    
    # Windows-style theme
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(240, 240, 240))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(0, 0, 0))
    palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(245, 245, 245))
    palette.setColor(QPalette.ColorRole.Text, QColor(0, 0, 0))
    palette.setColor(QPalette.ColorRole.Button, QColor(240, 240, 240))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(0, 0, 0))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(0, 120, 212))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    
    app.setPalette(palette)
    
    window = RobotControlUI()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()