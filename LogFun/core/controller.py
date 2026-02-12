import threading
from .registry import get_registry


class LogController:
    """
    High-Performance Controller.
    
    Design Philosophy:
    1. Runtime: Zero I/O. Pure memory lookups for 'should_mute'.
    2. Updates: Only applied on startup or via explicit network push.
    3. Sync: Local state is sent to server ONLY at application exit.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(LogController, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        self.registry = get_registry()

    def should_mute(self, func_id, tpl_id=None):
        # Direct memory access to Registry state.
        # No file checks. No locks (relying on atomic dict reads).
        return not self.registry.is_enabled(func_id, tpl_id)

    def sync_policy(self, full_config_tree):
        # Used if Manager forcefully pushes config (rare)
        self.registry.sync_from_server(full_config_tree)


def get_controller():
    return LogController()
