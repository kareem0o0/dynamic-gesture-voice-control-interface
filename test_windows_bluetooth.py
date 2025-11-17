#!/usr/bin/env python3
"""
Test Windows Bluetooth device enumeration.
"""

import subprocess
import json

def test_powershell_bluetooth():
    """Test PowerShell Bluetooth device enumeration."""
    print("=== Testing Windows PowerShell Bluetooth Enumeration ===")

    try:
        # Use PowerShell to query Bluetooth devices
        ps_command = """
        Get-PnpDevice | Where-Object {
            $_.Class -eq 'Bluetooth' -and
            $_.Status -eq 'OK' -and
            $_.Name -notlike '*Microsoft*' -and
            $_.Name -notlike '*Generic*'
        } | Select-Object Name, DeviceID | ConvertTo-Json
        """

        print("Running PowerShell command...")
        result = subprocess.run(
            ["powershell", "-Command", ps_command],
            capture_output=True,
            text=True,
            timeout=10
        )

        print(f"Return code: {result.returncode}")
        print(f"STDOUT:\n{result.stdout}")
        if result.stderr:
            print(f"STDERR:\n{result.stderr}")

        if result.returncode == 0 and result.stdout.strip():
            try:
                devices_data = json.loads(result.stdout.strip())
                devices = []

                # Handle both single device and array
                if isinstance(devices_data, list):
                    device_list = devices_data
                else:
                    device_list = [devices_data]

                print(f"Found {len(device_list)} potential Bluetooth devices:")

                for device in device_list:
                    name = device.get('Name', 'Unknown')
                    device_id = device.get('DeviceID', '')

                    print(f"  Device: {name}")
                    print(f"  DeviceID: {device_id}")

                    # Extract MAC address from DeviceID (format: BTHLE\Dev_XX:XX:XX:XX:XX:XX)
                    mac_match = None
                    if 'BTHLE\\Dev_' in device_id:
                        mac_part = device_id.split('BTHLE\\Dev_')[-1]
                        if len(mac_part) >= 17:  # XX:XX:XX:XX:XX:XX
                            mac_match = mac_part[:17].replace('_', ':')
                    elif 'BTH\\' in device_id:
                        mac_part = device_id.split('BTH\\')[-1]
                        if len(mac_part) >= 17:
                            mac_match = mac_part[:17].replace('_', ':')

                    if mac_match:
                        print(f"  MAC Address: {mac_match.upper()}")
                        devices.append({
                            "name": name,
                            "mac": mac_match.upper(),
                            "channels": [1],
                            "paired": True
                        })
                    else:
                        print("  MAC Address: Not found"
                print(f"\nSuccessfully parsed {len(devices)} Bluetooth devices")
                return devices

            except json.JSONDecodeError as e:
                print(f"Failed to parse PowerShell output: {e}")
                return []

        else:
            print("PowerShell command failed or returned no data")
            return []

    except FileNotFoundError:
        print("PowerShell not found")
        return []
    except subprocess.TimeoutExpired:
        print("PowerShell timeout")
        return []
    except Exception as e:
        print(f"Error testing PowerShell: {e}")
        return []

if __name__ == "__main__":
    devices = test_powershell_bluetooth()
    print(f"\nResult: Found {len(devices)} paired Bluetooth devices")
    for device in devices:
        print(f"  - {device['name']} ({device['mac']})")
