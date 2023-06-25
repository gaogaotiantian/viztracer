# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

from viztracer import VizTracer

from .base_tmpl import BaseTmpl


class TestFastLog(BaseTmpl):
    def test_log_var(self):
        tracer = VizTracer()
        tracer.start()
        tracer.log_var("test", 3)
        tracer.log_var("test", {"a": 1, "b": [3, 4, 3.6]})
        tracer.stop()
        tracer.parse()
        self.assertEventNumber(tracer.data, 2)
        self.assertEqual(tracer.data["traceEvents"][-2]["ph"], "C")
        self.assertEqual(tracer.data["traceEvents"][-2]["args"], {"value": 3})
        self.assertEqual(tracer.data["traceEvents"][-1]["ph"], "i")
        self.assertIn("object", tracer.data["traceEvents"][-1]["args"])

    def test_log_instant(self):
        tracer = VizTracer()
        tracer.start()
        tracer.log_instant("test")
        tracer.stop()
        tracer.parse()
        self.assertEventNumber(tracer.data, 1)
        self.assertEqual(tracer.data["traceEvents"][-1]["ph"], "i")
        self.assertEqual(tracer.data["traceEvents"][-1]["name"], "test")
