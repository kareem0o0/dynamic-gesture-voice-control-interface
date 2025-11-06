# SuperClaw Bot 
**A VEX EDR-Based Robotic Claw with Custom Arduino Control + AI-Powered Multimodal Interface**


*Custom-built robotic arm using VEX EDR educational kit, enhanced with independent servo control, Bluetooth communication, and **three AI-powered control modes**: Keyboard, Voice, and Hand Gestures.*

---
## Overview

**SuperClaw** is a multimodal robotic platform built from a **VEX EDR educational robotics kit**, but upgraded with:
- **Custom Arduino control logic** (replacing VEX default firmware)
- **Bluetooth serial communication**
- **Three independent control modes** via a Python-based unified controller:
  1. **Keyboard Control** (default)
  2. **Voice Command Recognition**
  3. **Real-time Hand Gesture Control**

The system uses **TensorFlow Lite** models for on-device inference, enabling low-latency voice and gesture recognition without cloud dependency.

---

## Hardware Setup

| Component | Description |
|--------|-------------|
| **Base Chassis** | VEX EDR metal frame & wheels |
| **Drive Motors** | 2x Continuous rotation servos (left/right) |
| **Claw Arm** | 3-DOF arm using VEX structural parts |
| **Arm Servos** | 3x Standard servos (joint 1, 2, 3) |
| **Microcontroller** | Arduino Uno (or compatible) |
| **Bluetooth Module** | HC-05 / HC-06 (configured as `/dev/rfcomm0`) |
| **Power** | 7.4V LiPo or a 12v power suply with a buck converter|
| **LED Indicator** | Onboard LED on pin 13 |

> **Note**: All servos are modified or configured for **continuous rotation** where needed. Drive motors use **reversed polarity logic** in code.

---

## Software Architecture

```
Arduino (Robot Brain)
     ↓ (Bluetooth Serial)
Python Controller (PC/Raspberry Pi)
     ├── Keyboard Listener
     ├── Voice Recognition (TFLite + sounddevice)
     └── Gesture Recognition (TFLite + OpenCV)
```

---

## Arduino Firmware (`superclaw_arduino.ino`)

### Pin Mapping

| Function | Arduino Pin | Servo |
|--------|-------------|-------|
| Left Motor | `3` | Continuous |
| Right Motor | `5` | Continuous |
| Arm Joint 1 | `6` | Standard |
| Arm Joint 2 | `9` | Standard |
| Arm Joint 3 | `10` |  Standard |
| Status LED | `13` | Built-in |

### Command Protocol (Single Char over Serial)

| Command | Action |
|-------|--------|
| `F` | Drive **forward** 
| `B` | Drive **backward** 
| `L` | Turn left |
| `R` | Turn right |
| `0` | Stop drive |
| `A` | Arm1 down (reversed) |
| `Z` | Arm1 up (reversed) |
| `a` | Stop Arm1 |
| `S` | Arm2 down |
| `X` | Arm2 up |
| `s` | Stop Arm2 |
| `C` | Arm3 clockwise |
| `V` | Arm3 counter-clockwise |
| `c` | Stop Arm3 |
| `Q` | Toggle LED |
| `!` | **EMERGENCY STOP ALL** |

> **Why reversed?**  
> Due to motor mounting orientation, forward motion required inverted logic. All directions are **re-mapped in code** for intuitive control.

### Key Features

- **State tracking**: Only stops motors that are moving
- **Non-blocking serial**: Processes one command per loop
- **Robust stop logic**: `stopAll()` resets all flags
- **Servo range**: `60°` (reverse), `90°` (stop), `120°` (forward)

---

## Dependencies 


```bash
pip install pyserial opencv-python pillow tflite-runtime pynput sounddevice numpy
```

> **Raspberry Pi / Linux**: Ensure `python3-opencv`, `libatlas-base-dev`, and microphone access.

---

### Control Modes

| Mode | Trigger | Description |
|------|--------|-----------|
| **Keyboard** | Default | Arrow keys + numpad |
| **Voice** | Press `a` | Speak commands like "forward", "up", "stop" |
| **Gesture** | Press `SPACE` | Show hand signs in front of camera |

> **ESC** = Emergency stop + exit (all modes)

---

### Keyboard Controls

| Key | Action |
|-----|--------|
| ↑ ↓ ← → | Drive |
| `1` / `4` | Arm1 up/down |
| `3` / `6` | Arm2 up/down |
| `0` / `2` | Arm3 rotate |
| `Q` | Toggle LED |
| `a` | Toggle Voice Mode |
| `SPACE` | Toggle Gesture Mode |
| `ESC` | Emergency Stop & Exit |

---

### Voice Commands (TFLite Audio Classifier)

| Spoken Word | Action | Duration |
|------------|--------|----------|
| `forward` | Move backward (`F`) | 3 sec |
| `backward` | Move forward (`B`) | 3 sec |
| `left` / `right` | Turn | 3 sec |
| `up` / `down` | Arm1 | 3 sec |
| `2up` / `2down` | Arm2 | 3 sec |
| `clockwise` / `anti` | Arm3 rotate | 3 sec |
| `stop` | **Immediate full stop** | — |
| `clap` | Toggle LED | — |

> Model: `soundclassifier_with_metadata.tflite`  
> Confidence threshold: **70%**

---

### Gesture Commands (TFLite Vision Model)

| Gesture | Action |
|--------|--------|
| `start` | Begin moving in **current direction** |
| `stop` | Stop + **toggle direction** (F ↔ B) |

> Model: `model.tflite` (224x224 input)  
> Cooldown: **1 second** between commands  
> Camera auto-detected (index 0–4)

---

## Configuration (`SuperClawBot_full_control.py`)

All settings are at the top of the Python file:

```python
# Bluetooth
PORT = "/dev/rfcomm0"
BAUD = 9600

# Voice
VOICE_MODEL = "sound_classifier/soundclassifier_with_metadata.tflite"
VOICE_LABELS = "sound_classifier/labels.txt"
VOICE_SAMPLE_RATE = 44100
VOICE_CONFIDENCE_THRESHOLD = 0.7

# Gesture
GESTURE_MODEL = "gesture_classifier/model.tflite"
GESTURE_LABELS = "gesture_classifier/labels.txt"
GESTURE_CONFIDENCE_THRESHOLD = 0.7
GESTURE_COOLDOWN = 1.0

# Timing
COMMAND_DURATION = 3.0   # Voice command length
COOLDOWN_TIME = 1.0      # After "stop"
```

> **Tip**: Pair Bluetooth once:
> ```bash
> sudo rfcomm bind 0 XX:XX:XX:XX:XX:XX 1
> ```

---
## 📂 Project Structure

```
SuperClawBot/
├── 🧠 AI_Models/
│   ├── pure_audio_model.py              # Voice command classifier (TFLite training)
│   ├── pure_vision_gesture_model.py     # Hand gesture recognition model (TFLite training)
│   ├── gesture_classifier/              # Trained gesture model + labels
│   │   ├── model.tflite
│   │   └── labels.txt
│   └── sound_classifier/                # Trained audio model + labels
│       ├── soundclassifier_with_metadata.tflite
│       └── labels.txt
│
├── 🤖 Robot_Control/
│   ├── SuperClawBot_full_control.py     # Unified controller: keyboard + voice + gesture
│   ├── SuperClawBot_key_control.py      # Keyboard-only (lightweight/debug)
│   ├── SuperClawBot_sound_key_control.py# Voice + keyboard hybrid control
│   ├── SuperClawBot_gesture_key_control.py # Gesture + keyboard hybrid mode
│   └── UART_audio_com.py                # UART audio streaming test (no Bluetooth)
│
├── 🔧 Arduino/
│   └── arduino_control.ino              # Servo control + Bluetooth command parser
│
├── 📘 Docs/
│   └── Bluetooth_Setup.txt              # HC-05/06 pairing and rfcomm binding guide
│
├── requirements.txt                     # Dependencies (pyserial, opencv, tflite-runtime, etc.)
└── README.md                            # Project documentation
```
---
## File Roles

| File | Purpose |
|------|--------|
| `arduino_control.ino` | Low-level robot control: reads serial commands, drives 5 servos (2 drive + 3 arm), LED toggle, emergency stop |
| `Bluetooth_Setup.txt` | Instructions to configure HC-05/06 module and bind to `/dev/rfcomm0` on Linux/Raspberry Pi |
| `pure_audio_model.py` | Script to train and export a TFLite audio classifier from labeled sound clips |
| `pure_vision_gesture_model.py` | Script to train and export a TFLite vision model for hand gesture recognition |
| `SuperClawBot_full_control.py` | **Primary controller** — integrates keyboard, voice, and gesture inputs with mode switching |
| `SuperClawBot_gesture_key_control.py` | Hybrid control: gestures start/stop motion, keyboard adjusts direction/speed |
| `SuperClawBot_key_control.py` | Minimal keyboard-only interface for testing and debugging |
| `SuperClawBot_sound_key_control.py` | Voice commands with real-time keyboard override support |
| `UART_audio_com.py` | Debug utility: streams raw audio over serial (bypasses AI and Bluetooth) |

---
## AI Models

### 1. **Voice Classifier**
- Trained on custom dataset (or AudioSet subset)
- Input: 1-second MFCC spectrograms
- Output: 12 classes (including background)
- Metadata included (TFLite Micro compatible)

### 2. **Gesture Classifier**
- MobileNetV2-based
- Input: 224×224 RGB image
- Output: `start`, `stop`, `background`
- Optimized for edge (Raspberry Pi, Jetson Nano)

> Place models in:
> ```
> sound_classifier/
>   ├── soundclassifier_with_metadata.tflite
>   └── labels.txt
> gesture_classifier/
>   ├── model.tflite
>   └── labels.txt
> ```

---


---

## Setup Guide

### 1. Flash Arduino
```bash
# Use Arduino IDE
# Select board: Arduino Uno
# Upload superclaw_arduino.ino
```

### 2. Pair Bluetooth
```bash
sudo bluetoothctl
scan on
pair XX:XX:XX:XX:XX:XX
trust XX:XX:XX:XX:XX:XX
exit
sudo rfcomm bind 0 XX:XX:XX:XX:XX:XX 1
```

### 3. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run Controller
```bash
python3 python/controller.py
```

---

## Troubleshooting

| Issue | Solution |
|------|----------|
| `Serial port not found` | Check `ls /dev/rfcomm*`, rebind Bluetooth |
| No voice detected | Test mic: `arecord -l`, lower threshold |
| Camera not opening | Try `cv2.VideoCapture(0)` manually |
| Servos jittering | Use external power, add capacitors |
| Commands delayed | Reduce `COMMAND_DURATION` or increase baud |

---

## Future Enhancements

- [ ] Add **autonomous navigation** (line following / obstacle avoidance)
- [ ] Web interface (Flask + WebRTC)
- [ ] ROS2 integration
- [ ] Train **custom gesture set** (grab, release, wave)
- [ ] Battery monitoring via ADC

---

## License

```
MIT License
```
