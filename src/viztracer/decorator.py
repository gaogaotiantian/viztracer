# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

import functools
from viztracer import VizTracer, get_tracer
import os
import time


def ignore_function(method=None, tracer=None):
    if not tracer:
        tracer = get_tracer()
    
    def inner(func):

        @functools.wraps(func)
        def ignore_wrapper(*args, **kwargs):
            tracer.pause()
            ret = func(*args, **kwargs)
            tracer.resume()
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
            file_name = os.path.join(output_dir, "result_{}_{}.json".format(func.__name__, int(100000*time.time())))
            tracer.fork_save(file_name)
            tracer.cleanup()
            return ret

        return wrapper

    if method:
        return inner(method)
    return inner

def log_sparse(func):

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        tracer = get_tracer()
        if tracer:
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
        else:
            ret = func(*args, **kwargs)
        return ret

    return wrapper
