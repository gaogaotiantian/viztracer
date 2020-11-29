# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

import functools
from viztracer import VizTracer, get_tracer
import os
import time


def ignore_function(method=None, tracer=None):

    def inner(func):

        @functools.wraps(func)
        def ignore_wrapper(*args, **kwargs):
            # We need this to keep trace a local variable
            t = tracer
            if not t:
                t = get_tracer()
                if not t:
                    raise NameError("ignore_function only works with global tracer")
            t.pause()
            ret = func(*args, **kwargs)
            t.resume()
            return ret

        return ignore_wrapper

    if method:
        return inner(method)
    return inner


def trace_and_save(method=None, output_dir="./", **viztracer_kwargs):

    def inner(func):

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            tracer = VizTracer(**viztracer_kwargs)
            tracer.start()
            ret = func(*args, **kwargs)
            tracer.stop()
            if not os.path.exists(output_dir):
                os.mkdir(output_dir)
            file_name = os.path.join(output_dir, "result_{}_{}.json".format(func.__name__, int(100000 * time.time())))
            tracer.fork_save(file_name)
            tracer.cleanup()
            return ret

        return wrapper

    if method:
        return inner(method)
    return inner


def log_sparse(func):
    tracer = get_tracer()
    if not tracer or not tracer.log_sparse:
        return func

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        tracer = get_tracer()
        if tracer:
            # This should always be true
            start = tracer._tracer.getts()
            ret = func(*args, **kwargs)
            dur = tracer._tracer.getts() - start
            raw_data = {
                "ph": "X",
                "name": func.__qualname__,
                "ts": start,
                "dur": dur,
                "cat": "FEE"
            }
            tracer._tracer.addraw(raw_data)
        else:  # pragma: no cover
            raise Exception("This should not be possible")
        return ret

    return wrapper
