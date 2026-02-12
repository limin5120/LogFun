import time
import collections
import statistics
import threading
from abc import ABC, abstractmethod
from .config import get_config
from .storage import get_storage


class BaseStrategy(ABC):
    def __init__(self, config):
        self.cfg = config

    @abstractmethod
    def record(self, app, fid, ts, vars):
        pass

    @abstractmethod
    def analyze(self, app):
        pass


class ZScoreStrategy(BaseStrategy):
    def __init__(self, cfg):
        super().__init__(cfg)
        self.data = collections.defaultdict(lambda: collections.defaultdict(collections.deque))
        self.lock = threading.Lock()

    def record(self, app, fid, ts, vars):
        with self.lock:
            self.data[app][fid].append(ts)

    def analyze(self, app):
        win = self.cfg.get("window_size", 180)
        thresh = self.cfg.get("threshold", 3.0)
        cutoff = time.time() - win
        counts = {}
        with self.lock:
            for fid, ts in list(self.data[app].items()):
                while ts and ts[0] < cutoff:
                    ts.popleft()
                if ts: counts[fid] = len(ts)
                else: del self.data[app][fid]

        if len(counts) < 2: return []
        vals = list(counts.values())
        mean = statistics.mean(vals)
        try:
            stdev = statistics.stdev(vals)
        except:
            return []
        if stdev == 0: return []

        mutes = []
        for fid, c in counts.items():
            if (c - mean) / stdev > thresh:
                mutes.append(fid)
        return mutes


class LogBalancer:
    def __init__(self):
        self.config = get_config()
        self.strategy = ZScoreStrategy(self.config.algo_config.get("zscore", {}))

    def record_traffic(self, app, fid, vars=None):
        self.strategy.record(app, fid, time.time(), vars)

    def run_analysis_cycle(self, app):
        # Identify spammers
        mutes = self.strategy.analyze(app)
        if mutes:
            storage = get_storage()
            for fid in mutes:
                print(f"[Balancer] Auto-muting high freq function: {fid}")
                storage.update_control(app, fid, None, False)


_balancer = LogBalancer()


def get_balancer():
    return _balancer
