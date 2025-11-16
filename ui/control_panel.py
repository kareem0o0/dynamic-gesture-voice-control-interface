"""
Manual control panel UI component.
"""

from PySide6.QtWidgets import QGroupBox, QGridLayout, QPushButton, QLabel, QVBoxLayout
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt

from config import STOP_DRIVE, STOP_ARM1, STOP_ARM2, STOP_ARM3, STOP_ALL, TOGGLE_LED


class ControlPanel(QGroupBox):
    """Manual control buttons for robot."""
    
    def __init__(self, backend, parent=None):
        super().__init__("🕹️ Manual Controls", parent)
        self.backend = backend
        self.all_buttons = []  # Store all button references
        self._init_ui()
    
    def _init_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout()
        
        # Drive controls section
        drive_group = QGroupBox("🚗 Drive Controls")
        drive_layout = QGridLayout()
        
        btn_forward = QPushButton("⬆️ Forward")
        btn_forward.pressed.connect(lambda: self.backend.send_command('F'))
        btn_forward.released.connect(lambda: self.backend.send_command(STOP_DRIVE))
        drive_layout.addWidget(btn_forward, 0, 1)
        self.all_buttons.append(btn_forward)
        
        btn_left = QPushButton("⬅️ Left")
        btn_left.pressed.connect(lambda: self.backend.send_command('L'))
        btn_left.released.connect(lambda: self.backend.send_command(STOP_DRIVE))
        drive_layout.addWidget(btn_left, 1, 0)
        self.all_buttons.append(btn_left)
        
        btn_stop = QPushButton("⏹️ STOP")
        btn_stop.setStyleSheet("background: #ff4444; font-weight: bold; color: white;")
        btn_stop.clicked.connect(lambda: self.backend.send_command(STOP_ALL))
        drive_layout.addWidget(btn_stop, 1, 1)
        self.all_buttons.append(btn_stop)
        
        btn_right = QPushButton("➡️ Right")
        btn_right.pressed.connect(lambda: self.backend.send_command('R'))
        btn_right.released.connect(lambda: self.backend.send_command(STOP_DRIVE))
        drive_layout.addWidget(btn_right, 1, 2)
        self.all_buttons.append(btn_right)
        
        btn_backward = QPushButton("⬇️ Backward")
        btn_backward.pressed.connect(lambda: self.backend.send_command('B'))
        btn_backward.released.connect(lambda: self.backend.send_command(STOP_DRIVE))
        drive_layout.addWidget(btn_backward, 2, 1)
        self.all_buttons.append(btn_backward)
        
        drive_group.setLayout(drive_layout)
        layout.addWidget(drive_group)
        
        # Arm controls section
        arm_group = QGroupBox("🦾 Arm Controls")
        arm_group.setCheckable(True)
        arm_group.setChecked(True)  # Start expanded (checked = expanded)
        arm_group.setCollapsible(True)
        arm_layout = QGridLayout()
        
        # Arm 1 - Column 0
        arm1_label = QLabel("Arm 1")
        arm1_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        arm_layout.addWidget(arm1_label, 0, 0)
        
        btn_arm1_up = QPushButton("⬆️ Up")
        btn_arm1_up.pressed.connect(lambda: self.backend.send_command('Z'))
        btn_arm1_up.released.connect(lambda: self.backend.send_command(STOP_ARM1))
        arm_layout.addWidget(btn_arm1_up, 1, 0)
        self.all_buttons.append(btn_arm1_up)
        
        btn_arm1_down = QPushButton("⬇️ Down")
        btn_arm1_down.pressed.connect(lambda: self.backend.send_command('A'))
        btn_arm1_down.released.connect(lambda: self.backend.send_command(STOP_ARM1))
        arm_layout.addWidget(btn_arm1_down, 2, 0)
        self.all_buttons.append(btn_arm1_down)
        
        # Arm 2 - Column 1
        arm2_label = QLabel("Arm 2")
        arm2_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        arm_layout.addWidget(arm2_label, 0, 1)
        
        btn_arm2_up = QPushButton("⬆️ Up")
        btn_arm2_up.pressed.connect(lambda: self.backend.send_command('S'))
        btn_arm2_up.released.connect(lambda: self.backend.send_command(STOP_ARM2))
        arm_layout.addWidget(btn_arm2_up, 1, 1)
        self.all_buttons.append(btn_arm2_up)
        
        btn_arm2_down = QPushButton("⬇️ Down")
        btn_arm2_down.pressed.connect(lambda: self.backend.send_command('X'))
        btn_arm2_down.released.connect(lambda: self.backend.send_command(STOP_ARM2))
        arm_layout.addWidget(btn_arm2_down, 2, 1)
        self.all_buttons.append(btn_arm2_down)
        
        # Arm 3 - Column 2
        arm3_label = QLabel("Arm 3")
        arm3_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        arm_layout.addWidget(arm3_label, 0, 2)
        
        btn_arm3_cw = QPushButton("↻ CW")
        btn_arm3_cw.pressed.connect(lambda: self.backend.send_command('C'))
        btn_arm3_cw.released.connect(lambda: self.backend.send_command(STOP_ARM3))
        arm_layout.addWidget(btn_arm3_cw, 1, 2)
        self.all_buttons.append(btn_arm3_cw)
        
        btn_arm3_ccw = QPushButton("↺ CCW")
        btn_arm3_ccw.pressed.connect(lambda: self.backend.send_command('V'))
        btn_arm3_ccw.released.connect(lambda: self.backend.send_command(STOP_ARM3))
        arm_layout.addWidget(btn_arm3_ccw, 2, 2)
        self.all_buttons.append(btn_arm3_ccw)
        
        arm_group.setLayout(arm_layout)
        layout.addWidget(arm_group)
        
        # LED toggle
        btn_led = QPushButton("💡 Toggle LED")
        btn_led.clicked.connect(lambda: self.backend.send_command(TOGGLE_LED))
        layout.addWidget(btn_led)
        self.all_buttons.append(btn_led)
        
        self.setLayout(layout)
    
    def refresh_theme(self):
        """Refresh button styles after theme change."""
        # Force style update for all buttons except STOP
        for button in self.all_buttons:
            if "STOP" not in button.text():
                # Clear inline styles to use palette
                button.setStyleSheet("")