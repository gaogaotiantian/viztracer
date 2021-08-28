# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

from logging import Handler, LogRecord

from .viztracer import VizTracer


class VizLoggingHandler(Handler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._tracer = None

    def emit(self, record: LogRecord):
        if not self._tracer:
            return
        self._tracer.add_instant(f"logging - {self.format(record)}", scope="p")

    def setTracer(self, tracer: VizTracer):
        self._tracer = tracer
