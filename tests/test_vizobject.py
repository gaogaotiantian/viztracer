import unittest
from viztracer import VizTracer
from viztracer import VizObject


class Hello(VizObject):
    def __init__(self, tracer):
        super().__init__(tracer, "name", trigger_on_change=False)
        self.a = 1
        self.b = "lol"

    @VizObject.triggerlog
    def change_val(self):
        self.a += 1
        self.b += "a"

    @VizObject.triggerlog(when="both")
    def change_val2(self):
        self.a += 2
        self.b += "b"


class TestVizObject(unittest.TestCase):
    def test_basic(self):
        tracer = VizTracer()
        tracer.start()
        a = VizObject(tracer, "my variable")
        a.hello = 1
        a.hello = 2
        tracer.stop()
        entries = tracer.parse()
        del a
        self.assertEqual(entries, 3)

    def test_include(self):
        tracer = VizTracer()
        tracer.start()
        a = VizObject(tracer, "my variable", include_attributes=["b", "c"])
        a.hello = 1
        a.b = 2
        a.c = 3
        a.lol = 4
        tracer.stop()
        entries = tracer.parse()
        del a
        self.assertEqual(entries, 3)

    def test_exclude(self):
        tracer = VizTracer()
        tracer.start()
        a = VizObject(tracer, "my variable", exclude_attributes=["b", "c"])
        a.hello = 1
        a.b = 2
        a.c = 3
        a.lol = 4
        tracer.stop()
        entries = tracer.parse()
        del a
        self.assertEqual(entries, 3)

    def test_trigger_on_change(self):
        tracer = VizTracer()
        tracer.stop()
        tracer.cleanup()
        tracer.start()
        a = VizObject(tracer, "my variable", trigger_on_change=False)
        a.hello = 1
        a.b = 2
        a.c = 3
        a.lol = 4
        a.log()
        tracer.stop()
        entries = tracer.parse()
        tracer.save()
        del a
        self.assertEqual(entries, 2)

    def test_config(self):
        tracer = VizTracer()
        tracer.start()
        a = VizObject(tracer, "my variable")
        a.config("trigger_on_change", False)
        a.hello = 1
        a.b = 2
        a.c = 3
        a.lol = 4
        a.log()
        tracer.stop()
        del a
        entries = tracer.parse()
        self.assertEqual(entries, 2)

    def test_decorator(self):
        tracer = VizTracer()
        tracer.start()
        a = Hello(tracer)
        a.config("include_attributes", ["a", "b"])
        a.change_val()
        a.change_val2()
        b = Hello(tracer)
        b.config("include_attributes", ["a", "b"])
        b.change_val()
        b.change_val2()
        tracer.stop()
        entries = tracer.parse()
        del a
        del b
        self.assertEqual(entries, 10)
