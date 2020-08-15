# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/codesnap/blob/master/NOTICE.txt

import unittest
import os
from viztracer.tracer import _VizTracer
from viztracer import VizTracer


def fib(n):
    if n == 1 or n == 0:
        return 1
    return fib(n-1) + fib(n-2)


class TestTracerBasic(unittest.TestCase):
    def test_construct(self):
        def fib(n):
            if n == 1 or n == 0:
                return 1
            return fib(n-1) + fib(n-2)
        t = _VizTracer()
        t.start()
        fib(5)
        t.stop()
        entries = t.parse()
        self.assertEqual(entries, 30)
        t.generate_report()

    def test_builtin_func(self):
        def fun(n):
            import random
            for _ in range(n):
                random.randrange(n)
        t = _VizTracer()
        t.start()
        fun(10)
        t.stop()
        entries = t.parse()
        self.assertEqual(entries, 42)


class TestCodeSnapBasic(unittest.TestCase):
    def test_run(self):
        snap = VizTracer()
        snap.run("import random; random.randrange(10)")
    
    def test_with(self):
        with VizTracer(output_file="test_with.json") as tracer:
            fib(10)
        self.assertTrue(os.path.exists("test_with.json"))
        os.remove("test_with.json")


class TestCodeSnapOutput(unittest.TestCase):
    def test_json(self):
        t = _VizTracer()
        t.start()
        fib(10)
        t.stop()
        t.parse()
        t.generate_json()


class TestInstant(unittest.TestCase):
    def test_addinstant(self):
        tracer = VizTracer(tracer="c")
        tracer.start()
        tracer.add_instant("instant", {"karma": True})
        tracer.stop()
        entries = tracer.parse()
        self.assertGreater(entries, 2)
        with open("testres.html", "w") as f:
            f.write(tracer.generate_report())
