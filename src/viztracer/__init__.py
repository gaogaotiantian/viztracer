# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

__version__ = "1.1.1"


from .cellmagic import load_ipython_extension
from .decorator import ignore_function, log_sparse, trace_and_save
from .viztracer import VizTracer, get_tracer

__all__ = [
    "__version__",
    "VizTracer",
    "ignore_function",
    "trace_and_save",
    "log_sparse",
    "get_tracer",
    "load_ipython_extension",
]
