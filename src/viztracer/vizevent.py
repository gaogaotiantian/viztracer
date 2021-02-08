# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

class VizEvent:
    def __init__(self, tracer, event_name, file_name, lineno):
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
