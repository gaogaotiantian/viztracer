import os

from viztracer import VizTracer


def fib(n):
    if n < 2:
        return 1
    return fib(n - 1) + fib(n - 2)


with VizTracer(log_func_args=True,
               log_func_retval=True,
               file_info=True,
               output_file=os.path.join(os.path.dirname(__file__), "../", "json/function_args_return.json")):
    fib(6)
