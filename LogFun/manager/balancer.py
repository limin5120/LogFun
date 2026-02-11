import time
import math
import collections
import statistics
import threading
from abc import ABC, abstractmethod
from .config import get_config


# --- Abstract Strategy ---
class BaseStrategy(ABC):
    def __init__(self, config_dict):
        self.cfg = config_dict

    @abstractmethod
    def record(self, app_name, func_id, timestamp, variables):
        pass

    @abstractmethod
    def analyze(self, app_name):
        """Returns a list of func_ids to mute."""
        pass


# --- Strategy 1: Z-Score (Pure Frequency) ---
class ZScoreStrategy(BaseStrategy):
    def __init__(self, config_dict):
        super().__init__(config_dict)
        self.data = collections.defaultdict(lambda: collections.defaultdict(collections.deque))
        self.lock = threading.Lock()

    def record(self, app_name, func_id, timestamp, variables):
        # Only track timestamps
        with self.lock:
            self.data[app_name][func_id].append(timestamp)

    def analyze(self, app_name):
        window = self.cfg.get("window_size", 180)
        threshold = self.cfg.get("threshold", 3.0)
        now = time.time()
        cutoff = now - window

        mute_list = []
        counts = {}

        with self.lock:
            app_data = self.data.get(app_name, {})
            for fid, timestamps in list(app_data.items()):
                # Prune old
                while timestamps and timestamps[0] < cutoff:
                    timestamps.popleft()
                if timestamps:
                    counts[fid] = len(timestamps)
                else:
                    del app_data[fid]

        if len(counts) < 2: return []

        # Calculate Stats
        values = list(counts.values())
        mean = statistics.mean(values)
        try:
            stdev = statistics.stdev(values)
        except:
            return []

        if stdev == 0: return []

        for fid, count in counts.items():
            z = (count - mean) / stdev
            if z > threshold:
                print(f"[Z-Score] Burst detected: App={app_name} FID={fid} Z={z:.2f} (Count={count})")
                mute_list.append(fid)

        return mute_list


# --- Strategy 2: Weighted Information Entropy ---
class EntropyStrategy(BaseStrategy):
    def __init__(self, config_dict):
        super().__init__(config_dict)
        # Store tuples of (timestamp, variables_str)
        self.data = collections.defaultdict(lambda: collections.defaultdict(collections.deque))
        self.lock = threading.Lock()

    def record(self, app_name, func_id, timestamp, variables):
        # We need variables for entropy
        # Variables come as a list, convert to string for hashing/counting
        var_str = str(variables)
        with self.lock:
            self.data[app_name][func_id].append((timestamp, var_str))

    def _calculate_entropy(self, var_list):
        """Shannon Entropy: H = -sum(p(x) * log2(p(x)))"""
        total = len(var_list)
        if total == 0: return 0.0

        counts = collections.Counter(var_list)
        entropy = 0.0
        for count in counts.values():
            p = count / total
            entropy -= p * math.log2(p)
        return entropy

    def analyze(self, app_name):
        window = self.cfg.get("window_size", 180)
        z_threshold = self.cfg.get("zscore_threshold", 3.0)
        ent_threshold = self.cfg.get("entropy_threshold", 0.8)
        min_samples = self.cfg.get("min_samples", 20)

        now = time.time()
        cutoff = now - window

        mute_list = []
        # Pre-calculation data for Z-Score (Frequency Part)
        counts = {}
        # Data for Entropy
        valid_funcs = {}

        with self.lock:
            app_data = self.data.get(app_name, {})
            for fid, entries in list(app_data.items()):
                # Prune
                while entries and entries[0][0] < cutoff:
                    entries.popleft()

                count = len(entries)
                if count > 0:
                    counts[fid] = count
                    valid_funcs[fid] = list(entries)  # Copy for analysis
                else:
                    del app_data[fid]

        # 1. Filter by Z-Score (Frequency) first
        # We only want to mute High Frequency logs
        if len(counts) < 2: return []

        values = list(counts.values())
        mean = statistics.mean(values)
        try:
            stdev = statistics.stdev(values)
        except:
            return []

        if stdev == 0: return []

        high_freq_candidates = []
        for fid, count in counts.items():
            z = (count - mean) / stdev
            if z > z_threshold:
                high_freq_candidates.append(fid)

        # 2. Filter by Entropy (Information Content)
        for fid in high_freq_candidates:
            entries = valid_funcs.get(fid, [])
            if len(entries) < min_samples:
                continue

            # Extract just the variable strings
            vars_only = [e[1] for e in entries]
            entropy = self._calculate_entropy(vars_only)

            # Decision: High Frequency + Low Entropy = SPAM -> Mute
            if entropy < ent_threshold:
                print(f"[Entropy] Spam detected: App={app_name} FID={fid} Z={((len(entries)-mean)/stdev):.2f} H={entropy:.2f}")
                mute_list.append(fid)
            else:
                print(f"[Entropy] High Freq but Valid: App={app_name} FID={fid} H={entropy:.2f} (Kept)")

        return mute_list


# --- Context Manager ---
class LogBalancer:
    def __init__(self):
        self.config = get_config()
        self.strategy = None
        self.current_algo_name = ""
        self._refresh_strategy()

    def _refresh_strategy(self):
        """Instantiate the correct strategy based on config."""
        algo_cfg = self.config.algo_config
        active = algo_cfg.get("active", "zscore")

        if active != self.current_algo_name or self.strategy is None:
            print(f"[Balancer] Switching strategy to: {active}")

            if active == "weighted_entropy":
                sub_cfg = algo_cfg.get("weighted_entropy", {})
                self.strategy = EntropyStrategy(sub_cfg)
            else:
                # Default to ZScore
                sub_cfg = algo_cfg.get("zscore", {})
                self.strategy = ZScoreStrategy(sub_cfg)

            self.current_algo_name = active

    def record_traffic(self, app_name, func_id, variables=None):
        if self.strategy:
            # Refresh check could be optimized to not run every record, but fine for now
            # self._refresh_strategy()
            self.strategy.record(app_name, func_id, time.time(), variables or [])

    def analyze(self, app_name):
        # Check if config changed and update strategy
        self._refresh_strategy()

        if self.strategy:
            return self.strategy.analyze(app_name)
        return []


_balancer = LogBalancer()


def get_balancer():
    return _balancer
