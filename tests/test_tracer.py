# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

import os
import unittest
from viztracer.tracer import _VizTracer


def fib(n):
    if n <= 1:
        return 1
    return fib(n-1) + fib(n-2)


class TestTracer(unittest.TestCase):
    def test_double_parse(self):
        tracer = _VizTracer()
        tracer.start()
        fib(10)
        tracer.stop()
        tracer.parse()
        result1 = tracer.generate_report()
        tracer.parse()
        result2 = tracer.generate_report()
        self.assertEqual(result1, result2)


class TestCTracer(unittest.TestCase):
    def test_c_load(self):
        tracer = _VizTracer(tracer="c")
        tracer.start()
        fib(5)
        tracer.stop()
        tracer.parse()

    def test_c_run_after_clear(self):
        tracer = _VizTracer(tracer="c")
        tracer.start()
        fib(5)
        tracer.stop()
        entries1 = tracer.parse()
        report1 = tracer.generate_report()
        tracer.start()
        fib(5)
        tracer.stop()
        entries2 = tracer.parse()
        report2 = tracer.generate_report()
        self.assertEqual(entries1, entries2)
        self.assertNotEqual(report1, report2)

    def test_c_cleanup(self):
        tracer = _VizTracer(tracer="c")
        tracer.start()
        fib(5)
        tracer.stop()
        tracer.cleanup()
        tracer.clear()
        tracer.cleanup()


class TestTracerFilter(unittest.TestCase):
    def test_max_stack_depth(self):
        tracer = _VizTracer(tracer="c", max_stack_depth=3)
        tracer.start()
        fib(10)
        tracer.stop()
        entries = tracer.parse()
        self.assertEqual(entries, 7)
        tracer = _VizTracer(tracer="python", max_stack_depth=3)
        tracer.start()
        fib(10)
        tracer.stop()
        entries = tracer.parse()
        self.assertEqual(entries, 10)

    def test_include_files(self):
        tracer = _VizTracer(tracer="c", include_files=["./src/"])
        tracer.start()
        fib(10)
        tracer.stop()
        entries = tracer.parse()
        self.assertEqual(entries, 0)

        tracer.include_files = [os.path.abspath("./")]
        tracer.start()
        fib(10)
        tracer.stop()
        entries = tracer.parse()
        self.assertEqual(entries, 177)

        tracer.include_files = ["./"]
        tracer.start()
        fib(10)
        tracer.stop()
        entries = tracer.parse()
        self.assertEqual(entries, 177)

    def test_exclude_files(self):
        tracer = _VizTracer(tracer="c", exclude_files=["./src/"])
        tracer.start()
        fib(10)
        tracer.stop()
        entries = tracer.parse()
        self.assertEqual(entries, 177)

        tracer.exclude_files = [os.path.abspath("./")]
        tracer.start()
        fib(10)
        tracer.stop()
        entries = tracer.parse()
        self.assertEqual(entries, 0)

        tracer.exclude_files = ["./"]
        tracer.start()
        fib(10)
        tracer.stop()
        entries = tracer.parse()
        self.assertEqual(entries, 0)

    def test_include_exclude_exception(self):
        tracer = _VizTracer(tracer="c", exclude_files=["./src/"], include_files=["./"])
        with self.assertRaises(Exception):
            tracer.start()
        tracer = _VizTracer(tracer="c", exclude_files=["./src/"])
        tracer.include_files = ["./"]
        with self.assertRaises(Exception):
            tracer.start()
        tracer.exclude_files = None
        tracer.start()
        tracer.stop()

    def test_ignore_c_function(self):
        tracer = _VizTracer(tracer="c")
        tracer.start()
        lst = []
        lst.append(1)
        tracer.stop()
        entries = tracer.parse()
        self.assertEqual(entries, 1)

        tracer.ignore_c_function = True
        tracer.start()
        lst = []
        lst.append(1)
        tracer.stop()
        entries = tracer.parse()
        self.assertEqual(entries, 0)
    
    def test_log_return_value(self):
        tracer = _VizTracer(tracer="c")
        tracer.start()
        fib(5)
        tracer.stop()
        tracer.parse()
        self.assertFalse("args" in tracer.data["traceEvents"][0])

        tracer.log_return_value = True
        tracer.start()
        fib(5)
        tracer.stop()
        tracer.parse()
        self.assertTrue("args" in tracer.data["traceEvents"][0] and \
                        "return_value" in tracer.data["traceEvents"][0]["args"])
