import os
import json
import threading

DEFAULT_SERVER_CONFIG = {"server": {"host": "0.0.0.0", "port": 9999}, "storage": {"root_dir": "./logfun_data"}, "algo_config": {"enable": True, "active": "zscore", "zscore": {"window_size": 180, "threshold": 3.0}, "weighted_entropy": {"window_size": 180, "zscore_threshold": 3.0, "entropy_threshold": 0.8, "min_samples": 20}}}


class ServerConfig:
    def __init__(self):
        self.config_path = "server_config.json"
        self.data = DEFAULT_SERVER_CONFIG
        self.lock = threading.RLock()
        self._load()

    def _load(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    user_cfg = json.load(f)
                    # Merge logic (simplified)
                    for sec, val in user_cfg.items():
                        if sec in self.data and isinstance(self.data[sec], dict):
                            self.data[sec].update(val)
                        else:
                            self.data[sec] = val
            except Exception as e:
                print(f"[LogFun-Manager] Config load error: {e}")

    def get(self, section, key=None):
        """
        Support .get('server', 'port') or .get('algo_config')
        """
        with self.lock:
            if section not in self.data:
                return None
            if key is None:
                return self.data[section]
            return self.data[section].get(key)

    @property
    def algo_config(self):
        return self.get("algo_config")

    def reload(self):
        """Hot reload checking"""
        # For simplicity, just re-load
        self._load()
        return True


_server_config = ServerConfig()


def get_config():
    return _server_config
