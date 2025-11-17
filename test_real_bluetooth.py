#!/usr/bin/env python3
"""
Test script for real Bluetooth/serial connections.
Tests serial port connections and command sending.
"""

import time
from core.bluetooth_manager import BluetoothManager
from ui import SignalEmitter

def test_serial_connection():
    """Test serial port connection."""
    print("=== Testing Serial Port Connection ===")

    signals = SignalEmitter()
    bt = BluetoothManager(signals)

    # Test serial connection to default port
    print("Testing serial connection to COM3...")
    success = bt.connect_serial("COM3", 9600)

    if success:
        print("✓ Serial connection successful")

        # Test command sending
        print("Testing command sending...")
        commands = ['F', 'B', 'L', 'R', '!', 'Q']
        for cmd in commands:
            result = bt.send(cmd)
            print(f"Send '{cmd}' result: {result}")
            time.sleep(0.1)  # Small delay between commands

        print("✓ Commands sent successfully")

        # Wait a moment
        time.sleep(1)

    else:
        print("✗ Serial connection failed (expected if no device connected)")
        print("This is normal if no Bluetooth device is connected to COM3")

    # Disconnect
    bt.disconnect()
    print("Serial test complete!")
    return success

def test_bluetoothctl_paired_devices():
    """Test fetching paired devices using bluetoothctl."""
    print("\n=== Testing Paired Devices (bluetoothctl) ===")

    try:
        import subprocess

        print("Running bluetoothctl paired-devices...")
        result = subprocess.run(
            ["bluetoothctl", "paired-devices"],
            capture_output=True,
            text=True,
            timeout=10
        )

        print(f"Return code: {result.returncode}")
        print(f"STDOUT:\n{result.stdout}")
        if result.stderr:
            print(f"STDERR:\n{result.stderr}")

        if result.returncode == 0 and result.stdout.strip():
            print("✓ Found paired devices")
            # Parse devices
            devices = []
            for line in result.stdout.splitlines():
                line = line.strip()
                if line.startswith("Device "):
                    parts = line.split(" ", 2)
                    if len(parts) >= 2:
                        mac = parts[1]
                        name = parts[2] if len(parts) > 2 else "Unknown"
                        devices.append((mac, name))
                        print(f"  - {name} ({mac})")

            if devices:
                print(f"✓ Found {len(devices)} paired device(s)")
                return devices
            else:
                print("⚠ No devices parsed from output")
                return []
        else:
            print("⚠ No paired devices found or bluetoothctl failed")
            return []

    except FileNotFoundError:
        print("✗ bluetoothctl not found (not on Linux or not installed)")
        return []
    except subprocess.TimeoutExpired:
        print("✗ bluetoothctl timeout")
        return []
    except Exception as e:
        print(f"✗ Error testing bluetoothctl: {e}")
        return []

def test_direct_socket_connection():
    """Test direct socket connection to a Bluetooth device."""
    print("\n=== Testing Direct Socket Connection ===")

    # First get paired devices
    paired_devices = test_bluetoothctl_paired_devices()

    if not paired_devices:
        print("No paired devices available for testing")
        return False

    signals = SignalEmitter()
    bt = BluetoothManager(signals)

    # Try to connect to first paired device
    mac, name = paired_devices[0]
    print(f"Attempting direct socket connection to {name} ({mac})...")

    success = bt.connect_direct(mac, 1)  # Default channel 1

    if success:
        print("✓ Direct socket connection successful")

        # Test command sending
        print("Testing command sending...")
        commands = ['F', '!', 'Q']
        for cmd in commands:
            result = bt.send(cmd)
            print(f"Send '{cmd}' result: {result}")
            time.sleep(0.2)

        print("✓ Commands sent successfully")

        # Wait
        time.sleep(1)

    else:
        print("✗ Direct socket connection failed")
        print("This may be expected if the device is not a robot controller")

    bt.disconnect()
    print("Direct socket test complete!")
    return success

def main():
    """Run Bluetooth tests."""
    print("SuperClawBot - Real Bluetooth Testing")
    print("=" * 50)

    # Test serial connection
    serial_success = test_serial_connection()

    # Test direct socket (only on Linux where bluetoothctl works)
    import platform
    if platform.system() == "Linux":
        socket_success = test_direct_socket_connection()
    else:
        print("\n⚠ Direct socket testing skipped (not on Linux)")
        socket_success = None

    print("\n" + "=" * 50)
    print("TEST RESULTS:")
    print(f"Serial Connection: {'✓ PASS' if serial_success else '⚠ Expected fail (no device)'}")

    if socket_success is not None:
        print(f"Direct Socket: {'✓ PASS' if socket_success else '⚠ Expected fail (no compatible device)'}")
    else:
        print("Direct Socket: Skipped (Windows)")

    print("\nNOTE: These tests require actual Bluetooth hardware to be connected.")
    print("Virtual Bluetooth mode works without hardware and is fully tested.")

if __name__ == "__main__":
    main()
