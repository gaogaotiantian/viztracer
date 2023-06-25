# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

import logging

from viztracer import VizLoggingHandler, VizTracer

from .base_tmpl import BaseTmpl


class TestLogging(BaseTmpl):
    def test_handler(self):
        tracer = VizTracer()
        handler = VizLoggingHandler()
        handler.setTracer(tracer)
        logging.getLogger().addHandler(handler)
        tracer.start()
        logging.warning("lol")
        tracer.stop()
        entries = tracer.parse()
        self.assertGreater(entries, 10)
        self.assertTrue(any([entry["ph"] == "i" for entry in tracer.data["traceEvents"]]))
        logging.getLogger().removeHandler(handler)

    def test_notracer(self):
        tracer = VizTracer()
        handler = VizLoggingHandler()
        logging.getLogger().addHandler(handler)
        tracer.start()
        logging.warning("lol")
        tracer.stop()
        logging.getLogger().removeHandler(handler)
