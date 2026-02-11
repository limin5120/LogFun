import os
import json
import threading
import atexit
from .config import get_config


class BaseRegistry:
    def __init__(self, db_path_getter):
        self.config = get_config()
        self.db_path_getter = db_path_getter
        self.map_lock = threading.RLock()
        self.str_to_id = {}
        self.id_to_str = {}
        self.next_id = 1
        self._dirty = False  # Flag to track unsaved changes
        self._load()
        # Ensure data is persisted when the process exits
        atexit.register(self.save)

    def _load(self):
        path = getattr(self.config, self.db_path_getter)
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.str_to_id = data
                    self.id_to_str = {int(v): k for k, v in data.items()}
                    if self.str_to_id:
                        self.next_id = max(self.str_to_id.values()) + 1
            except Exception:
                pass

    def save(self):
        """Persist registry to disk only if data has changed."""
        if not self._dirty:
            return
        path = getattr(self.config, self.db_path_getter)
        try:
            with self.map_lock:
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(self.str_to_id, f, ensure_ascii=False, indent=0)
                self._dirty = False
                # print("[LogFun] Registry saved to disk.")
        except Exception:
            pass

    def get_id(self, key_str, create=True):
        if not key_str:
            return 0

        if key_str in self.str_to_id:
            return self.str_to_id[key_str]

        if not create:
            return None

        with self.map_lock:
            if key_str in self.str_to_id:
                return self.str_to_id[key_str]

            new_id = self.next_id
            self.str_to_id[key_str] = new_id
            self.id_to_str[new_id] = key_str
            self.next_id += 1
            self._dirty = True  # Mark as dirty but don't write to disk yet
            return new_id


_template_registry = None
_function_registry = None
_reg_lock = threading.Lock()


def get_template_registry():
    global _template_registry
    if not _template_registry:
        with _reg_lock:
            if not _template_registry:
                _template_registry = BaseRegistry('template_db_path')
    return _template_registry


def get_function_registry():
    global _function_registry
    if not _function_registry:
        with _reg_lock:
            if not _function_registry:
                _function_registry = BaseRegistry('function_db_path')
    return _function_registry
