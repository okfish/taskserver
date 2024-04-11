import time, timeit
import functools
import logging


logger = logging.getLogger('taskserver')


def log_timings(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = timeit.default_timer()
        res = await func(*args, **kwargs)
        end_time = timeit.default_timer()
        delta = end_time - start_time
        t_str = f'{end_time - start_time} c'
        if delta > 60:
            t_str = time.strftime("%H:%M:%S", time.gmtime(delta))
        logger.debug(f'{func.__name__} elapsed time: {t_str}')
        return res
    return wrapper
