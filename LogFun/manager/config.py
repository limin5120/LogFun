import os
import json
import threading

# Default Config with Merged Algorithm Settings
DEFAULT_CONFIG = {
    "server": {
        "host": "0.0.0.0",
        "port": 9999
    },
    "storage": {
        "root_dir": "./server_data"
    },
    "algorithm": {
        "enable": True,
        "active": "zscore",  # Options: "zscore", "weighted_entropy"

        # Strategy 1: Frequency Burst Detection
        "zscore": {
            "window_size": 180,  # Seconds
            "check_interval": 5,  # Seconds
            "threshold": 3.0  # Sigma
        },

        # Strategy 2: Information Entropy (Frequency + Content)
        "weighted_entropy": {
            "window_size": 180,
            "check_interval": 5,
            "min_samples": 20,  # Minimum samples to calculate entropy
            "entropy_threshold": 0.8,  # Below this entropy -> Low Information -> Mute
            "zscore_threshold": 3.0  # Must also be high frequency to consider muting
        }
    },
    "rules": []
}


class ServerConfig:
    def __init__(self, config_path="server_config.json"):
        self.config_path = config_path
        self._config = DEFAULT_CONFIG
        self._lock = threading.RLock()
        self.last_hash = ""

        if not os.path.exists(config_path):
            self._save_default()
        else:
            self._merge_defaults()

        self.reload()

    def _save_default(self):
        try:
            with open(self.config_path, 'w') as f:
                json.dump(DEFAULT_CONFIG, f, indent=4)
        except Exception as e:
            print(f"[Manager] Failed to create default config: {e}")

    def _merge_defaults(self):
        try:
            changed = False
            with open(self.config_path, 'r') as f:
                current = json.load(f)

            # Merge 'algorithm' section
            if "algorithm" not in current:
                current["algorithm"] = DEFAULT_CONFIG["algorithm"]
                changed = True
            else:
                for k, v in DEFAULT_CONFIG["algorithm"].items():
                    if k not in current["algorithm"]:
                        current["algorithm"][k] = v
                        changed = True

            if changed:
                with open(self.config_path, 'w') as f:
                    json.dump(current, f, indent=4)
        except Exception:
            pass

    def reload(self):
        if not os.path.exists(self.config_path):
            return False

        with self._lock:
            try:
                with open(self.config_path, 'r') as f:
                    content = f.read()
                    new_hash = str(hash(content))

                    if new_hash != self.last_hash:
                        self._config = json.loads(content)
                        self.last_hash = new_hash
                        return True
            except Exception as e:
                print(f"[Manager] Config load error: {e}")
        return False

    def get(self, section, key, default=None):
        with self._lock:
            return self._config.get(section, {}).get(key, default)

    @property
    def algo_config(self):
        with self._lock:
            return self._config.get("algorithm", {})


_server_config = ServerConfig()


def get_config():
    return _server_config
