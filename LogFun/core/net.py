import socket
import struct
import json
import threading
import time
from .config import get_config
from .registry import get_registry
from .controller import get_controller

PROTO_VERSION = 1
TYPE_HANDSHAKE = 1
TYPE_LOG_DATA = 2
TYPE_HEARTBEAT = 3
PACKET_HEAD = struct.Struct('!BBI')


class LogNetworkClient:
    def __init__(self):
        self.config = get_config()
        self.sock = None
        self.connected = False
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.threads_started = False

    def connect(self):
        if self.connected: return True
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(5.0)
            self.sock.connect(self.config.manager_address)
            self.connected = True

            # Start threads only if not already running
            if not self.threads_started and threading.current_thread() is not threading.main_thread():
                self.start_threads()

            self.send_handshake()
            return True
        except Exception:
            self.connected = False
            return False

    def start_threads(self):
        if not self.threads_started:
            self.stop_event.clear()
            threading.Thread(target=self._heartbeat_loop, daemon=True).start()
            threading.Thread(target=self._receiver_loop, daemon=True).start()
            self.threads_started = True

    def disconnect(self):
        self.stop_event.set()
        self.connected = False
        if self.sock:
            try:
                self.sock.close()
            except:
                pass
            self.sock = None

    def send_log(self, payload_data, log_type="compress"):
        """
        Sends a log entry or a list of log entries (batch).
        """
        if not self.connected:
            if not self.connect(): return False
            self.start_threads()

        try:
            body = {"log": payload_data, "type": log_type}
            self._send_packet(TYPE_LOG_DATA, body)
            return True
        except:
            self.connected = False
            return False

    def send_handshake(self, blocking=False):
        """
        Sends the full Unified Registry config.
        """
        reg = get_registry()
        # [FIX] Send the unified 'config' tree + stats
        body = {
            "app_name": self.config.app_name,
            "config": reg.data,
            # If registry has stats feature enabled:
            "blocked_stats": getattr(reg, 'get_and_clear_stats', lambda: {})()
        }

        if blocking:
            try:
                tmp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                tmp_sock.settimeout(2.0)
                tmp_sock.connect(self.config.manager_address)
                body_bytes = json.dumps(body).encode('utf-8')
                header = PACKET_HEAD.pack(PROTO_VERSION, TYPE_HANDSHAKE, len(body_bytes))
                tmp_sock.sendall(header + body_bytes)
                tmp_sock.close()
            except:
                pass
        else:
            self._send_packet(TYPE_HANDSHAKE, body)

    def _send_packet(self, pkg_type, body_dict):
        if not self.sock: raise ConnectionError
        body_bytes = json.dumps(body_dict).encode('utf-8')
        header = PACKET_HEAD.pack(PROTO_VERSION, pkg_type, len(body_bytes))
        with self.lock:
            self.sock.sendall(header + body_bytes)

    def _heartbeat_loop(self):
        while not self.stop_event.is_set():
            if self.connected:
                try:
                    reg = get_registry()
                    body = {
                        "timestamp": time.time(),
                        "app_name": self.config.app_name,
                        # [FIX] Send stats if available
                        "blocked_stats": getattr(reg, 'get_and_clear_stats', lambda: {})()
                    }
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
                head = self.sock.recv(6)
                if not head:
                    self.connected = False
                    continue
                _, p_type, length = PACKET_HEAD.unpack(head)

                body = b""
                while len(body) < length:
                    chunk = self.sock.recv(length - len(body))
                    if not chunk: break
                    body += chunk

                self._handle_packet(p_type, body)
            except:
                self.connected = False

    def _handle_packet(self, p_type, body):
        try:
            data = json.loads(body.decode('utf-8'))
            if p_type == TYPE_HEARTBEAT:
                # [FIX] Sync full config tree from server
                if "config" in data:
                    get_controller().sync_policy(data["config"])
        except:
            pass


_client = LogNetworkClient()


def get_network_client():
    return _client
