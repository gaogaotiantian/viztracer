# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

from viztracer import VizCounter, VizTracer

from .base_tmpl import BaseTmpl


class Hello(VizCounter):
    def __init__(self, tracer, name):
        super().__init__(tracer, name, trigger_on_change=False)


class TestCounterClass(BaseTmpl):
    def test_basic(self):
        tracer = VizTracer(verbose=0)
        tracer.start()
        counter = VizCounter(tracer, "name")
        counter.a = 1
        counter.b = 2
        tracer.stop()
        entries = tracer.parse()
        self.assertEqual(entries, 2)

    def test_exception(self):
        tracer = VizTracer(verbose=0)
        tracer.start()
        counter = VizCounter(tracer, "name")
        with self.assertRaises(Exception) as _:
            counter.a = ""
        with self.assertRaises(Exception) as _:
            counter.b = {}
        with self.assertRaises(Exception) as _:
            counter.c = []
        tracer.stop()
        tracer.clear()

    def test_inherit(self):
        tracer = VizTracer(verbose=0)
        tracer.start()
        a = Hello(tracer, "name")
        a.b = 1
        a.c = 2
        a.d = 3
        a.log()
        tracer.stop()
        entries = tracer.parse()
        tracer.save()
        self.assertEqual(entries, 2)

    def test_notracer(self):
        counter = VizCounter(None, "name")
        counter.a = 1
        counter.b = 2

        a = Hello(None, "name")
        a.b = 1
        a.c = 2
        a.d = 3
        a.log()
