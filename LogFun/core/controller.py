import threading
import json
import os
from .config import get_config


class LogController:
    """
    Central Policy Enforcement Point.
    Determines if a specific function or template should be muted.
    Policies are loaded from 'policy.json' and updated via Manager Heartbeats.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(LogController, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.config = get_config()
        self.policy_lock = threading.RLock()

        # Policy Structure:
        # {
        #   "functions": { func_id (int): "mute" },
        #   "templates": { func_id (int): { tpl_id (int): "mute" } }
        # }
        self.rules = {"functions": {}, "templates": {}}

        self._load_local_policy()
        self._initialized = True

    @property
    def policy_path(self):
        return os.path.join(self.config.output_dir, "policy.json")

    def _load_local_policy(self):
        """Load rules from local policy.json"""
        if os.path.exists(self.policy_path):
            try:
                with open(self.policy_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                    # Parse and convert keys to int where possible
                    funcs = data.get("functions", {})
                    self.rules["functions"] = {int(k): v for k, v in funcs.items()}

                    tpls = data.get("templates", {})
                    # tpls structure: { "func_id": { "tpl_id": "mute" } }
                    parsed_tpls = {}
                    for fid, tpl_rules in tpls.items():
                        parsed_tpls[int(fid)] = {int(tid): action for tid, action in tpl_rules.items()}
                    self.rules["templates"] = parsed_tpls

            except Exception as e:
                print(f"[LogFun] Failed to load policy: {e}")

    def save_policy(self):
        """Persist current rules to disk"""
        try:
            with self.policy_lock:
                with open(self.policy_path, 'w', encoding='utf-8') as f:
                    json.dump(self.rules, f, indent=4)
        except Exception:
            pass

    def update_rule(self, rule_type, target_id, sub_id=None, action="mute"):
        """
        Update a rule dynamically (e.g. from Manager).
        rule_type: 'function' or 'template'
        """
        with self.policy_lock:
            if rule_type == 'function':
                self.rules["functions"][int(target_id)] = action
            elif rule_type == 'template':
                fid = int(target_id)
                tid = int(sub_id)
                if fid not in self.rules["templates"]:
                    self.rules["templates"][fid] = {}
                self.rules["templates"][fid][tid] = action

            self.save_policy()

    def should_mute(self, func_id, tpl_id=None):
        """
        Decision engine.
        Returns True if the log should be suppressed.
        """
        fid = int(func_id)

        # 1. Check Function Level Mute
        if self.rules["functions"].get(fid) == "mute":
            return True

        # 2. Check Template Level Mute (Specific to this function)
        if tpl_id is not None:
            tid = int(tpl_id)
            func_rules = self.rules["templates"].get(fid, {})
            if func_rules.get(tid) == "mute":
                return True

        return False


def get_controller():
    return LogController()
