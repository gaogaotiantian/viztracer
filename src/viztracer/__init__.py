# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

from .viztracer import VizTracer
from .flamegraph import FlameGraph
from .decorator import ignore_function

__version__ = "0.2.3"

__all__ = [
    "__version__",
    "VizTracer",
    "FlameGraph",
    "ignore_function"
]
