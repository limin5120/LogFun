import os
import json
import threading
from .config import get_config


class StorageManager:
    def __init__(self):
        self.config = get_config()
        self.root_dir = self.config.get("storage", "root_dir")
        self.apps_data = {}
        self.app_stats = {}
        self.lock = threading.RLock()

    def _get_app_dir(self, app_name):
        d = os.path.join(self.root_dir, app_name)
        os.makedirs(d, exist_ok=True)
        return d

    def _get_config_path(self, app_name):
        return os.path.join(self._get_app_dir(app_name), f"{app_name}.json")

    def _get_log_path(self, app_name):
        return os.path.join(self._get_app_dir(app_name), f"{app_name}.log")

    def update_stats(self, app_name, stats_dict):
        with self.lock:
            if app_name not in self.app_stats: self.app_stats[app_name] = {}
            curr = self.app_stats[app_name]
            for k, v in stats_dict.items():
                curr[k] = max(curr.get(k, 0), v)

    def get_app_stats(self, app_name):
        with self.lock:
            return self.app_stats.get(app_name, {})

    def sync_config(self, app_name, client_config):
        path = self._get_config_path(app_name)
        with self.lock:
            if app_name not in self.apps_data:
                if os.path.exists(path):
                    try:
                        with open(path, 'r', encoding='utf-8') as f:
                            self.apps_data[app_name] = json.load(f)
                    except:
                        self.apps_data[app_name] = {}

            server_data = self.apps_data.get(app_name, {})
            if not server_data: server_data = {"app_name": app_name, "functions": {}}

            c_funcs = client_config.get("functions", {})
            s_funcs = server_data.setdefault("functions", {})
            changed = False

            for fid, c_func in c_funcs.items():
                if fid not in s_funcs:
                    s_funcs[fid] = c_func
                    changed = True
                else:
                    c_tpls = c_func.get("templates", {})
                    s_tpls = s_funcs[fid].setdefault("templates", {})
                    for tid, c_tpl in c_tpls.items():
                        if tid not in s_tpls:
                            s_tpls[tid] = c_tpl
                            changed = True

            self.apps_data[app_name] = server_data
            if changed: self._save_to_disk(app_name)

    def update_control(self, app_name, target_id, sub_id, enable, source="manual"):
        """
        Update enabled status.
        [FIX] Support 'source' to track manual vs balancer mutes.
        """
        with self.lock:
            if app_name not in self.apps_data: return
            data = self.apps_data[app_name]
            funcs = data.get("functions", {})
            fid = str(target_id)

            if fid in funcs:
                target_node = None

                if sub_id:
                    tid = str(sub_id)
                    if tid in funcs[fid].get("templates", {}):
                        target_node = funcs[fid]["templates"][tid]
                else:
                    target_node = funcs[fid]
                    # Cascade disable to templates
                    for tid in funcs[fid].get("templates", {}):
                        t_node = funcs[fid]["templates"][tid]
                        t_node["enabled"] = enable
                        if not enable: t_node["muted_by"] = source
                        else: t_node.pop("muted_by", None)

                if target_node:
                    target_node["enabled"] = enable
                    if not enable:
                        target_node["muted_by"] = source
                    else:
                        # Clear metadata if re-enabling
                        target_node.pop("muted_by", None)

            self._save_to_disk(app_name)

    def _save_to_disk(self, app_name):
        with open(self._get_config_path(app_name), 'w', encoding='utf-8') as f:
            json.dump(self.apps_data[app_name], f, ensure_ascii=False, indent=2)

    def get_app_config(self, app_name):
        with self.lock:
            if app_name not in self.apps_data:
                path = self._get_config_path(app_name)
                if os.path.exists(path):
                    try:
                        with open(path, 'r', encoding='utf-8') as f:
                            self.apps_data[app_name] = json.load(f)
                    except:
                        pass
            return self.apps_data.get(app_name, {})

    def write_log(self, app_name, msg, log_type):
        with open(self._get_log_path(app_name), 'a', encoding='utf-8') as f:
            f.write(str(msg).strip() + "\n")


_storage = StorageManager()


def get_storage():
    return _storage
