import inspect
from .coreFunction import make_trace_function


def install_trace_methods(target_class, logger, methods=None, exclude=False):
    """
    Applies the tracing decorator to methods of a class.
    
    Args:
        target_class: The class object to patch.
        logger: The Logger instance associated with this class.
        methods (list): List of method names to trace (or exclude).
        exclude (bool): If True, 'methods' list acts as a blacklist. 
                        If False (default), 'methods' list acts as a whitelist.
                        If 'methods' is empty/None:
                            - exclude=False (default): Trace ALL methods.
                            - exclude=True: Trace NO methods (useless but logical).
    """
    if methods is None:
        methods = []

    # Iterate over the class dictionary directly to access descriptors
    # (staticmethod, classmethod) before they are bound.
    for name, value in list(target_class.__dict__.items()):

        # 1. Check if we should trace this attribute
        should_trace = False

        # Skip magic methods (optional, but usually safer to skip __new__, etc. unless requested)
        # Here we allow __init__ but might want to be careful with others.
        if name.startswith('__') and name.endswith('__') and name != '__init__':
            continue

        if exclude:
            # Blacklist mode: Trace if NOT in methods list
            if name not in methods:
                should_trace = True
        else:
            # Whitelist mode:
            # If methods list is empty, trace EVERYTHING (default behavior)
            # If methods list is not empty, trace only if IN list
            if not methods:
                should_trace = True
            elif name in methods:
                should_trace = True

        if not should_trace:
            continue

        # 2. Apply Tracing based on type
        # We must verify it's actually a function/method wrapper

        # Case A: @staticmethod
        if isinstance(value, staticmethod):
            raw_func = value.__func__
            traced_func = make_trace_function(raw_func, logger)
            setattr(target_class, name, staticmethod(traced_func))

        # Case B: @classmethod
        elif isinstance(value, classmethod):
            raw_func = value.__func__
            traced_func = make_trace_function(raw_func, logger)
            setattr(target_class, name, classmethod(traced_func))

        # Case C: Regular instance method (Function in Python 3 class dict)
        elif inspect.isfunction(value) or inspect.isroutine(value):
            # Double check it's not a coroutine or other exotic type if needed
            if inspect.iscoroutinefunction(value):
                # For now, treat async functions same as sync (LogFun supports them basic way)
                pass

            traced_func = make_trace_function(value, logger)
            setattr(target_class, name, traced_func)

    return target_class
