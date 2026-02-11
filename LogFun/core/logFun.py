from .config import get_config
from .logger import Logger, add_logger_to
from .coreFunction import make_trace_function
from .coreClass import install_trace_methods
from inspect import isclass, isroutine


def traced(*args, **keywords):
    obj = args[0] if args else None
    t_methods = keywords.get("methods", [])
    t_exclude = keywords.get("exclude", False)

    if obj:
        logger = Logger(name=obj.__name__)
        add_logger_to(obj, logger)
    else:
        return lambda real_obj: traced(real_obj, **keywords)

    if isroutine(obj):
        return make_trace_function(obj, logger)
    elif isclass(obj):
        return install_trace_methods(obj, logger, t_methods, t_exclude)
    elif isinstance(obj, tuple):
        return lambda class_or_fn: traced(class_or_fn, **keywords)
    else:
        return obj


def basicConfig(**keywords):
    """
    Configure Global Settings.
    Supported keys: mode, logtype, output, app_name, manager_ip, manager_port
    """
    config = get_config()

    if "mode" in keywords:
        config.mode = keywords.get("mode")
    if "logtype" in keywords:
        config.log_type = keywords.get("logtype")
    if "output" in keywords:
        config.output_dir = keywords.get("output")

    # Batch update for other props including network config
    update_kwargs = {}
    for k in ["app_name", "manager_ip", "manager_port"]:
        if k in keywords:
            update_kwargs[k] = keywords.get(k)

    if update_kwargs:
        config.update(**update_kwargs)


def gzip_file(filename):
    pass
