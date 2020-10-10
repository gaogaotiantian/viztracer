# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

__version__ = "0.8.0"


from .viztracer import VizTracer
from .flamegraph import FlameGraph
from .decorator import ignore_function, trace_and_save
from .vizcounter import VizCounter
from .vizobject import VizObject
from .vizlogging import VizLoggingHandler
from .main import main
from .simulator import main as sim_main


__all__ = [
    "__version__",
    "main",
    "sim_main",
    "VizTracer",
    "FlameGraph",
    "ignore_function",
    "trace_and_save",
    "VizCounter",
    "VizObject",
    "VizLoggingHandler"
]


def get_tracer():
    try:
        return __viz_tracer__
    except NameError:
        return None
