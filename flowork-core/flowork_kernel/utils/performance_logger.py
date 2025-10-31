#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\utils\performance_logger.py JUMLAH BARIS 34 
#######################################################################

import time
from functools import wraps
def log_performance(log_message: str):
    """
    A decorator that logs the execution time of a function.
    It accesses the kernel logger through the 'self' argument of the decorated method.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            instance = args[0] if args else None
            kernel = getattr(instance, 'kernel', None)
            logger = None
            if kernel and hasattr(kernel, 'write_to_log'):
                logger = kernel.write_to_log
            start_time = time.perf_counter()
            result = func(*args, **kwargs)
            end_time = time.perf_counter()
            duration_ms = (end_time - start_time) * 1000
            if logger:
                log_entry = f"PERF: {log_message} - Execution Time: {duration_ms:.2f} ms"
                logger(log_entry, "DEBUG")
            else:
                print(f"[PERFORMANCE LOG] {log_message} - Time: {duration_ms:.2f} ms")
            return result
        return wrapper
    return decorator
