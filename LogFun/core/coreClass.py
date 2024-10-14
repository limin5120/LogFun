from .utils import *
from .coreFunction import make_trace_function, FunctionTracingGhost
from types import FunctionType
from functools import wraps


def install_trace_methods(class_, logger, methods, exclude):
    """
    Install LogFun for the methods of class.
    - class_: a class being traced
    - methods: (list) the methods to be traced
    - exclude: (True) regard methods as an exclusion list
    """
    # confirm the method names of a class
    if methods:
        trace_method_names = get_trace_method_names(methods, class_, exclude)
    else:
        trace_method_names = get_default_trace_method_names(class_)

    # decorate each method with LogFun
    for name in trace_method_names:
        func_ = class_.__dict__[name]
        func_type = type(func_)

        if func_type is FunctionType:
            make_logfun = make_trace_instancemethod
        elif func_type is classmethod:
            make_logfun = make_trace_classmethod
        elif func_type is staticmethod:
            make_logfun = make_trace_staticmethod
        else:
            warnings.warn("Method not supported: %r" % func_type)
            continue

        tracing_logfun = make_logfun(func_, logger)
        setattr(class_, name, tracing_logfun)

    return class_


def make_trace_instancemethod(function, logger):
    """
    Create LogFun for unbound function
    - function: the function to be traced
    - logger: logger for parsing and encoding
    - return: an function that wraps logFun
    """
    # functions have a __get__ method, they can act as logFun
    ghost = FunctionTracingGhost(function, logger)

    @wraps(function)
    def autologging_traced_instancemethod_ghost(self_, *args, **keywords):
        method = function.__get__(self_, self_.__class__)
        return ghost(method, args, keywords)

    if not hasattr(autologging_traced_instancemethod_ghost, "__wrapped__"):
        # __wrapped__ is only set by functools.wraps() in Python 3.2+
        autologging_traced_instancemethod_ghost.__wrapped__ = function

    return autologging_traced_instancemethod_ghost


def make_trace_classmethod(method, logger):
    """
    Create a tracing Ghost for a class
    - method: the method in the class to be traced
    - logger: logger for parsing and encoding
    - return: a method that wraps logFun
    """
    function = method.__func__
    ghost = FunctionTracingGhost(function, logger)

    @wraps(function)
    def autologging_traced_classmethod_ghost(cls, *args, **keywords):
        method = method.__get__(None, cls)
        return ghost(method, args, keywords)

    if not hasattr(autologging_traced_classmethod_ghost, "__wrapped__"):
        # __wrapped__ is only set by functools.wraps() in Python 3.2+
        autologging_traced_classmethod_ghost.__wrapped__ = function

    return classmethod(autologging_traced_classmethod_ghost)


def make_trace_staticmethod(method, logger):
    """
    Create a tracing Ghost for a static method.
    - method: the static method to be traced
    - logger: logger for parsing and encoding
    - return: a method that wraps logFun
    """
    autologging_traced_staticmethod_ghost = make_trace_function(method.__func__, logger)
    return staticmethod(autologging_traced_staticmethod_ghost)
