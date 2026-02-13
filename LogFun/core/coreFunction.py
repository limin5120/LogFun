import time
import sys
import contextvars
import os
import json
from functools import wraps
from inspect import isgenerator
from .config import get_config, LogType
from .agent import get_agent
from .registry import get_registry
from .logger import CURRENT_LOG_BUFFER
from .context import CURRENT_FUNC_ID
from .controller import get_controller


def make_trace_function(function, logger):
    ghost = FunctionTracingGhost(function, logger)

    @wraps(function)
    def autologging_traced_function_ghost(*args, **keywords):
        return ghost(function, args, keywords)

    if not hasattr(autologging_traced_function_ghost, "__wrapped__"):
        autologging_traced_function_ghost.__wrapped__ = function
    return autologging_traced_function_ghost


class FunctionTracingGhost(object):
    def __init__(self, function, logger):
        self.func_name = getattr(function, "__qualname__", function.__name__)
        self.logger = logger
        self.config = get_config()
        self.agent = get_agent()
        self.registry = get_registry()
        self.controller = get_controller()

        try:
            filename = os.path.abspath(function.__code__.co_filename)
        except AttributeError:
            filename = "unknown"

        self.unique_func_key = f"{filename}:{self.func_name}"
        # Cache ID for performance
        self.cached_func_id = self.registry.get_func_id(self.unique_func_key)

    def __call__(self, function, args, keywords):
        func_id = self.cached_func_id
        # Set context first to allow internal logging control even if muted
        token_fid = CURRENT_FUNC_ID.set(func_id)

        try:
            if self.controller.should_mute(func_id):
                return function(*args, **keywords)

            current_type = self.config.log_type
            if current_type == LogType.NORMAL:
                return self._run_normal(function, args, keywords)
            elif current_type == LogType.COMPRESS:
                return self._run_compress(function, args, keywords, func_id)
            else:
                return function(*args, **keywords)
        finally:
            CURRENT_FUNC_ID.reset(token_fid)

    def _run_normal(self, function, args, keywords):
        self.logger.info("Call %s | Args: %s Kwargs: %s", self.func_name, args, keywords)
        start_time = time.time()
        try:
            value = function(*args, **keywords)
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            self.logger.error("Error in %s: %s | Duration: %.3fms", self.func_name, e, duration)
            raise e
        duration = (time.time() - start_time) * 1000
        if isgenerator(value):
            return GeneratorIteratorTracingProxy(function, value, self.logger)
        self.logger.info("Return %s | Value: %s | Duration: %.3fms", self.func_name, value, duration)
        return value

    def _run_compress(self, function, args, keywords, func_id):
        token_buf = CURRENT_LOG_BUFFER.set([])
        start_time = time.time()
        try:
            value = function(*args, **keywords)
        finally:
            buffer = CURRENT_LOG_BUFFER.get()
            CURRENT_LOG_BUFFER.reset(token_buf)
            duration = (time.time() - start_time) * 1000
            self._flush_compressed_log(start_time, duration, buffer, func_id)
        if isgenerator(value):
            return GeneratorIteratorTracingProxy(function, value, self.logger)
        return value

    def _flush_compressed_log(self, start_time, duration, buffer, func_id):
        if not buffer: return

        # Buffer item format: (level, tpl_id, args_tuple)

        # 1. Prepare Log Metadata: [[Level, TplID], ...]
        # This structure maps 1:1 with the execution order
        log_meta = [[item[0], item[1]] for item in buffer]

        # 2. Flatten all variables
        all_vars = []
        for item in buffer:
            # item[2] is the args tuple
            all_vars.extend(item[2])

        # 3. Construct Payload
        # Format: <Timestamp> <AppID> <FuncID> <Duration> <LogDataJSON> <VarsJSON>
        # Use JSON for complex structures to avoid delimiter collision and handle escaping
        try:
            app_id = self.registry.app_id
            log_data_json = json.dumps(log_meta, ensure_ascii=False)
            vars_json = json.dumps(all_vars, ensure_ascii=False)

            payload = f"{start_time:.4f} {app_id} {func_id} {duration:.2f} {log_data_json} {vars_json}"
            self.agent.log(payload)
        except Exception:
            # Failsafe for serialization errors
            pass


class GeneratorIteratorTracingProxy(object):
    def __init__(self, generator, generator_iterator, logger):
        self.name = getattr(generator, "__qualname__", generator.__name__)
        self._gi = generator_iterator
        self.logger = logger

    def __iter__(self):
        try:
            for next_value in self._gi:
                yield next_value
        except Exception as e:
            raise e

    def __getattr__(self, name):
        return getattr(self._gi, name)
