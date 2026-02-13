import time
import threading


class LogMonitor:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(LogMonitor, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized"): return
        self.start_time = time.time()
        self.total_logs = 0
        self.interval_logs = 0
        self.last_check = time.time()
        self.qps = 0
        # [FIX] Add lock for thread-safe counters
        self.stats_lock = threading.Lock()
        self._initialized = True

    def tick(self, count=1):
        """
        Increment log counter safely.
        """
        with self.stats_lock:
            self.total_logs += count
            self.interval_logs += count

            now = time.time()
            if now - self.last_check >= 1.0:
                self.qps = self.interval_logs / (now - self.last_check)
                self.interval_logs = 0
                self.last_check = now

    def get_snapshot(self):
        return {"uptime": time.time() - self.start_time, "total_logs": self.total_logs, "qps": int(self.qps)}


_monitor = LogMonitor()


def get_monitor():
    return _monitor
