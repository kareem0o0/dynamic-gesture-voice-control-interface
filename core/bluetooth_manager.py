"""
Bluetooth connection manager with virtual connection support.
"""

import time
import serial
import socket
import threading
import platform

from config import BLUETOOTH_PORT, BLUETOOTH_BAUD
from .virtual_bluetooth import VirtualBluetoothConnection


class BluetoothManager:
    """Manages Bluetooth connections via serial, socket, or virtual."""
    
    # Connection timeouts
    SERIAL_TIMEOUT = 2.0  # seconds
    SOCKET_TIMEOUT = 10.0  # seconds
    RECONNECT_ATTEMPTS = 3
    RECONNECT_DELAY = 2.0  # seconds
    
    def __init__(self, signal_emitter):
        self.signals = signal_emitter
        self.connection = None
        self.lock = threading.Lock()
        self.connection_type = None  # 'serial', 'socket', or 'virtual'
        self.last_connection_params = None  # Store for reconnection
        self.is_reconnecting = False
    
    def connect_serial(self, port=BLUETOOTH_PORT, baud=BLUETOOTH_BAUD):
        """
        Connect via serial port (after rfcomm bind).
        
        Args:
            port: Serial port path
            baud: Baud rate
            
        Returns:
            True if successful, False otherwise
        """
        with self.lock:
            try:
                if self.connection:
                    self.disconnect()
                
                self.signals.log_signal.emit(f"Connecting to {port}...", "info")
                
                # Attempt connection with timeout
                self.connection = serial.Serial(
                    port, 
                    baud, 
                    timeout=self.SERIAL_TIMEOUT,
                    write_timeout=self.SERIAL_TIMEOUT
                )
                self.connection_type = 'serial'
                
                # Wait for connection to stabilize
                time.sleep(2)
                
                # Verify connection is working
                if not self._verify_serial_connection():
                    raise Exception("Serial connection verification failed")
                
                # Store connection params for reconnection
                self.last_connection_params = {'type': 'serial', 'port': port, 'baud': baud}
                
                self.signals.log_signal.emit(f"Connected to {port}", "success")
                self.signals.status_signal.emit("Connected")
                return True
            
            except serial.SerialException as e:
                error_msg = f"Serial connection error: {e}"
                self.signals.log_signal.emit(error_msg, "error")
                self.signals.log_signal.emit("Check: Device exists, permissions, not in use", "warning")
                self.signals.status_signal.emit("Disconnected")
                self.connection = None
                return False
            
            except Exception as e:
                self.signals.log_signal.emit(f"Connection error: {e}", "error")
                self.signals.status_signal.emit("Disconnected")
                self.connection = None
                return False
    
    def _verify_serial_connection(self):
        """Verify serial connection is working."""
        try:
            if not self.connection or not self.connection.is_open:
                return False
            # Connection is open and ready
            return True
        except Exception:
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
        with self.lock:
            try:
                if self.connection:
                    self.disconnect()
                
                self.signals.log_signal.emit(f"Connecting to {mac_address}:{channel}...", "info")
                
                sock = None
                
                # Preferred: use native AF_BLUETOOTH RFCOMM sockets (Linux / modern BSDs)
                try:
                    sock = socket.socket(socket.AF_BLUETOOTH,
                                           socket.SOCK_STREAM,
                                           socket.BTPROTO_RFCOMM)
                    # Set timeout for connection attempt
                    sock.settimeout(self.SOCKET_TIMEOUT)
                    sock.connect((mac_address, channel))
                    
                except (AttributeError, OSError) as e:
                    # socket.AF_BLUETOOTH not available or unsupported on this platform.
                    # Try a PyBluez fallback if available (works on Windows with appropriate drivers).
                    if sock:
                        try:
                            sock.close()
                        except:
                            pass
                    
                    try:
                        import bluetooth as _bluetooth  # PyBluez
                        sock = _bluetooth.BluetoothSocket(_bluetooth.RFCOMM)
                        sock.settimeout(self.SOCKET_TIMEOUT)
                        sock.connect((mac_address, channel))
                    except ImportError:
                        msg = (
                            "Direct RFCOMM sockets are not supported on this platform and "
                            "PyBluez is not installed. Use virtual connection or serial/COM bridge instead."
                        )
                        self.signals.log_signal.emit(msg, "error")
                        self.signals.status_signal.emit("Disconnected")
                        return False
                    except Exception as pybluez_error:
                        msg = f"PyBluez connection failed: {pybluez_error}"
                        self.signals.log_signal.emit(msg, "error")
                        self.signals.log_signal.emit("Try: Pair device in system settings first", "warning")
                        self.signals.status_signal.emit("Disconnected")
                        return False
                
                # Verify socket is connected
                if not sock:
                    raise Exception("Socket creation failed")
                
                # Set socket to non-blocking mode after connection
                sock.settimeout(1.0)
                
                # If we get here, sock is a connected socket-like object
                self.connection = sock
                self.connection_type = 'socket'
                
                # Store connection params for reconnection
                self.last_connection_params = {
                    'type': 'socket', 
                    'mac_address': mac_address, 
                    'channel': channel
                }
                
                self.signals.log_signal.emit(f"Connected to {mac_address}:{channel}", "success")
                self.signals.status_signal.emit("Connected")
                return True
            
            except socket.timeout:
                self.signals.log_signal.emit(f"Connection timeout to {mac_address}", "error")
                self.signals.log_signal.emit("Check: Device is powered on and in range", "warning")
                self.signals.status_signal.emit("Disconnected")
                if sock:
                    try:
                        sock.close()
                    except:
                        pass
                return False
            
            except Exception as e:
                self.signals.log_signal.emit(f"Direct socket failed: {e}", "error")
                self.signals.log_signal.emit("Try: Virtual mode for testing or check device pairing", "warning")
                self.signals.status_signal.emit("Disconnected")
                if sock:
                    try:
                        sock.close()
                    except:
                        pass
                return False
    
    def connect_virtual(self):
        """
        Connect via virtual Bluetooth (simulation mode).
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.connection:
                self.disconnect()
            
            self.connection = VirtualBluetoothConnection(self.signals)
            self.connection_type = 'virtual'
            
            success = self.connection.connect()
            if success:
                self.signals.log_signal.emit("Virtual Bluetooth connected (SIMULATION)", "success")
                self.signals.status_signal.emit("Connected")
            
            return success
        
        except Exception as e:
            self.signals.log_signal.emit(f"Virtual connection failed: {e}", "error")
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
                self.signals.log_signal.emit("Not connected - command not sent", "warning")
                return False
            
            try:
                if self.connection_type == 'serial':
                    self.connection.write(command.encode())
                elif self.connection_type == 'socket':
                    self.connection.send(command.encode())
                elif self.connection_type == 'virtual':
                    self.connection.send(command)
                
                self.signals.log_signal.emit(f"Sent: {command}", "info")
                return True
            
            except (serial.SerialException, socket.error, BrokenPipeError, ConnectionResetError) as e:
                self.signals.log_signal.emit(f"Connection lost: {e}", "error")
                self._handle_connection_loss()
                return False
            
            except Exception as e:
                self.signals.log_signal.emit(f"Send error: {e}", "error")
                return False
    
    def _handle_connection_loss(self):
        """Handle unexpected connection loss."""
        self.signals.status_signal.emit("Connection Lost")
        
        # Attempt reconnection if we have stored params
        if self.last_connection_params and not self.is_reconnecting:
            self.signals.log_signal.emit("Attempting to reconnect...", "warning")
            threading.Thread(target=self._reconnect_thread, daemon=True).start()
        else:
            self.disconnect()
    
    def _reconnect_thread(self):
        """Background thread for reconnection attempts."""
        self.is_reconnecting = True
        
        try:
            for attempt in range(self.RECONNECT_ATTEMPTS):
                self.signals.log_signal.emit(
                    f"Reconnection attempt {attempt + 1}/{self.RECONNECT_ATTEMPTS}...", 
                    "info"
                )
                
                time.sleep(self.RECONNECT_DELAY)
                
                params = self.last_connection_params
                success = False
                
                if params['type'] == 'serial':
                    success = self.connect_serial(params['port'], params['baud'])
                elif params['type'] == 'socket':
                    success = self.connect_direct(params['mac_address'], params['channel'])
                
                if success:
                    self.signals.log_signal.emit("Reconnection successful!", "success")
                    return
            
            self.signals.log_signal.emit(
                f"Reconnection failed after {self.RECONNECT_ATTEMPTS} attempts", 
                "error"
            )
            self.disconnect()
        
        finally:
            self.is_reconnecting = False
    
    def disconnect(self):
        """Disconnect from robot."""
        with self.lock:
            if self.connection:
                try:
                    if self.connection_type in ['serial', 'socket']:
                        self.connection.close()
                    elif self.connection_type == 'virtual':
                        self.connection.disconnect()
                    
                    self.signals.log_signal.emit("Disconnected", "info")
                
                except Exception as e:
                    self.signals.log_signal.emit(f"Error during disconnect: {e}", "warning")
                
                finally:
                    self.connection = None
                    self.connection_type = None
                    self.signals.status_signal.emit("Disconnected")
            
            # Don't clear last_connection_params - keep for manual reconnection
    
    def is_connected(self):
        """Check if connected."""
        return self.connection is not None
    
    def is_virtual(self):
        """Check if using virtual connection."""
        return self.connection_type == 'virtual'