"""
Manual control panel UI component.
"""

from PySide6.QtWidgets import QGroupBox, QGridLayout, QPushButton, QLabel
from PySide6.QtGui import QFont

from config import STOP_DRIVE, STOP_ARM1, STOP_ARM2, STOP_ARM3, STOP_ALL, TOGGLE_LED


class ControlPanel(QGroupBox):
    """Manual control buttons for robot."""
    
    def __init__(self, backend, parent=None):
        super().__init__("🕹️ Manual Controls", parent)
        self.backend = backend
        self._init_ui()
    
    def _init_ui(self):
        """Initialize UI components."""
        layout = QGridLayout()
        
        # Drive controls
        drive_label = QLabel("Drive:")
        drive_label.setFont(QFont("Arial", 10, QFont.Bold))
        layout.addWidget(drive_label, 0, 0, 1, 3)
        
        btn_forward = QPushButton("⬆️ Forward")
        btn_forward.pressed.connect(lambda: self.backend.send_command('F'))
        btn_forward.released.connect(lambda: self.backend.send_command(STOP_DRIVE))
        layout.addWidget(btn_forward, 1, 1)
        
        btn_left = QPushButton("⬅️ Left")
        btn_left.pressed.connect(lambda: self.backend.send_command('L'))
        btn_left.released.connect(lambda: self.backend.send_command(STOP_DRIVE))
        layout.addWidget(btn_left, 2, 0)
        
        btn_stop = QPushButton("⏹️ STOP")
        btn_stop.setStyleSheet("background: #ff4444; font-weight: bold;")
        btn_stop.clicked.connect(lambda: self.backend.send_command(STOP_ALL))
        layout.addWidget(btn_stop, 2, 1)
        
        btn_right = QPushButton("➡️ Right")
        btn_right.pressed.connect(lambda: self.backend.send_command('R'))
        btn_right.released.connect(lambda: self.backend.send_command(STOP_DRIVE))
        layout.addWidget(btn_right, 2, 2)
        
        btn_backward = QPushButton("⬇️ Backward")
        btn_backward.pressed.connect(lambda: self.backend.send_command('B'))
        btn_backward.released.connect(lambda: self.backend.send_command(STOP_DRIVE))
        layout.addWidget(btn_backward, 3, 1)
        
        # Arm controls
        arm_label = QLabel("Arms:")
        arm_label.setFont(QFont("Arial", 10, QFont.Bold))
        layout.addWidget(arm_label, 4, 0, 1, 3)
        
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
            layout.addWidget(btn, 5 + i // 3, i % 3)
        
        # LED toggle
        btn_led = QPushButton("💡 Toggle LED")
        btn_led.clicked.connect(lambda: self.backend.send_command(TOGGLE_LED))
        layout.addWidget(btn_led, 8, 0, 1, 3)
        
        self.setLayout(layout)