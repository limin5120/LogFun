import json
import logging
from .config import *


def setup_socket():
    """
    Initialize the remote server.
    If the server is not available, it will change to global `dev` mode.
    `File templates` and `context templates` will be initialized at the same time.
    """
    global MODE, DEFAULT_LOCK
    global TEMPLATES_LOCK, FILE_TEMPLATES, CONTEXT_TEMPLATES, LEN_FT, LEN_CT
    try:
        SOCKET.connect_ex((LOG_DECODER_IP, LOG_DECODER_PROT))
        SOCKET.send('Initial'.encode('utf-8'))
        if TEMPLATES_LOCK:
            TEMPLATES_LOCK = False
            data = SOCKET.recv(8192)
            data = json.loads(data.decode('utf-8'))
            FILE_TEMPLATES = {v: int(k) for k, v in data[0].items()}
            LEN_FT = len(FILE_TEMPLATES)
            CONTEXT_TEMPLATES = {v: int(k) for k, v in data[1].items()}
            LEN_CT = len(CONTEXT_TEMPLATES)
        else:
            SOCKET.recv(8192)
    except Exception or socket.timeout as e:
        DEFAULT_LOCK = False
        MODE = 'dev'
        logging.basicConfig(filename="./dev.log", filemode='a', level=logging.DEBUG, format=STD_FORMAT, datefmt='%Y %H:%M:%S')
        SOCKET.close()
        print('LogServer is not available in ({}:{}) ERROR:{}'.format(LOG_DECODER_IP, LOG_DECODER_PROT, e))
        print('Logs will not be send to LogServer.')


def save_to_server_socket(title, contents, header=2):
    """
    Save to remote socket server

    - title: log pid, file path id, template id sequences
    - contents: code line, context params, timestamps
    - header: message type, 0: 'ft' (file template), 1: 'ct' (context template), 
                            2: 'msg' (real messages),3: 'seq' (templates sequence)
    """
    global FILE_TEMPLATES, LEN_FT, CONTEXT_TEMPLATES, LEN_CT
    global SEQUENCE, LEN_SEQ, SEQUENCE_LOCK
    if len(FILE_TEMPLATES) != LEN_FT:
        LEN_FT = len(FILE_TEMPLATES)
        try:
            ft = [0] + [FILE_TEMPLATES]
            SOCKET.send(json.dumps(ft).encode())
            SOCKET.recv(8192)
        except Exception as e:
            print("Update file templates failed. ERROR:", e)
            pass
    if len(CONTEXT_TEMPLATES) != LEN_CT:
        LEN_CT = len(CONTEXT_TEMPLATES)
        try:
            ct = [1] + [CONTEXT_TEMPLATES]
            SOCKET.send(json.dumps(ct).encode())
            SOCKET.recv(8192)
        except Exception as e:
            print("Update context templates failed. ERROR:", e)
            pass
    if LEN_SEQ != 0 and len(SEQUENCE) == LEN_SEQ and SEQUENCE_LOCK:
        SEQUENCE_LOCK = False
        try:
            seq = [3] + [GLOBAL_PATH] + [SEQUENCE]
            SOCKET.send(json.dumps(seq).encode())
            SOCKET.recv(8192)
        except Exception as e:
            print("Update templates sequence failed. ERROR:", e)
            pass
    if len(SEQUENCE) != LEN_SEQ:
        LEN_SEQ = len(SEQUENCE)
        SEQUENCE_LOCK = True
    msg = [header] + [title] + [contents]
    try:
        SOCKET.send(json.dumps(msg).encode())
        SOCKET.recv(8192)
    except Exception as e:
        print("Send logs failed. ERROR:", e)
        pass