import functools
import viztracer.snaptrace as snaptrace


def ignore_function(func):
    @functools.wraps(func)
    def ignore_wrapper(*args, **kwargs):
        snaptrace.pause()
        ret = func(*args, **kwargs)
        snaptrace.resume()
        return ret

    return ignore_wrapper
