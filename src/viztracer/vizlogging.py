from logging import Handler


class VizLoggingHandler(Handler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._tracer = None

    def emit(self, record):
        if not self._tracer:
            raise Exception("You need to set the tracer first! use handler.setTracer() function")
        self._tracer.add_instant("logging", {"data": self.format(record)}, scope="p")

    def setTracer(self, tracer):
        self._tracer = tracer
