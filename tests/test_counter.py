import unittest
from viztracer import VizTracer, Counter


class TestCounterClass(unittest.TestCase):
    def callback(self, name, value):
        self.g_name = name
        self.g_value = value

    def test_basic(self):
        counter = Counter(self.callback, "name")
        self.assertEqual(counter._name, "name")
        counter.update({"a": 1})
        self.assertEqual(self.g_value["a"], 1)
        counter.update("a", 2)
        self.assertEqual(self.g_value["a"], 2)


class TestVizTracerCounter(unittest.TestCase):
    def test_basic(self):
        tracer = VizTracer()
        counter = tracer.register_counter("counter")
        tracer.start()
        counter.update("a", 3)
        counter.update({"a": 4})
        tracer.update_counter("counter", "a", 5)
        tracer.update_counter("counter", {"a": 6})
        tracer.stop()
        entries = tracer.parse()
        self.assertEqual(entries, 4)
