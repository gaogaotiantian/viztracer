# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

import functools
import os
import time
from typing import Any, Callable, Optional

from .viztracer import VizTracer, get_tracer


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
            file_name = os.path.join(output_dir, f"result_{func.__name__}_{int(100000 * time.time())}.json")
            tracer.fork_save(file_name)
            tracer.cleanup()
            return ret

        return wrapper

    if method:
        return inner(method)
    return inner

def _log_sparse_wrapper(func: Optional[Callable] = None, stack_depth: int = 0,
                        dynamic_tracer_check: bool = False) -> Callable:
    if not dynamic_tracer_check:
        tracer = get_tracer()
        if tracer is None or not tracer.log_sparse:
            if func is None:
                return lambda f: f
            return func

    if stack_depth > 0:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            local_tracer = get_tracer() if dynamic_tracer_check else tracer

            if local_tracer is None or not local_tracer.log_sparse:
                return func(*args, **kwargs)

            assert isinstance(local_tracer, VizTracer)
            if not local_tracer.enable:
                orig_max_stack_depth = local_tracer.max_stack_depth
                local_tracer.max_stack_depth = stack_depth
                local_tracer.start()
                ret = func(*args, **kwargs)
                local_tracer.stop()
                local_tracer.max_stack_depth = orig_max_stack_depth
                return ret
            else:
                return func(*args, **kwargs)
        return wrapper
    else:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            local_tracer = get_tracer() if dynamic_tracer_check else tracer

            if local_tracer is None or not local_tracer.log_sparse:
                return func(*args, **kwargs)

            assert callable(func)
            assert isinstance(local_tracer, VizTracer)
            start = local_tracer.getts()
            ret = func(*args, **kwargs)
            dur = local_tracer.getts() - start
            code = func.__code__
            raw_data = {
                "ph": "X",
                "name": f"{code.co_name} ({code.co_filename}:{code.co_firstlineno})",
                "ts": start,
                "dur": dur,
                "cat": "FEE",
            }
            local_tracer.add_raw(raw_data)
            return ret

        return wrapper


def _log_sparse_wrapper_with_args(stack_depth: int = 0, dynamic_tracer_check: bool = False) -> Callable:
    return functools.partial(_log_sparse_wrapper, stack_depth=stack_depth, dynamic_tracer_check=dynamic_tracer_check)

def log_sparse(func: Optional[Callable] = None, stack_depth: int = 0, dynamic_tracer_check: bool = False) -> Callable:
    if func is not None:
        return _log_sparse_wrapper(func=func, stack_depth=stack_depth, dynamic_tracer_check=dynamic_tracer_check)
    return _log_sparse_wrapper_with_args(stack_depth=stack_depth, dynamic_tracer_check=dynamic_tracer_check)
