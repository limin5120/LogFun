import os
import json
import threading
import atexit
import time
from .config import get_config


class UnifiedRegistry:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(UnifiedRegistry, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized"): return
        self.config = get_config()
        self.data_lock = threading.RLock()

        # Configuration Data
        self.data = {"app_name": self.config.app_name, "functions": {}}

        # Runtime Stats for Balancer Visibility
        # Structure: { "func_id": count, "func_id:tpl_id": count }
        self.blocked_stats = {}

        self.func_name_to_id = {}
        self.tpl_content_to_id = {}
        self.next_func_id = 1
        self.next_tpl_id = 1
        self._dirty = False

        self._load()
        atexit.register(self._on_exit)
        self._initialized = True

    def _load(self):
        path = self.config.config_filepath
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    loaded_data = json.load(f)
                    with self.data_lock:
                        self.data = loaded_data
                        max_fid = 0
                        max_tid = 0
                        for fid_str, f_data in self.data.get("functions", {}).items():
                            fid = int(fid_str)
                            if fid > max_fid: max_fid = fid
                            self.func_name_to_id[f_data.get("name", "")] = fid
                            for tid_str, t_data in f_data.get("templates", {}).items():
                                tid = int(tid_str)
                                if tid > max_tid: max_tid = tid
                                self.tpl_content_to_id[(fid, t_data.get("content", ""))] = tid
                        self.next_func_id = max_fid + 1
                        self.next_tpl_id = max_tid + 1
            except Exception:
                pass

    def _on_exit(self):
        self.save()
        try:
            from .net import get_network_client
            client = get_network_client()
            # Sync final stats and config on exit
            client.send_handshake(blocking=True)
            client.disconnect()
        except:
            pass

    def save(self):
        path = self.config.config_filepath
        try:
            with self.data_lock:
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def get_func_id(self, func_name):
        if func_name in self.func_name_to_id: return self.func_name_to_id[func_name]
        with self.data_lock:
            if func_name in self.func_name_to_id: return self.func_name_to_id[func_name]
            new_id = self.next_func_id
            self.next_func_id += 1
            self.data["functions"][str(new_id)] = {"name": func_name, "enabled": True, "templates": {}}
            self.func_name_to_id[func_name] = new_id
            return new_id

    def get_tpl_id(self, func_id, content):
        key = (func_id, content)
        if key in self.tpl_content_to_id: return self.tpl_content_to_id[key]
        with self.data_lock:
            if key in self.tpl_content_to_id: return self.tpl_content_to_id[key]
            new_id = self.next_tpl_id
            self.next_tpl_id += 1
            fid_str = str(func_id)
            if fid_str in self.data["functions"]:
                self.data["functions"][fid_str]["templates"][str(new_id)] = {"content": content, "enabled": True}
                self.tpl_content_to_id[key] = new_id
                return new_id
            return 0

    def is_enabled(self, func_id, tpl_id=None):
        """
        Check if allowed. If blocked, increment stats.
        """
        fid_str = str(func_id)
        func_data = self.data["functions"].get(fid_str)

        # Function Level Check
        if func_data and not func_data.get("enabled", True):
            self._record_block(fid_str)
            return False

        # Template Level Check
        if tpl_id is not None:
            tid_str = str(tpl_id)
            if func_data:
                tpl_data = func_data["templates"].get(tid_str)
                if tpl_data and not tpl_data.get("enabled", True):
                    self._record_block(f"{fid_str}:{tid_str}")
                    return False

        return True

    def _record_block(self, key):
        # Lightweight stats increment (Race condition acceptable for stats)
        try:
            self.blocked_stats[key] = self.blocked_stats.get(key, 0) + 1
        except:
            pass

    def get_and_clear_stats(self):
        """Retrieve current stats to send to server."""
        # We copy current stats. We don't clear them to keep cumulative counts consistent for UI,
        # or we can clear delta. Let's send cumulative.
        return self.blocked_stats.copy()

    def sync_from_server(self, server_data):
        with self.data_lock:
            server_funcs = server_data.get("functions", {})
            local_funcs = self.data["functions"]
            for fid, s_func in server_funcs.items():
                if fid in local_funcs:
                    local_funcs[fid]["enabled"] = s_func.get("enabled", True)
                    l_tpls = local_funcs[fid]["templates"]
                    for tid, s_tpl in s_func.get("templates", {}).items():
                        if tid in l_tpls: l_tpls[tid]["enabled"] = s_tpl.get("enabled", True)
                        else:
                            l_tpls[tid] = s_tpl
                            self.tpl_content_to_id[(int(fid), s_tpl["content"])] = int(tid)
                else:
                    local_funcs[fid] = s_func
                    self.func_name_to_id[s_func["name"]] = int(fid)
                    for tid, t_data in s_func.get("templates", {}).items():
                        self.tpl_content_to_id[(int(fid), t_data["content"])] = int(tid)
            self.save()


def get_registry():
    return UnifiedRegistry()
