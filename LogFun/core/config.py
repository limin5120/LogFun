import os
import threading
from enum import Enum

DEFAULT_LOG_DIR = './logfun_output/'


class LogMode(Enum):
    DEV = "dev"  # Console output
    FILE = "file"  # Local file write
    REMOTE = "remote"  # Network socket (Manager)


class LogType(Enum):
    NORMAL = "normal"  # Plain text / JSON
    COMPRESS = "compress"  # ID + Variables


class AgentConfig:
    """
    Thread-safe singleton configuration.
    Keeps Agent lightweight: Only knows WHO to connect to, not HOW to analyze.
    """
    def __init__(self):
        # 1. Basic Identity & Output
        self._mode = LogMode.DEV
        self._log_type = LogType.COMPRESS
        self._output_dir = DEFAULT_LOG_DIR
        self._app_name = "root"  # Identity

        # 2. Connection Info (The only thing needed for Remote mode)
        self._manager_ip = "127.0.0.1"
        self._manager_port = 9999

        self._lock = threading.RLock()

        if not os.path.exists(self._output_dir):
            os.makedirs(self._output_dir, exist_ok=True)

    @property
    def mode(self):
        with self._lock:
            return self._mode

    @mode.setter
    def mode(self, value):
        with self._lock:
            if isinstance(value, str):
                try:
                    self._mode = LogMode(value.lower())
                except ValueError:
                    self._mode = LogMode.DEV
            elif isinstance(value, LogMode):
                self._mode = value

    @property
    def log_type(self):
        with self._lock:
            return self._log_type

    @log_type.setter
    def log_type(self, value):
        with self._lock:
            if isinstance(value, str):
                try:
                    self._log_type = LogType(value.lower())
                except ValueError:
                    self._log_type = LogType.COMPRESS
            elif isinstance(value, LogType):
                self._log_type = value

    @property
    def output_dir(self):
        with self._lock:
            return self._output_dir

    @output_dir.setter
    def output_dir(self, path):
        with self._lock:
            self._output_dir = path
            if not os.path.exists(path):
                os.makedirs(path, exist_ok=True)

    @property
    def log_file_path(self):
        with self._lock:
            return os.path.join(self._output_dir, f"{self._app_name}.log")

    @property
    def template_db_path(self):
        with self._lock:
            return os.path.join(self._output_dir, "templates.json")

    @property
    def function_db_path(self):
        with self._lock:
            return os.path.join(self._output_dir, "functions.json")

    # --- Network Configuration ---
    @property
    def app_name(self):
        with self._lock:
            return self._app_name

    @property
    def manager_address(self):
        with self._lock:
            return (self._manager_ip, self._manager_port)

    def update(self, **kwargs):
        for k, v in kwargs.items():
            if k == 'mode':
                self.mode = v
            elif k == 'logtype':
                self.log_type = v
            elif k == 'output':
                self.output_dir = v
            elif k == 'app_name':
                with self._lock:
                    self._app_name = v
            elif k == 'manager_ip':
                with self._lock:
                    self._manager_ip = v
            elif k == 'manager_port':
                with self._lock:
                    self._manager_port = int(v)


_global_config = AgentConfig()


def get_config():
    return _global_config
