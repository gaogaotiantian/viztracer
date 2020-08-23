import unittest
from viztracer import VizTracer, VizCounter


class Hello(VizCounter):
    def __init__(self, tracer, name):
        super().__init__(tracer, name, trigger_on_change=False)


class TestCounterClass(unittest.TestCase):
    def test_basic(self):
        tracer = VizTracer()
        tracer.start()
        counter = VizCounter(tracer, "name")
        counter.a = 1
        counter.b = 2
        tracer.stop()
        entries = tracer.parse()
        self.assertEqual(entries, 2)

    def test_exception(self):
        tracer = VizTracer()
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
        tracer = VizTracer()
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
