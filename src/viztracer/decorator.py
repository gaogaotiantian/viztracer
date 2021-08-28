# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

import functools
import os
import time
from typing import Any, Callable, Optional

from .util import get_tracer
from .viztracer import VizTracer


def ignore_function(method: Optional[Callable] = None, tracer: Optional[VizTracer] = None) -> Callable:

    def inner(func: Callable) -> Callable:

        @functools.wraps(func)
        def ignore_wrapper(*args, **kwargs) -> Any:
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


def trace_and_save(method: Optional[Callable] = None, output_dir: str = "./", **viztracer_kwargs):

    def inner(func: Callable) -> Callable:

        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
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


def log_sparse(func: Callable) -> Callable:
    tracer = get_tracer()
    if not tracer or not tracer.log_sparse:
        return func

    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        tracer = get_tracer()
        if tracer:
            # This should always be true
            start = tracer.getts()
            ret = func(*args, **kwargs)
            dur = tracer.getts() - start
            code = func.__code__
            raw_data = {
                "ph": "X",
                "name": f"{code.co_name} ({code.co_filename}:{code.co_firstlineno})",
                "ts": start,
                "dur": dur,
                "cat": "FEE"
            }
            tracer.add_raw(raw_data)
        else:  # pragma: no cover
            raise Exception("This should not be possible")
        return ret

    return wrapper
