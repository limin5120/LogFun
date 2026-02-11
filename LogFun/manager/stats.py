import time
import threading


class TrafficMonitor:
    """
    Thread-safe traffic statistics collector.
    Calculates Real-time QPS and Total Logs.
    """
    def __init__(self):
        self.start_time = time.time()
        self.total_logs = 0
        self.current_qps = 0.0
        self.lock = threading.Lock()

        # Internal counters for QPS calculation
        self._last_check_time = time.time()
        self._last_total = 0

        # Start background calculation thread
        self._stop_event = threading.Event()
        self._calc_thread = threading.Thread(target=self._calc_loop, daemon=True)
        self._calc_thread.start()

    def tick(self, count=1):
        """Record a log event."""
        with self.lock:
            self.total_logs += count

    def _calc_loop(self):
        """Update QPS every second."""
        while not self._stop_event.is_set():
            time.sleep(1.0)
            with self.lock:
                now = time.time()
                delta_t = now - self._last_check_time
                delta_c = self.total_logs - self._last_total

                if delta_t > 0:
                    self.current_qps = delta_c / delta_t

                self._last_check_time = now
                self._last_total = self.total_logs

    def get_snapshot(self):
        """Return current stats dict."""
        with self.lock:
            return {"uptime": int(time.time() - self.start_time), "total_logs": self.total_logs, "qps": round(self.current_qps, 2)}


_monitor = TrafficMonitor()


def get_monitor():
    return _monitor
