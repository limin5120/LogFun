import time
import collections
import statistics
import threading
import math
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
        win = int(self.cfg.get("window_size", 180))
        thresh = float(self.cfg.get("threshold", 3.0))
        cutoff = time.time() - win
        counts = {}
        with self.lock:
            for fid, ts in list(self.data[app].items()):
                while ts and ts[0] < cutoff:
                    ts.popleft()
                if ts: counts[fid] = len(ts)
                else: del self.data[app][fid]

        if not counts: return []
        vals = list(counts.values())

        # [FIX] Handle single function or zero variance case
        if len(vals) < 2:
            # If only one function, mute if it exceeds a high absolute threshold (e.g., 2x of a reasonable freq)
            # Default fallback: if count > 100 in window, consider it a spike
            for fid, c in counts.items():
                if c > 100: return [fid]
            return []

        mean = statistics.mean(vals)
        try:
            stdev = statistics.stdev(vals)
        except:
            stdev = 0

        if stdev == 0:
            # All functions have same frequency. Mute if very high.
            return [fid for fid, c in counts.items() if c > 100]

        return [fid for fid, c in counts.items() if (c - mean) / stdev > thresh]


class WeightedEntropyStrategy(BaseStrategy):
    def __init__(self, cfg):
        super().__init__(cfg)
        self.data = collections.defaultdict(lambda: collections.defaultdict(collections.deque))
        self.lock = threading.Lock()

    def record(self, app, fid, ts, vars):
        with self.lock:
            self.data[app][fid].append((ts, str(vars)))

    def _calc_entropy(self, logs):
        if not logs: return 0
        total = len(logs)
        counts = collections.Counter(logs)
        ent = 0
        for count in counts.values():
            p = count / total
            ent -= p * math.log2(p)
        return ent

    def analyze(self, app):
        win = int(self.cfg.get("window_size", 60))
        thresh = float(self.cfg.get("threshold", 3.0))
        min_ent = float(self.cfg.get("min_entropy", 1.5))
        cutoff = time.time() - win
        stats = {}

        with self.lock:
            for fid, items in list(self.data[app].items()):
                while items and items[0][0] < cutoff:
                    items.popleft()
                if not items:
                    del self.data[app][fid]
                    continue
                count = len(items)
                var_contents = [x[1] for x in items]
                entropy = self._calc_entropy(var_contents)
                stats[fid] = (count, entropy)

        if not stats: return []
        counts = [v[0] for v in stats.values()]

        # [FIX] Advanced single-function detection for entropy
        if len(counts) < 2:
            for fid, (c, ent) in stats.items():
                # If high frequency and low entropy, mute even without a baseline
                if c > 50 and ent < min_ent: return [fid]
            return []

        mean = statistics.mean(counts)
        try:
            stdev = statistics.stdev(counts)
        except:
            stdev = 0

        mutes = []
        for fid, (c, ent) in stats.items():
            # Z-Score check
            z = (c - mean) / stdev if stdev > 0 else (1 if c > mean else 0)
            # Mute if high frequency AND low entropy
            if (z > thresh or c > 100) and ent < min_ent:
                mutes.append(fid)
        return mutes


class LogBalancer:
    def __init__(self):
        self.config = get_config()
        self._init_strategy()

    def _init_strategy(self):
        cfg = self.config.algo_config
        active = cfg.get("active", "zscore")
        params = cfg.get(active, {})
        if active == "weighted_entropy": self.strategy = WeightedEntropyStrategy(params)
        else: self.strategy = ZScoreStrategy(params)

    def update_strategy(self, name, params):
        self.config.algo_config["active"] = name
        self.config.algo_config[name] = params
        self._init_strategy()

    def record_traffic(self, app, fid, vars=None):
        self.strategy.record(app, fid, time.time(), vars)

    def run_analysis_cycle(self, app):
        if app == "unknown": return []
        mutes = self.strategy.analyze(app)
        if mutes:
            storage = get_storage()
            for fid in mutes:
                storage.update_control(app, fid, None, False, source="balancer")
            return mutes
        return []


_balancer = LogBalancer()


def get_balancer():
    return _balancer
