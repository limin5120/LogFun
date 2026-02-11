import threading
import queue
import sys
import atexit
from .config import get_config, LogMode
from .net import get_network_client


class AgentCore:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(AgentCore, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized: return

        self.config = get_config()
        self._queue = queue.Queue()
        self._running = False
        self._worker_thread = None
        self.net_client = get_network_client()

        self.start()
        atexit.register(self.stop)
        self._initialized = True

    def start(self):
        if self._running: return
        self._running = True
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True, name="LogFun-Worker")
        self._worker_thread.start()

    def stop(self):
        if not self._running: return
        self._running = False
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=2.0)
        self.net_client.disconnect()

    def log(self, payload):
        self._queue.put(payload)

    def _worker_loop(self):
        log_file = None
        current_file_path = self.config.log_file_path

        # Initial Setup for File Mode
        if self.config.mode == LogMode.FILE:
            try:
                log_file = open(current_file_path, 'a', encoding='utf-8')
            except Exception as e:
                sys.stderr.write(f"[LogFun] Failed to open log file: {e}\n")

        while self._running or not self._queue.empty():
            try:
                payload = self._queue.get(timeout=0.1)
            except queue.Empty:
                continue

            try:
                target_mode = self.config.mode

                # --- Mode: FILE ---
                if target_mode == LogMode.FILE:
                    if not log_file or self.config.log_file_path != current_file_path:
                        if log_file: log_file.close()
                        current_file_path = self.config.log_file_path
                        try:
                            log_file = open(current_file_path, 'a', encoding='utf-8')
                        except Exception:
                            continue
                    self._write_file(log_file, payload)

                # --- Mode: DEV ---
                elif target_mode == LogMode.DEV:
                    if log_file:
                        log_file.close()
                        log_file = None
                    sys.stdout.write(str(payload) + ('\n' if not str(payload).endswith('\n') else ''))
                    sys.stdout.flush()

                # --- Mode: REMOTE ---
                elif target_mode == LogMode.REMOTE:
                    current_type_str = self.config.log_type.value

                    # Try sending via network
                    sent_success = self.net_client.send_log(str(payload), current_type_str)

                    if sent_success:
                        # If successful, we don't need the local file handle
                        if log_file:
                            log_file.close()
                            log_file = None
                    else:
                        # --- FALLBACK: Write to local file if Network Fails ---
                        # Ensure local file is open
                        if not log_file or self.config.log_file_path != current_file_path:
                            if log_file: log_file.close()
                            current_file_path = self.config.log_file_path
                            try:
                                log_file = open(current_file_path, 'a', encoding='utf-8')
                            except Exception:
                                # If even file open fails, we can't do much (maybe stderr)
                                sys.stderr.write(f"[LogFun] Fallback failed: Could not open log file.\n")
                                continue

                        # Write payload to local disk
                        self._write_file(log_file, payload)

            except Exception as e:
                sys.stderr.write(f"[LogFun] Worker Error: {e}\n")
            finally:
                self._queue.task_done()

        if log_file:
            log_file.close()

    def _write_file(self, f, payload):
        msg = str(payload)
        if not msg.endswith('\n'):
            msg += '\n'
        f.write(msg)


def get_agent():
    return AgentCore()
