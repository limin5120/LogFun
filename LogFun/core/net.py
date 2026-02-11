import socket
import struct
import json
import threading
import time
import sys
from .config import get_config
from .registry import get_template_registry, get_function_registry
from .controller import get_controller

PROTO_VERSION = 1
TYPE_HANDSHAKE = 1
TYPE_LOG_DATA = 2
TYPE_HEARTBEAT = 3
TYPE_CONFIG_PUSH = 4
PACKET_HEAD = struct.Struct('!BBI')


class LogNetworkClient:
    def __init__(self):
        self.config = get_config()
        self.sock = None
        self.connected = False
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.heartbeat_thread = None
        self.receiver_thread = None

    def connect(self):
        address = self.config.manager_address
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(5.0)
            self.sock.connect(address)
            self.connected = True

            if not self.heartbeat_thread or not self.heartbeat_thread.is_alive():
                self.stop_event.clear()
                self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True, name="LogFun-Heartbeat")
                self.heartbeat_thread.start()

            if not self.receiver_thread or not self.receiver_thread.is_alive():
                self.receiver_thread = threading.Thread(target=self._receiver_loop, daemon=True, name="LogFun-Receiver")
                self.receiver_thread.start()

            self._send_handshake()
            return True
        except Exception:
            self.connected = False
            return False

    def disconnect(self):
        self.stop_event.set()
        self.connected = False
        if self.sock:
            try:
                self.sock.close()
            except:
                pass
            self.sock = None

    def send_log(self, payload_str, log_type="compress"):
        """
        Sends a log entry.
        Returns: True if sent successfully, False otherwise.
        """
        # 1. Check Connection / Auto-reconnect
        if not self.connected:
            if not self.connect():
                return False  # Failed to connect

        # 2. Try Sending
        try:
            body = {"log": payload_str, "type": log_type}
            self._send_packet(TYPE_LOG_DATA, body)
            return True  # Success
        except Exception:
            # If send fails, mark disconnected and return False
            self.connected = False
            return False

    def _send_handshake(self):
        tpl_reg = get_template_registry()
        func_reg = get_function_registry()
        try:
            body = {"app_name": self.config.app_name, "timestamp": time.time(), "templates": tpl_reg.str_to_id.copy(), "functions": func_reg.str_to_id.copy()}
            self._send_packet(TYPE_HANDSHAKE, body)
        except:
            pass

    def _send_packet(self, pkg_type, body_dict):
        if not self.sock: raise ConnectionError("No socket")

        body_bytes = json.dumps(body_dict).encode('utf-8')
        length = len(body_bytes)
        header = PACKET_HEAD.pack(PROTO_VERSION, pkg_type, length)

        with self.lock:
            self.sock.sendall(header + body_bytes)

    def _heartbeat_loop(self):
        while not self.stop_event.is_set():
            if self.connected:
                try:
                    body = {"timestamp": time.time(), "app_name": self.config.app_name}
                    self._send_packet(TYPE_HEARTBEAT, body)
                except:
                    self.connected = False
            time.sleep(5.0)

    def _receiver_loop(self):
        while not self.stop_event.is_set():
            if not self.connected or not self.sock:
                time.sleep(1)
                continue

            try:
                try:
                    header_data = self.sock.recv(6)
                except socket.timeout:
                    continue
                except BlockingIOError:
                    continue

                if not header_data:
                    self.connected = False
                    break

                ver, p_type, length = PACKET_HEAD.unpack(header_data)

                body_data = b""
                while len(body_data) < length:
                    try:
                        chunk = self.sock.recv(length - len(body_data))
                        if not chunk: raise ConnectionError("Incomplete")
                        body_data += chunk
                    except socket.timeout:
                        continue

                self._handle_server_packet(p_type, body_data)
            except Exception:
                self.connected = False
                break

    def _handle_server_packet(self, p_type, body_bytes):
        try:
            data = json.loads(body_bytes.decode('utf-8'))
            if p_type == TYPE_HEARTBEAT:
                mute_list = data.get("mute_list", [])
                if mute_list:
                    controller = get_controller()
                    for func_id in mute_list:
                        controller.update_rule("function", func_id, action="mute")
            elif p_type == TYPE_CONFIG_PUSH:
                pass
        except Exception:
            pass


_net_client = None
_net_lock = threading.Lock()


def get_network_client():
    global _net_client
    if not _net_client:
        with _net_lock:
            if not _net_client:
                _net_client = LogNetworkClient()
    return _net_client
