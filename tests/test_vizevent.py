# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

from viztracer import VizTracer

from .base_tmpl import BaseTmpl


class TestVizEvent(BaseTmpl):
    def test_basic(self):
        tracer = VizTracer(verbose=0)
        tracer.start()
        with tracer.log_event("event"):
            a = []
            a.append(1)
        tracer.stop()
        tracer.parse()
        self.assertEventNumber(tracer.data, 2)
