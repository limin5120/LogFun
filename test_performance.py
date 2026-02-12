import time
import os
import logging
import random
import string
from loguru import logger as loguru_logger
from LogFun import traced, basicConfig

# --- 1. Business Logic for Testing ---


def generate_random_str(length=10):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def business_logic(i, logger_func):
    """
    Simulates a typical task with computational load and logging.
    """
    x = i * 0.01
    y = x**2

    # Static part of the message with dynamic variables
    logger_func(f"Step 1: Start processing item {i}, val={x:.2f}")
    if i % 2 == 0:
        logger_func(f"Step 2: Even number detected {i}")
    else:
        logger_func(f"Step 2: Odd number detected {i}")

    rand_msg = generate_random_str()
    logger_func(f"Step 3: Random signature {rand_msg}")
    return y


# --- 2. Testing Wrappers ---


def test_native_logging(count, filename):
    if os.path.exists(filename): os.remove(filename)
    logger = logging.getLogger("native_test")
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(filename)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    start = time.time()
    for i in range(count):
        business_logic(i, logger.info)
    end = time.time()

    logger.removeHandler(handler)
    handler.close()
    return end - start


def test_loguru(count, filename):
    if os.path.exists(filename): os.remove(filename)
    loguru_logger.remove()
    loguru_logger.add(filename, format="{time} {level} {message}")

    start = time.time()
    for i in range(count):
        business_logic(i, loguru_logger.info)
    end = time.time()
    return end - start


@traced
def logfun_task(i):
    """
    Traced function using LogFun's variable extraction capability.
    """
    x = i * 0.01
    # Use standard formatting for best compression performance
    logfun_task._log("Step 1: Start processing item %s, val=%s", (i, f"{x:.2f}"))

    if i % 2 == 0:
        logfun_task._log("Step 2: Even number detected %s", i)
    else:
        logfun_task._log("Step 2: Odd number detected %s", i)

    rand_msg = generate_random_str()
    logfun_task._log("Step 3: Random signature %s", rand_msg)


def test_logfun(count, app_name):
    # Config: Local File + Compression Mode
    basicConfig(mode='file', logtype='compress', output='./', app_name=app_name)
    log_file = f"{app_name}.log"
    if os.path.exists(log_file): os.remove(log_file)

    start = time.time()
    for i in range(count):
        logfun_task(i)
    end = time.time()
    return end - start, log_file


# --- 3. Main Execution ---

if __name__ == "__main__":
    COUNT = 50000
    print(f"=== Performance Benchmark ({COUNT} iterations) ===")

    # Native Logging
    t_log = test_native_logging(COUNT, "bench_native.log")
    s_log = os.path.getsize("bench_native.log") / (1024 * 1024)
    print(f"Logging -> Time: {t_log:.4f}s, Size: {s_log:.2f} MB")

    # Loguru
    t_guru = test_loguru(COUNT, "bench_loguru.log")
    s_guru = os.path.getsize("bench_loguru.log") / (1024 * 1024)
    print(f"Loguru  -> Time: {t_guru:.4f}s, Size: {s_guru:.2f} MB")

    # LogFun
    t_fun, f_fun = test_logfun(COUNT, "bench_logfun")
    s_fun = os.path.getsize(f_fun) / (1024)
    print(f"LogFun  -> Time: {t_fun:.4f}s, Size: {s_fun:.2f} KB")
