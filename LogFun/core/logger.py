import logging
import contextvars
import time
import json
from datetime import datetime
from .config import get_config, LogType, LogMode
from .agent import get_agent
from .registry import get_template_registry
from .context import CURRENT_FUNC_ID
from .controller import get_controller

# Global context for compressed logs buffer
CURRENT_LOG_BUFFER = contextvars.ContextVar('logfun_buffer', default=None)


class Logger:
    def __init__(self, name="root"):
        self.name = name
        self.agent = get_agent()
        self.tpl_registry = get_template_registry()
        self.config = get_config()
        self.controller = get_controller()

    def _log(self, level, msg, args=None):
        current_type = self.config.log_type

        # Always ensure a template ID is generated for metadata sync
        tpl_id = self.tpl_registry.get_id(msg, create=True)

        # Policy Check
        func_id = CURRENT_FUNC_ID.get()
        if func_id != 0:
            if self.controller.should_mute(func_id, tpl_id):
                return

        # Handle NORMAL mode
        if current_type == LogType.NORMAL:
            content = msg
            if args:
                formatting_args = args
                if len(args) == 1 and isinstance(args[0], tuple):
                    try:
                        content = msg % args[0]
                    except TypeError:
                        pass
                else:
                    try:
                        content = msg % formatting_args
                    except TypeError:
                        content = f"{msg} | {args}"

            now = time.time()
            ts = datetime.fromtimestamp(now).strftime('%Y-%m-%d %H:%M:%S')
            ms = int((now - int(now)) * 1000)

            if self.config.mode == LogMode.REMOTE:
                payload_dict = {"ts": f"{ts},{ms:03d}", "lvl": level, "name": self.name, "msg": content, "fid": func_id, "tid": tpl_id}
                self.agent.log(json.dumps(payload_dict))
            else:
                payload = f"{ts},{ms:03d} [{self.name}] {level}: {content}"
                self.agent.log(payload)

        # Handle COMPRESS mode
        elif current_type == LogType.COMPRESS:
            buffer = CURRENT_LOG_BUFFER.get()
            if buffer is not None:
                stored_args = args
                if args and len(args) == 1 and isinstance(args[0], tuple):
                    stored_args = args[0]
                buffer.append((tpl_id, stored_args or ()))
            else:
                # Fallback if log is called outside a traced function
                original_type = self.config.log_type
                self.config.log_type = LogType.NORMAL
                self._log(level, f"{msg} (Outside Trace Context)", args)
                self.config.log_type = original_type

    def info(self, msg, *args):
        self._log("INFO", msg, args)

    def error(self, msg, *args):
        self._log("ERROR", msg, args)

    def warning(self, msg, *args):
        self._log("WARNING", msg, args)

    def debug(self, msg, *args):
        self._log("DEBUG", msg, args)

    def __call__(self, msg, *args):
        self.info(msg, *args)


def add_logger_to(obj, logger):
    """
    Helper to attach a logger instance to a class or routine.
    """
    from inspect import isclass

    def mangle_name(internal_name, class_name):
        return "_%s%s" % (class_name.lstrip('_'), internal_name)

    if isclass(obj):
        setattr(obj, mangle_name("__log", obj.__name__), logger)
    else:
        obj._log = logger
    return obj
