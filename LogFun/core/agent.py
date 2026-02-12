import threading
import queue
import sys
import atexit
import time
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
        """
        Gracefully stop the agent, ensuring all pending logs are flushed.
        """
        if not self._running: return
        self._running = False

        if self._worker_thread and self._worker_thread.is_alive():
            # Wait for queue to drain
            while not self._queue.empty():
                time.sleep(0.1)
            self._worker_thread.join(timeout=5.0)

        self.net_client.disconnect()

    def log(self, payload, log_type="compress"):
        """
        Queue log for processing.
        [FIX] Added log_type argument to match Logger calls.
        """
        self._queue.put((payload, log_type))

    def _worker_loop(self):
        log_file = None
        current_file_path = self.config.log_file_path

        # Batching settings
        batch_buffer = []
        current_batch_type = None  # Track type to avoid mixing types in one batch

        BATCH_SIZE = 100
        FLUSH_INTERVAL = 0.5
        last_flush_time = time.time()

        def process_batch(batch, batch_type):
            nonlocal log_file, current_file_path
            if not batch: return

            try:
                target_mode = self.config.mode

                # --- Mode: FILE ---
                if target_mode == LogMode.FILE:
                    if not log_file or self.config.log_file_path != current_file_path:
                        if log_file: log_file.close()
                        current_file_path = self.config.log_file_path
                        try:
                            # Use line buffering for better performance than unbuffered
                            log_file = open(current_file_path, 'a', encoding='utf-8', buffering=1)
                        except Exception:
                            return
                    for item in batch:
                        self._write_file(log_file, item)

                # --- Mode: DEV ---
                elif target_mode == LogMode.DEV:
                    for item in batch:
                        sys.stdout.write(str(item) + ('\n' if not str(item).endswith('\n') else ''))
                    sys.stdout.flush()

                # --- Mode: REMOTE ---
                elif target_mode == LogMode.REMOTE:
                    # Use the batch's type, defaulting to compress if None
                    type_to_send = batch_type if batch_type else "compress"

                    # Convert items to strings
                    str_batch = [str(item) for item in batch]

                    # Send batch
                    sent_success = self.net_client.send_log(str_batch, log_type=type_to_send)

                    if not sent_success:
                        # Fallback to local file
                        if not log_file or self.config.log_file_path != current_file_path:
                            if log_file: log_file.close()
                            current_file_path = self.config.log_file_path
                            try:
                                log_file = open(current_file_path, 'a', encoding='utf-8', buffering=1)
                            except Exception:
                                pass
                        if log_file:
                            for item in batch:
                                self._write_file(log_file, item)

            except Exception as e:
                sys.stderr.write(f"[LogFun] Worker Error: {e}\n")

        while self._running or not self._queue.empty() or batch_buffer:
            try:
                # Get (payload, type) tuple
                item = self._queue.get(timeout=0.1)

                # Unpack or handle legacy single-item (just in case)
                if isinstance(item, tuple) and len(item) == 2:
                    payload, msg_type = item
                else:
                    payload, msg_type = item, "compress"

                # Check if we need to switch batches due to type change
                if current_batch_type is not None and msg_type != current_batch_type:
                    process_batch(batch_buffer, current_batch_type)
                    batch_buffer = []

                current_batch_type = msg_type
                batch_buffer.append(payload)
                self._queue.task_done()

            except queue.Empty:
                pass

            # Check flush conditions
            is_full = len(batch_buffer) >= BATCH_SIZE
            is_timeout = (time.time() - last_flush_time) > FLUSH_INTERVAL
            is_stopping = (not self._running and self._queue.empty())

            if batch_buffer and (is_full or is_timeout or is_stopping):
                process_batch(batch_buffer, current_batch_type)
                batch_buffer = []
                last_flush_time = time.time()

        if log_file:
            log_file.close()

    def _write_file(self, f, payload):
        try:
            msg = str(payload)
            if not msg.endswith('\n'):
                msg += '\n'
            f.write(msg)
        except:
            pass


def get_agent():
    return AgentCore()
