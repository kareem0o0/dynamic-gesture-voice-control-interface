#!/usr/bin/env python3
"""
Test script for Bluetooth functionality.
"""

from core.bluetooth_manager import BluetoothManager
from ui import SignalEmitter

def test_virtual_bluetooth():
    """Test virtual Bluetooth connection and command sending."""
    print("=== Testing Virtual Bluetooth ===")

    signals = SignalEmitter()
    bt = BluetoothManager(signals)

    # Test virtual connection
    print("Connecting to virtual Bluetooth...")
    success = bt.connect_virtual()
    print(f"Virtual connect result: {success}")
    print(f"Is connected: {bt.is_connected()}")
    print(f"Is virtual: {bt.is_virtual()}")

    if success:
        # Test command sending
        print("\nTesting command sending...")
        commands = ['F', 'B', 'L', 'R', '!']
        for cmd in commands:
            result = bt.send(cmd)
            print(f"Send '{cmd}' result: {result}")

        # Check history
        history = bt.connection.get_history()
        print(f"\nCommand history: {len(history)} commands")
        print("Last 5 commands:")
        for cmd in history[-5:]:
            print(f"  {cmd['timestamp_str']}: {cmd['command']}")

    # Disconnect
    print("\nDisconnecting...")
    bt.disconnect()
    print("Virtual Bluetooth test complete!")

if __name__ == "__main__":
    test_virtual_bluetooth()
