from .config import *
from .socket import *
from .utils import *
import time
import platform
from functools import wraps
from inspect import isgenerator

# BEGIN IronPython detection
# (this needs to be implemented consistently w/r/t Aglyph's aglyph._compat)
try:
    _py_impl = platform.python_implementation()
except:
    _py_impl = "Python"

try:
    import clr
    clr.AddReference("System")
    _has_clr = True
except:
    _has_clr = False

_is_ironpython = _py_impl == "IronPython" and _has_clr
# END IronPython detection


def make_trace_function(function, logger):
    """
    Create LogFun for a function
    - function: an unbound, module-level (or nested) function
    - logger: logger for parsing and encoding
    - return: a function that wraps LogFun
    """
    ghost = FunctionTracingGhost(function, logger)

    @wraps(function)
    def autologging_traced_function_ghost(*args, **keywords):
        return ghost(function, args, keywords)

    if not hasattr(autologging_traced_function_ghost, "__wrapped__"):
        # __wrapped__ is only set by functools.wraps() in Python 3.2+
        autologging_traced_function_ghost.__wrapped__ = function

    return autologging_traced_function_ghost


class FunctionTracingGhost(object):
    """
    Ghost a function to capture the call arguments and return value.
    """
    def __init__(self, function, logger):
        """
        - function: the function name
        - logger: logger for parsing and encoding
        """
        self.func_code = function.__code__
        self.logger = logger
        self._func_name = [
            self.__encode_filename(self.func_code.co_filename, self.func_code.co_name), self.func_code.co_firstlineno
        ]

    def __encode_filename(self, path, func):
        """
        Encode filename to id (int), it will be added to `file_template_list` when there is a new filename.
        - path: whole file path of the function
        - func: function name
        """
        global FILE_TEMPLATES, SEQ_STACK
        filename = " ".join([path, func])
        if filename not in FILE_TEMPLATES:
            num_ = len(FILE_TEMPLATES) + 1
            FILE_TEMPLATES[filename] = num_
            FILE_TEMPLATES_R[num_] = filename
        return FILE_TEMPLATES[filename]

    def __call__(self, function, args, keywords):
        """
        Call function, tracing arguments and return value.
        - args: the positional arguments for *function*
        - keywords: the keyword arguments for *function*
        """
        title = []
        contents = []
        title.append(OS_PID)
        title.append(self._func_name[0])
        contents.append(self._func_name[1])
        contents.append(str(args) if args else None)
        begin_time = int(time.time())
        global SEQ_STACK
        SEQ_STACK.append(self.func_code.co_name)
        try:
            value = function(*args, **keywords)
        except Exception as e:
            value = "ERROR: " + str(e)
        SEQ_STACK.append(self.func_code.co_name)
        templates, params, times = self.logger.get()
        times.append(int(time.time()))
        times = [begin_time] + [t - begin_time for t in times]
        title.append(times)
        title.append(templates)
        contents.append(params)
        contents.append(value)
        if self.logger.mode == 'run':
            save_to_server_socket(title, contents)
        else:
            self.logger.stdout_to_local(title, contents)
        return (GeneratorIteratorTracingProxy(function, value, self.logger) if isgenerator(value) else value)


class GeneratorIteratorTracingProxy(object):
    """
    the iterator protocol for a generator iterator to capture and trace `yield` and `StopIteration` events.
    """
    def __init__(self, generator, generator_iterator, logger):
        """
        - generator: the generator function that produced generator_iterator
        - generator_iterator: a generator iterator returned by a traced function
        - logger: logger for parsing and encoding
        """
        self._fallback_lineno = find_lastlineno(generator.__code__)
        self._gi = generator_iterator
        self.logger = logger

    @property
    def __wrapped__(self):
        """
        The original generator iterator.
        """
        return self._gi

    @property
    def _gi_lineno(self):
        return (self._gi.gi_frame.f_lineno if not _is_ironpython else self._fallback_lineno)

    def __iter__(self):
        """
        Trace each `yield` and the terminating `StopIteration` for the wrapped generator iterator.
        """
        # get this now in case the generator iterator is empty
        # (gi.gi_frame is None when the generator iterator is finished.)
        gi_lineno = self._gi_lineno

        for next_value in self._gi:
            gi_lineno = self._gi_lineno
            contents = []
            entertime = int(time.time())
            func_name = " ".join([self._gi.gi_code.co_filename, self._gi.gi_code.co_name, str(gi_lineno)])
            contents.append(OS_PID)
            contents.append(func_name)
            contents.append(next_value)
            contents.append(None)
            contents.append(None)
            contents.append([entertime, int(time.time())])
            save_to_server_socket(contents)
            # print(json.dumps(contents))
            yield next_value

    def __getattr__(self, name):
        """
        Delegate unimplemented methods/properties to the original generator iterator.
        """
        return getattr(self._gi, name)
