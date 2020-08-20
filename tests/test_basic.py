# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

import unittest
import os
from viztracer.tracer import _VizTracer
from viztracer import VizTracer, ignore_function


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
        self.assertEqual(entries, 15)
        t.generate_report()

    def test_builtin_func(self):
        def fun(n):
            import random
            for _ in range(n):
                random.randrange(n)
        t = _VizTracer(ignore_c_function=True)
        t.start()
        fun(10)
        t.stop()
        entries = t.parse()
        self.assertEqual(entries, 21)

    def test_cleanup(self):
        def fib(n):
            if n == 1 or n == 0:
                return 1
            return fib(n-1) + fib(n-2)
        t = _VizTracer()
        t.start()
        fib(5)
        t.stop()
        t.cleanup()
        entries = t.parse()
        self.assertEqual(entries, 0)


class TestCodeSnapBasic(unittest.TestCase):
    def test_run(self):
        snap = VizTracer()
        snap.run("import random; random.randrange(10)")

    def test_with(self):
        with VizTracer(output_file="test_with.json") as _:
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
        self.assertEqual(entries, 1)


class TestDecorator(unittest.TestCase):
    def test_pause_resume(self):
        @ignore_function
        def ignore(n):
            if n == 0:
                return 1
            return ignore(n-1) + 1
        tracer = VizTracer(tracer="c")
        tracer.start()
        ignore(10)
        tracer.stop()
        entries = tracer.parse()
        self.assertEqual(entries, 0)


class TestLogPrint(unittest.TestCase):
    def test_log_print(self):
        tracer = VizTracer(log_print=True)
        tracer.start()
        print("hello")
        print("hello")
        print("hello")
        print("hello")
        tracer.stop()
        entries = tracer.parse()
        self.assertEqual(entries, 4)
