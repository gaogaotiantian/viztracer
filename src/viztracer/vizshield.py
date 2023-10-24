# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .viztracer import VizTracer  # pragma: no cover


class VizShield:
    def __init__(self, tracer: "VizTracer") -> None:
        self._tracer = tracer
        self._prev_ignore_stack = None

    def __enter__(self) -> None:
        if self._tracer.enable and not self._tracer.log_sparse:
            self._prev_ignore_stack = self._tracer.setignorestackcounter(0)

    def __exit__(self, type, value, trace) -> None:
        if self._prev_ignore_stack is not None:
            self._tracer.setignorestackcounter(self._prev_ignore_stack)
