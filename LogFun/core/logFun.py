from . import *
import warnings
from inspect import isclass, isroutine


def traced(*args, **keywords):
    """
    Add to an unbound function or the methods of a class
    - args func: the unbound function
    - args class: a class name
    - args method_names: the methods list of a class
    - keywords exclude: (True) set the method list to be excluded
    - keywords mode: `std` set logging to command line, 
                     `dev` set logging to local file, 
                     `run` set logging to remote server.
    """
    obj = args[0] if args else None
    global T_MODE, T_LOGTYPE, T_METHODS, T_EXCLUDE
    if keywords:
        T_MODE = keywords.get("mode", MODE)
        T_LOGTYPE = keywords.get("logtype", LOGTYPE)
        T_METHODS = keywords.get("methods", T_METHODS)
        T_EXCLUDE = keywords.get("exclude", False)
    if obj:
        mode = T_MODE if T_MODE else MODE
        logtype = T_LOGTYPE if T_LOGTYPE else LOGTYPE
        T_MODE = T_LOGTYPE = ""
        # logger for parsing and encoding
        logger = Logger(mode, logtype, obj.__name__)
        # add logger attr to a class or a function
        add_logger_to(obj, logger)
    # set @traced() as @traced
    else:
        return traced

    # LogFun for Function
    if isroutine(obj):
        return make_trace_function(obj, logger)

    # LogFun for Class
    elif isclass(obj):
        methods = T_METHODS if T_METHODS else []
        exclude = T_EXCLUDE if T_EXCLUDE else False
        T_METHODS = []
        T_EXCLUDE = False
        return install_trace_methods(obj, logger, methods, exclude)

    # LogFun for a class or a function input instance
    elif isinstance(obj, tuple):
        method_names = args[1:]

        def traced_decorator(class_or_fn):
            # input a class : @traced(logger) or @traced(logger, "method", ..)
            if isclass(class_or_fn):
                return install_trace_methods(class_or_fn, logger, *method_names, exclude=keywords.get("exclude", False))
            # input a function : @traced(logger)
            else:
                if method_names:
                    warnings.warn("Methods ignoring: %s.%s" % (class_or_fn.__module__, class_or_fn.__name__))
                return make_trace_function(class_or_fn, logger)

        return traced_decorator
    # LogFun for input exclude list of a class : @traced(exclude=["method_name1", ..])
    else:
        method_names = args[:]
        return lambda class_: install_trace_methods(class_, logger, *method_names, exclude=keywords.get("exclude", False))


def basicConfig(*args, **keywords):
    global MODE, LOGTYPE, OUTPUT_PAHT
    MODE = keywords.get("mode", MODE)
    LOGTYPE = keywords.get("logtype", LOGTYPE)
    OUTPUT_PAHT = keywords.get("output", OUTPUT_PAHT)
