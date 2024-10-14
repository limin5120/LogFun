import os
import socket
from .utils import *

# common path
GLOBAL_PATH = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PAHT = './logfun_output/'
os.makedirs(OUTPUT_PAHT, exist_ok=True)

# mode controller
MODE = "dev"
T_MODE = ""
LOGTYPE = "compress"
T_LOGTYPE = ""
T_METHODS = []
T_EXCLUDE = False
DEFAULT_LOCK = True

# log format
STD_FORMAT = '%(message)s'  # STD_FORMAT = '%(asctime)s %(message)s'
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# log template
SEQUENCE = []
SEQ_STACK = []
LOG_TEMPLATE = dict()
CONTEXT_TEMPLATES = dict()
CONTEXT_TEMPLATES_R = dict()
FILE_TEMPLATES = dict()
FILE_TEMPLATES_R = dict()
TRACE_FILE = OUTPUT_PAHT + 'trace.pkl'
if os.path.exists(TRACE_FILE):
    LOG_TEMPLATE = read_pkl(TRACE_FILE)
    CONTEXT_TEMPLATES = LOG_TEMPLATE['_TEMPLATES']
    CONTEXT_TEMPLATES_R = {v: k for k, v in CONTEXT_TEMPLATES.items()}
    FILE_TEMPLATES = LOG_TEMPLATE['_FILENAMES']
    FILE_TEMPLATES_R = {v: k for k, v in FILE_TEMPLATES.items()}

FILTER_CONF = OUTPUT_PAHT + 'templates_config.pkl'
FILTER_TEMPLATE = dict()
if os.path.exists(FILTER_CONF):
    FILTER_TEMPLATE = read_pkl(FILTER_CONF)

LEN_FT = 0
LEN_CT = 0
TEMPLATES_LOCK = True
LEN_SEQ = 0
SEQUENCE_LOCK = True

# log basicinfo
OS_PID = os.getpid()
BEGIN_TIME = 0

# remote storing
SOCKET = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
SOCKET.settimeout(3)
LOG_DECODER_IP = '127.0.0.1'
LOG_DECODER_PROT = 5000
