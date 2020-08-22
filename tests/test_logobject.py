import unittest
from viztracer import VizTracer
from viztracer import LogObject


class Hello(LogObject):
    def __init__(self, tracer):
        super().__init__(tracer, "name")
        self.a = 1
        self.b = "lol"
    
    @LogObject.snapshot
    def change_val(self):
        self.a += 1
        self.b += "a"

    @LogObject.snapshot(when="both")
    def change_val2(self):
        self.a += 2
        self.b += "b"

class TestLogObject(unittest.TestCase):
    def test_basic(self):
        tracer = VizTracer()
        tracer.start()
        a = Hello(tracer)
        a.set_viztracer_attributes(["a", "b"])
        a.change_val()
        a.change_val2()
        a = Hello(tracer)
        a.change_val()
        tracer.stop()
        entries = tracer.parse()
        tracer.save()
        self.assertEqual(entries, 8)
