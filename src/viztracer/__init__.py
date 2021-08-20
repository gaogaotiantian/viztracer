# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

__version__ = "0.13.4"


from .viztracer import VizTracer
from .util import get_tracer
from .decorator import ignore_function, trace_and_save, log_sparse
from .vizcounter import VizCounter
from .vizobject import VizObject
from .vizlogging import VizLoggingHandler
from .cellmagic import load_ipython_extension
from .main import main
from .simulator import main as sim_main
from .viewer import viewer_main


__all__ = [
    "__version__",
    "main",
    "sim_main",
    "viewer_main",
    "VizTracer",
    "ignore_function",
    "trace_and_save",
    "log_sparse",
    "get_tracer",
    "VizCounter",
    "VizObject",
    "VizLoggingHandler",
    "load_ipython_extension"
]
