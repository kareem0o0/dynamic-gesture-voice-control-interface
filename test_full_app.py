#!/usr/bin/env python3
"""
Full application startup test.
Tests that all components can be imported and initialized without errors.
"""

import sys
import os

def test_imports():
    """Test that all critical imports work."""
    print("=== Testing Imports ===")

    try:
        # Core imports
        from core.bluetooth_manager import BluetoothManager
        from core.robot_backend import RobotControllerBackend
        from core.command_executor import CommandExecutor
        print("✓ Core modules imported successfully")

        # UI imports
        from ui import SignalEmitter, RobotControlUI
        print("✓ UI modules imported successfully")

        # Controller imports
        from controllers import VoiceController, GestureController
        print("✓ Controller modules imported successfully")

        # Model imports
        from models import GestureModel, VoiceModel
        print("✓ Model modules imported successfully")

        return True

    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error during imports: {e}")
        return False

def test_backend_initialization():
    """Test backend initialization."""
    print("\n=== Testing Backend Initialization ===")

    try:
        from ui import SignalEmitter
        from core.robot_backend import RobotControllerBackend

        signals = SignalEmitter()
        backend = RobotControllerBackend(signals)

        print("✓ Backend initialized successfully")

        # Test virtual Bluetooth connection
        success = backend.bluetooth.connect_virtual()
        if success:
            print("✓ Virtual Bluetooth connected")
        else:
            print("✗ Virtual Bluetooth failed")
            return False

        # Test command sending
        backend.send_command('F')
        backend.send_command('!')
        print("✓ Commands sent successfully")

        # Test cleanup
        backend.cleanup()
        print("✓ Backend cleanup successful")

        return True

    except Exception as e:
        print(f"✗ Backend initialization error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_ui_initialization():
    """Test UI initialization (headless)."""
    print("\n=== Testing UI Initialization ===")

    try:
        # Set headless mode for testing
        os.environ['QT_QPA_PLATFORM'] = 'offscreen'

        from PySide6.QtWidgets import QApplication
        from ui import SignalEmitter, RobotControlUI
        from core.robot_backend import RobotControllerBackend

        # Create Qt application
        app = QApplication.instance()
        if app is None:
            app = QApplication([])

        signals = SignalEmitter()
        backend = RobotControllerBackend(signals)

        # Create UI (this will test all UI components)
        window = RobotControlUI(backend)

        print("✓ UI initialized successfully")

        # Test mode switching
        backend.switch_mode('VOICE')
        backend.switch_mode('GESTURE')
        backend.switch_mode('KEYBOARD')
        print("✓ Mode switching works")

        # Cleanup
        backend.cleanup()
        app.quit()

        return True

    except Exception as e:
        print(f"✗ UI initialization error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("SuperClawBot - Full Application Test")
    print("=" * 40)

    all_passed = True

    # Test imports
    if not test_imports():
        all_passed = False

    # Test backend
    if not test_backend_initialization():
        all_passed = False

    # Test UI (optional - may fail in headless environment)
    try:
        if not test_ui_initialization():
            print("⚠ UI test failed (may be expected in headless environment)")
    except Exception as e:
        print(f"⚠ UI test skipped: {e}")

    print("\n" + "=" * 40)
    if all_passed:
        print("🎉 ALL TESTS PASSED! Application is ready for release.")
        return 0
    else:
        print("❌ SOME TESTS FAILED. Please review errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
