"""
Bluetooth connection manager.
"""

import time
import serial
import socket
import threading

from config import BLUETOOTH_PORT, BLUETOOTH_BAUD


class BluetoothManager:
    """Manages Bluetooth connections via serial or socket."""
    
    def __init__(self, signal_emitter):
        self.signals = signal_emitter
        self.connection = None
        self.lock = threading.Lock()
        self.connection_type = None  # 'serial' or 'socket'
    
    def connect_serial(self, port=BLUETOOTH_PORT, baud=BLUETOOTH_BAUD):
        """
        Connect via serial port (after rfcomm bind).
        
        Args:
            port: Serial port path
            baud: Baud rate
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.connection:
                self.disconnect()
            
            self.connection = serial.Serial(port, baud, timeout=1)
            self.connection_type = 'serial'
            time.sleep(2)
            
            self.signals.log_signal.emit(f"Connected to {port}", "success")
            self.signals.status_signal.emit("Connected")
            return True
        
        except Exception as e:
            self.signals.log_signal.emit(f"Connection error: {e}", "error")
            self.signals.status_signal.emit("Disconnected")
            return False
    
    def connect_direct(self, mac_address, channel=1):
        """
        Connect via direct RFCOMM socket.
        
        Args:
            mac_address: Bluetooth MAC address
            channel: RFCOMM channel number
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.connection:
                self.disconnect()
            
            sock = socket.socket(socket.AF_BLUETOOTH,
                               socket.SOCK_STREAM,
                               socket.BTPROTO_RFCOMM)
            sock.connect((mac_address, channel))
            
            self.connection = sock
            self.connection_type = 'socket'
            
            self.signals.log_signal.emit(f"Direct socket to {mac_address}", "success")
            self.signals.status_signal.emit("Connected")
            return True
        
        except Exception as e:
            self.signals.log_signal.emit(f"Direct socket failed: {e}", "error")
            self.signals.status_signal.emit("Disconnected")
            return False
    
    def send(self, command):
        """
        Send command to robot.
        
        Args:
            command: Command string to send
        """
        with self.lock:
            if not self.connection:
                return
            
            try:
                if self.connection_type == 'serial':
                    self.connection.write(command.encode())
                elif self.connection_type == 'socket':
                    self.connection.send(command.encode())
                
                self.signals.log_signal.emit(f"Sent: {command}", "info")
            
            except Exception as e:
                self.signals.log_signal.emit(f"Send error: {e}", "error")
    
    def disconnect(self):
        """Disconnect from robot."""
        with self.lock:
            if self.connection:
                try:
                    if self.connection_type == 'serial':
                        self.connection.close()
                    elif self.connection_type == 'socket':
                        self.connection.close()
                except Exception:
                    pass
                
                self.connection = None
                self.connection_type = None
                self.signals.status_signal.emit("Disconnected")
    
    def is_connected(self):
        """Check if connected."""
        return self.connection is not None