# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

import functools
from viztracer import VizTracer
import viztracer.snaptrace as snaptrace
import os
import time


def ignore_function(func):
    @functools.wraps(func)
    def ignore_wrapper(*args, **kwargs):
        snaptrace.pause()
        ret = func(*args, **kwargs)
        snaptrace.resume()
        return ret

    return ignore_wrapper


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
