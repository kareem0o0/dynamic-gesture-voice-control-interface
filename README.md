# SuperClawBot - Unified Robot Controller

A comprehensive robot control system with **keyboard**, **voice**, and **gesture** recognition capabilities. Built with PySide6 and TensorFlow Lite for real-time control and machine learning-based input recognition.

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## Features

### 🎮 Multiple Control Modes
- **Keyboard Control**: WASD for drive, number pad for arm control
- **Voice Control**: Real-time voice command recognition with TensorFlow Lite
- **Gesture Control**: Camera-based gesture recognition with custom gesture training

### 🧠 Machine Learning Integration
- Dynamic TensorFlow Lite model loading
- Custom voice command training
- Custom gesture training with embedding extraction
- Configurable class-to-letter mappings
- Profile management for different model configurations

### 🎨 User Interface
- Modern dark/light theme support
- Real-time video feed for gesture recognition
- Activity logging with color-coded messages
- Intuitive model configuration dialogs
- Bluetooth connection management

### 🔧 Advanced Features
- Bluetooth communication (Serial, Socket, or Virtual mode)
- Save/load complete configurations
- Profile management system
- Frame rate limiting for performance
- Comprehensive error handling

## Installation

### Prerequisites
- Python 3.8 or higher
- Linux (tested on Ubuntu/Debian)
- Camera (for gesture control)
- Microphone (for voice control)
- Bluetooth adapter (for robot communication)

### Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/kareem0o0/dynamic-gesture-voice-control-interface.git
   cd dynamic-gesture-voice-control-interface
   ```

2. **Create a virtual environment (recommended):**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application:**
   ```bash
   python main.py
   ```

## Quick Start

### 1. Connect to Robot
- Open the application
- Go to **Bluetooth Setup** panel
- Choose connection method:
  - **Virtual Mode**: For testing without hardware
  - **Direct Socket**: Connect via Bluetooth MAC address
  - **Serial Port**: Connect via `/dev/rfcomm0` (requires rfcomm setup)

### 2. Load Models
- Go to **Models → Configure Models**
- **Voice Tab**: Load your `.tflite` voice model and `labels.txt`
- **Gesture Tab**: Load your `.tflite` gesture model and `labels.txt`
- Assign letters to each class for robot commands

### 3. Train Custom Commands
- **Custom Voice Commands**: 
  - Click "➕ Add Custom Voice Command"
  - Record multiple samples (recommended: 10 samples)
  - Assign a unique letter
  
- **Custom Gestures**:
  - Click "➕ Add Custom Gesture"
  - Hold gesture steady while camera captures frames
  - Assign a unique letter

### 4. Control the Robot
- **Keyboard Mode**: Use WASD for drive, number pad for arms
- **Voice Mode**: Speak commands that match your voice model classes
- **Gesture Mode**: Show gestures to the camera

## Configuration

### Model Files
Place your TensorFlow Lite models in:
- Voice models: `resources/sound_classifier/`
- Gesture models: `resources/gesture_classifier/`

### Configuration File
Edit `config.py` to customize:
- Bluetooth port and baud rate
- Voice/gesture confidence thresholds
- Training parameters
- UI settings

### Keyboard Controls

**Drive:**
- `W` - Forward
- `S` - Backward
- `A` - Left
- `D` - Right

**Arms:**
- `1` / `4` - Arm 1 Up/Down
- `3` / `6` - Arm 2 Up/Down
- `0` / `2` - Arm 3 Clockwise/Counter-clockwise

**Other:**
- `Q` - Toggle LED
- `ESC` - Emergency Stop (stops all motors)

## Project Structure

```
SuperClawBot/
├── main.py                 # Application entry point
├── config.py              # Configuration and constants
├── requirements.txt       # Python dependencies
│
├── core/                  # Core business logic
│   ├── robot_backend.py   # Main controller backend
│   ├── bluetooth_manager.py
│   ├── command_executor.py
│   ├── model_manager.py
│   ├── profile_manager.py
│   ├── voice_trainer.py
│   └── embedding_extractor.py
│
├── controllers/           # Control mode implementations
│   ├── base_controller.py
│   ├── keyboard_controller.py
│   ├── voice_controller.py
│   └── gesture_controller.py
│
├── models/                # ML model wrappers
│   ├── voice_model.py
│   └── gesture_model.py
│
├── ui/                    # User interface components
│   ├── main_window.py
│   ├── control_panel.py
│   ├── bluetooth_panel.py
│   ├── model_config_dialog.py
│   ├── custom_voice_dialog.py
│   └── custom_gesture_dialog.py
│
├── utils/                 # Utility modules
│   ├── camera.py
│   ├── logger.py
│   └── resource_loader.py
│
└── resources/             # Model files and resources
    ├── sound_classifier/
    └── gesture_classifier/
```

## Troubleshooting

### Camera Not Working
- Check camera permissions
- Verify camera is not being used by another application
- Try different camera indices in `utils/camera.py`

### Microphone Not Working
- Check microphone permissions
- Verify default input device: `python -c "import sounddevice; print(sounddevice.query_devices())"`
- Ensure microphone is not muted in system settings

### Bluetooth Connection Issues
- Use **Virtual Mode** for testing without hardware
- For serial connection, ensure rfcomm is bound: `sudo rfcomm bind 0 <MAC_ADDRESS> 1`
- Check Bluetooth adapter: `hciconfig` or `bluetoothctl`

### Model Loading Errors
- Ensure `.tflite` file and `labels.txt` are in correct directories
- Verify model file format is TensorFlow Lite
- Check file permissions

## Development

### Running in Debug Mode
Set `DEBUG = True` in `config.py` to enable debug logging.

### Contributing
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

This project is open source. See LICENSE file for details.

## Author

**kareem0o0**

## Acknowledgments

- Built with PySide6 for the GUI
- TensorFlow Lite for machine learning inference
- OpenCV for camera and image processing

## Version

**v2.0** - Modular Architecture

---

For issues, questions, or contributions, please open an issue on GitHub.

