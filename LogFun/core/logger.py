from .config import *
from .utils import *
from .socket import *
import time
import logging
from inspect import isclass


class Logger():
    """
    parsing templates and params in logs.
    """
    def __init__(self, mode=MODE, logtype=LOGTYPE, func="root"):
        self.logger = logging.getLogger(func)
        self.logger.setLevel(logging.INFO)
        if mode == 'run':
            setup_socket()
        elif mode == 'dev':
            handler = logging.FileHandler(filename='./dev.log', mode='a')
        elif mode == 'std':
            handler = logging.StreamHandler()
        handler.setLevel(logging.INFO)
        handler.setFormatter(logging.Formatter(fmt=STD_FORMAT, datefmt=DATE_FORMAT))
        self.logger.addHandler(handler)
        self.template = []
        self.params = []
        self.times = []
        self.mode = mode
        self.logtype = logtype

    def __encode_template(self, msg, args=None):
        """
        Encode templates to id (int), it will be added when there is a new template.
        - msg: a log template include labels such as `%s`
        - args: parameters in a log template.
        """
        if msg not in SEQUENCE:
            SEQUENCE.append(msg)
        if msg not in CONTEXT_TEMPLATES:
            num_ = len(CONTEXT_TEMPLATES) + 1
            CONTEXT_TEMPLATES[msg] = num_
            CONTEXT_TEMPLATES_R[num_] = msg
        return CONTEXT_TEMPLATES[msg], args

    def __call__(self, msg='', args=''):
        """
        Defined as `__call__`, it can be used as:
        (a) function: function._log('')
        (b) class: self.__log('')
        """
        global FILTER_TEMPLATE
        if msg in FILTER_TEMPLATE:
            return
        if msg:
            encode_id, params = self.__encode_template(msg, args)
            self.template.append(encode_id)
            self.params.append(params)
            self.times.append(int(time.time()))

    def get(self):
        """
        Output a whole log sequence in a function and reset.
        """
        templates = self.template
        params = self.params
        times = self.times
        self.params = []
        self.template = []
        self.times = []
        return templates, params, times

    def stdout_to_local(self, title, contents):
        """
        Output to local, mainly for debugging.
        - title: PID, filepath ID, template ID sequences
        - contents: function line, context params, timestamps
        """
        if self.logtype == 'compress':
            self.logger.info(title + contents)
        else:
            pid = title[0]
            func = FILE_TEMPLATES_R[title[1]] + ' ' + str(contents[0])
            beginTime = title[2][0]
            endTime = title[2][-1]
            times = title[2]
            template = title[3]
            begin = contents[1]
            context = contents[2]
            end = contents[3]
            self.logger.info(("%s %s %s Input %s") % (beginTime, pid, func, begin))
            step = 1
            for idx in range(len(template)):
                c = CONTEXT_TEMPLATES_R[template[idx]] % context[idx] if context[idx] else CONTEXT_TEMPLATES_R[template[idx]]
                self.logger.info(("%s %s %s Step %s %s") % (times[idx + 1] + beginTime, pid, func, step, c))
                step += 1
            self.logger.info(("%s %s %s Return %s") % (endTime + beginTime, pid, func, end))

        global SEQUENCE, FILTER_TEMPLATE, TRACE_FILE, FILTER_CONF
        if FILE_TEMPLATES_R[title[1]] not in LOG_TEMPLATE:
            LOG_TEMPLATE[FILE_TEMPLATES_R[title[1]]] = SEQUENCE
            LOG_TEMPLATE['_STACK'] = SEQ_STACK
            LOG_TEMPLATE['_TEMPLATES'] = CONTEXT_TEMPLATES
            LOG_TEMPLATE['_FILENAMES'] = FILE_TEMPLATES
            write_pkl(TRACE_FILE, LOG_TEMPLATE)
        SEQUENCE = []
        if os.path.exists(FILTER_CONF):
            FILTER_TEMPLATE = read_pkl(FILTER_CONF)


def add_logger_to(obj, logger):
    """
    Add logging method to function or class
    - obj: a class or function object
    - logger: logger for parsing and encoding
    - return obj with logging method
    """
    # class
    if isclass(obj):
        setattr(obj, mangle_name("__log", obj.__name__), logger)
    # function
    else:
        obj._log = logger

    return obj
