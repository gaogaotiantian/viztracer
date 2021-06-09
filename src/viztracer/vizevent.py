# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt


from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from .viztracer import VizTracer  # pragma: no cover


class VizEvent:
    def __init__(self, tracer: "VizTracer", event_name: str, file_name: str, lineno: int):
        self._tracer = tracer
        self.event_name = event_name
        self.file_name = file_name
        self.lineno = lineno
        self.start = None

    def __enter__(self):
        self.start = self._tracer.getts()

    def __exit__(self, type, value, trace):
        dur = self._tracer.getts() - self.start
        raw_data = {
            "ph": "X",
            "name": f"{self.event_name} ({self.file_name}:{self.lineno})",
            "ts": self.start,
            "dur": dur,
            "cat": "FEE"
        }
        self._tracer.add_raw(raw_data)
