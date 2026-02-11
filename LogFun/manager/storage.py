import os
import json
import time
import shutil
import threading
from .config import get_config


class StorageManager:
    def __init__(self):
        self.config = get_config()
        self.root_dir = self.config.get("storage", "root_dir")
        self.registries = {}
        self.lock = threading.RLock()

    def _get_app_dir(self, app_name):
        path = os.path.join(self.root_dir, app_name)
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)
            os.makedirs(os.path.join(path, "history"), exist_ok=True)
        return path

    def sync_registry(self, app_name, client_funcs, client_tpls):
        app_dir = self._get_app_dir(app_name)
        self._sync_single_file(app_name, app_dir, "functions.json", client_funcs)
        self._sync_single_file(app_name, app_dir, "templates.json", client_tpls)
        self._load_registry_to_memory(app_name)

    def _sync_single_file(self, app_name, app_dir, filename, client_data):
        file_path = os.path.join(app_dir, filename)

        # Load existing
        server_data = None
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    server_data = json.load(f)
            except Exception:
                pass

        # --- FIX: Robust Comparison ---
        try:
            # 1. Handle empty cases
            if not client_data and not server_data:
                return

            # 2. Normalize: Use ensure_ascii=False to match file write format
            # and sort_keys to ignore dictionary order.
            client_str = json.dumps(client_data, sort_keys=True, ensure_ascii=False)
            server_str = json.dumps(server_data, sort_keys=True, ensure_ascii=False) if server_data else ""

            if client_str == server_str:
                return  # Identical
        except Exception:
            pass

        # Backup Logic
        if server_data is not None:
            ts = time.strftime("%Y%m%d_%H%M%S")
            backup_name = f"{filename.split('.')[0]}_{ts}.json"
            backup_path = os.path.join(app_dir, "history", backup_name)
            try:
                shutil.move(file_path, backup_path)
                print(f"[Storage] Backed up {app_name}/{filename}")
            except Exception:
                pass

        # Write Logic
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(client_data, f, indent=0, ensure_ascii=False)
        except Exception as e:
            print(f"[Storage] Write failed: {e}")

    def _load_registry_to_memory(self, app_name):
        app_dir = self._get_app_dir(app_name)
        funcs = {}
        tpls = {}
        try:
            with open(os.path.join(app_dir, "functions.json"), 'r') as f:
                funcs_raw = json.load(f)
                funcs = {int(v): k for k, v in funcs_raw.items()}
            with open(os.path.join(app_dir, "templates.json"), 'r') as f:
                tpls_raw = json.load(f)
                tpls = {int(v): k for k, v in tpls_raw.items()}
        except Exception:
            pass
        with self.lock:
            self.registries[app_name] = {"funcs": funcs, "tpls": tpls}

    def write_log(self, app_name, raw_payload, log_type="compress"):
        try:
            msg = str(raw_payload)
            if not msg.endswith('\n'):
                msg += '\n'

            log_file = os.path.join(self._get_app_dir(app_name), f"{app_name}.log")

            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(msg)
        except Exception as e:
            print(f"[Storage] Write Error for {app_name}: {e}")

    def _get_str(self, app_name, reg_type, id_val):
        with self.lock:
            reg = self.registries.get(app_name, {})
            return reg.get(reg_type, {}).get(int(id_val), f"UnknownID<{id_val}>")

    def get_all_registries(self, app_name):
        """Returns all synced metadata for dashboard visualization."""
        with self.lock:
            reg = self.registries.get(app_name, {})
            # Format data for frontend: {functions: {id: name}, templates: {id: content}}
            return {"functions": reg.get("funcs", {}), "templates": reg.get("tpls", {})}


_storage_manager = StorageManager()


def get_storage():
    return _storage_manager
