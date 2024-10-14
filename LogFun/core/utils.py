import sys
import json
import gzip
import pickle
import warnings
from inspect import isclass, isroutine


def mangle_name(internal_name, class_name):
    """
    Transform internal name into a "_ClassNameInternalName" name.
    - internal_name: the internal member name
    - class_name: name of the class
    - return: the transformed "_ClassNameInternalName" name
    """
    return "_%s%s" % (class_name.lstrip('_'), internal_name)


def unmangle_name(mangled_name, class_name):
    """
    Transform mangled_name into an "__internal" name.
    - mangled_name: a mangled "ClassName_internal" member name
    - class_name: name of the class where the name is defined
    - return: the transformed "__internal" name
    """
    return mangled_name.replace("_%s" % class_name.lstrip("_"), "")


def is_internal_name(name):
    """
    Whether a name is an internal name.
    - name: a name defined in class.__dict__
    - return: (True) if name is an internal name, else False
    """
    return name.startswith("__") and not name.endswith("__")


def is_special_name(name):
    """
    Whether a name is a "__special__" name.
    - name:a name defined in a class.__dict__
    - return: (True) if name is a "__special__" name, else False
    """
    return name.startswith("__") and name.endswith("__")


def get_default_trace_method_names(class_):
    """
    Return all methods defined in class.__dict__
    - class_: the class being traced
    - return: all methods of class_ 
    """
    default_trace_method_names = []
    for (name, member) in class_.__dict__.items():
        if isroutine(member) and (not is_special_name(name) or name in ("__init__", "__call__")):
            default_trace_method_names.append(name)
    return default_trace_method_names


def get_trace_method_names(methods, class_, exclude):
    """
    Confirm the method names actually defined in class.__dict__
    - methods: (list) methods names
    - class_: the class being traced
    - exclude: (True) method_names as an exclusion list
    - return: identified methods that are defined in class_
    """
    trace_method_names = []
    if not exclude:
        for name in methods:
            m_name = (name if not is_internal_name(name) else mangle_name(name, class_.__name__))
            if isroutine(class_.__dict__.get(m_name)):
                trace_method_names.append(m_name)
            else:
                warnings.warn("%r is not a method defined in %s" % (name, class_.__name__))
    else:
        trace_method_names = [
            name for name in get_default_trace_method_names(class_) if unmangle_name(name, class_.__name__) not in methods
        ]
        if not trace_method_names:
            warnings.warn(("exclude=True, the supplied method names not in %s") % class_.__name__)
    return trace_method_names


# generate_logger_name(class_)
def generate_logger_name(obj, parent_name=None):
    """
    Generate the name of a class or function.
    - obj: a class or function
    - parent_name: the name of obj's parent

    If parent_name is not specified, the default is obj's module name.
    """
    parent_logger_name = parent_name if parent_name else obj.__module__
    return "%s.%s" % (parent_logger_name, getattr(obj, "__qualname__", obj.__name__)) \
        if isclass(obj) else parent_logger_name


def write_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def write_pkl(filenane, data):
    with open(filenane, 'wb') as f:
        pickle.dump(data, f)


def read_pkl(filename):
    with open(filename, 'rb') as f:
        loaded_dict = pickle.load(f)
    return loaded_dict


def find_lastlineno(f_code):
    """
    Return the last line number of a function.
    - f_code: the bytecode object for a function, as obtained from function.__code__
    - return: the last physical line number of the function
    """
    last_line_number = f_code.co_firstlineno

    # Jython and IronPython do not have co_lnotab
    if hasattr(f_code, "co_lnotab"):
        # co_lnotab is a sequence of 2-byte offsets
        # (address offset, line number offset), each relative to the previous.
        # we only care about the line number offsets here, so start at index 1 and increment by 2
        i = 1
        while i < len(f_code.co_lnotab):
            # co_lnotab is bytes in Python 3, but str in Python 2
            last_line_number += (f_code.co_lnotab[i] if sys.version_info[0] >= 3 else ord(f_code.co_lnotab[i]))
            i += 2

    return last_line_number


def gzip_file(filename):
    with open(filename, 'rb') as f_in:
        with gzip.open(filename.split('.')[0] + '.gz', 'wb') as f_out:
            f_out.writelines(f_in)
