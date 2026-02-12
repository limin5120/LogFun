import time
import sys
import contextvars
import os
from functools import wraps
from inspect import isgenerator
from .config import get_config, LogType
from .agent import get_agent
from .registry import get_registry  # [FIX] Import unified registry
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
        self.registry = get_registry()  # [FIX]
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
        # [CRITICAL] Set context first to allow internal logging control even if muted
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
        # [FIX] Use static template string to prevent template ID explosion
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
        tpl_ids = [item[0] for item in buffer]
        all_vars = []
        for item in buffer:
            all_vars.extend(item[1])
        payload = f"{start_time:.4f}|{func_id}|{duration:.2f}|{tpl_ids}|{all_vars}"
        self.agent.log(payload)


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
