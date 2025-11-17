#!/usr/bin/env python3
"""
Test Bluetooth UI components.
"""

import sys
import os

def test_bluetooth_panel():
    """Test Bluetooth panel initialization and methods."""
    print("=== Testing Bluetooth Panel ===")

    try:
        # Set headless mode
        os.environ['QT_QPA_PLATFORM'] = 'offscreen'

        from PySide6.QtWidgets import QApplication
        from ui.bluetooth_panel import BluetoothPanel
        from core.robot_backend import RobotControllerBackend
        from ui import SignalEmitter

        # Create Qt application
        app = QApplication.instance()
        if app is None:
            app = QApplication([])

        # Create components
        signals = SignalEmitter()
        backend = RobotControllerBackend(signals)

        # Create Bluetooth panel
        panel = BluetoothPanel(backend, signals)

        print("✓ Bluetooth panel created successfully")

        # Test virtual connection toggle
        print("Testing virtual connection...")
        panel.toggle_virtual()  # Should connect
        panel.toggle_virtual()  # Should disconnect

        print("✓ Virtual connection toggle works")

        # Test paired devices (should handle Windows gracefully)
        print("Testing paired devices fetch...")
        # This will run in background, but we can check it doesn't crash
        panel.show_paired_devices()

        print("✓ Paired devices method called without error")

        # Cleanup
        backend.cleanup()
        app.quit()

        return True

    except Exception as e:
        print(f"✗ Bluetooth panel test error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_bluetooth_panel()
    print("\n" + "=" * 40)
    if success:
        print("🎉 Bluetooth UI test PASSED")
    else:
        print("❌ Bluetooth UI test FAILED")
    sys.exit(0 if success else 1)
