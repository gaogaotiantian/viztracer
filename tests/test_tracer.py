# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

import io
import os
import time

from viztracer import VizTracer
from viztracer.tracer import _VizTracer

from .base_tmpl import BaseTmpl


def fib(n):
    if n <= 1:
        return 1
    return fib(n - 1) + fib(n - 2)


class TestTracer(BaseTmpl):
    def test_double_parse(self):
        tracer = VizTracer(verbose=0)
        tracer.start()
        fib(10)
        tracer.stop()
        tracer.parse()
        result1 = tracer.save()
        tracer.parse()
        result2 = tracer.save()
        self.assertEqual(result1, result2)


class TestCTracer(BaseTmpl):
    def test_c_load(self):
        tracer = _VizTracer()
        tracer.start()
        fib(5)
        tracer.stop()
        tracer.parse()

    def test_c_run_after_clear(self):
        tracer = VizTracer(verbose=0)
        tracer.start()
        fib(5)
        tracer.stop()
        entries1 = tracer.parse()
        with io.StringIO() as s:
            tracer.save(s)
            report1 = s.getvalue()
        tracer.start()
        fib(5)
        tracer.stop()
        entries2 = tracer.parse()
        with io.StringIO() as s:
            tracer.save(s)
            report2 = s.getvalue()
        self.assertEqual(entries1, entries2)
        self.assertNotEqual(report1, report2)

    def test_c_cleanup(self):
        tracer = _VizTracer()
        tracer.start()
        fib(5)
        tracer.stop()
        tracer.cleanup()
        tracer.clear()
        tracer.cleanup()


class TestCircularBuffer(BaseTmpl):
    def test_wrap(self):
        tracer = _VizTracer(tracer_entries=10)
        tracer.start()
        fib(10)
        tracer.stop()
        entries = tracer.parse()
        self.assertEqual(entries, 10)


class TestTracerFilter(BaseTmpl):
    def test_max_stack_depth(self):
        tracer = _VizTracer(max_stack_depth=3)
        tracer.start()
        fib(10)
        tracer.stop()
        entries = tracer.parse()
        self.assertEqual(entries, 7)

    def test_include_files(self):
        tracer = _VizTracer(include_files=["./src/"])
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
        tracer = _VizTracer(exclude_files=["./src/"])
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

        tracer.exclude_files = []
        tracer.start()
        fib(10)
        tracer.stop()
        entries = tracer.parse()
        self.assertEqual(entries, 177)

    def test_include_exclude_exception(self):
        tracer = _VizTracer(exclude_files=["./src/"], include_files=["./"])
        with self.assertRaises(Exception):
            tracer.start()
        tracer = _VizTracer(exclude_files=["./src/"])
        tracer.include_files = ["./"]
        with self.assertRaises(Exception):
            tracer.start()
        tracer.exclude_files = None
        tracer.start()
        tracer.stop()

    def test_ignore_c_function(self):
        tracer = _VizTracer()
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

    def test_ignore_frozen(self):
        tracer = _VizTracer(ignore_frozen=True)
        tracer.start()
        import random  # noqa: F401
        lst = []
        lst.append(1)
        tracer.stop()
        entries = tracer.parse()
        self.assertEqual(entries, 1)


class TestTracerFeature(BaseTmpl):
    def test_log_func_retval(self):
        tracer = _VizTracer()
        tracer.start()
        fib(5)
        tracer.stop()
        tracer.parse()
        events = [e for e in tracer.data["traceEvents"] if e["ph"] != "M"]
        self.assertFalse("args" in events[0])

        tracer.log_func_retval = True
        tracer.start()
        fib(5)
        tracer.stop()
        tracer.parse()
        events = [e for e in tracer.data["traceEvents"] if e["ph"] != "M"]
        self.assertTrue("args" in events[0]
                        and "return_value" in events[0]["args"])

    def test_log_func_args(self):
        tracer = _VizTracer(log_func_args=True)
        tracer.start()
        fib(5)
        tracer.stop()
        tracer.parse()
        events = [e for e in tracer.data["traceEvents"] if e["ph"] != "M"]
        self.assertTrue("args" in events[0] and "func_args" in events[0]["args"])

    def test_log_gc(self):
        import gc
        tracer = _VizTracer(log_gc=True)
        # do collect first to get rid of the garbage tracer
        gc.collect()
        self.assertTrue(tracer.log_gc)
        tracer.start()
        gc.collect()
        tracer.stop()
        tracer.parse()
        self.assertEventNumber(tracer.data, 3)
        tracer.log_gc = False
        tracer.start()
        gc.collect()
        tracer.stop()
        tracer.parse()
        self.assertEventNumber(tracer.data, 1)

    def test_min_duration(self):
        tracer = _VizTracer(min_duration=100)
        tracer.start()
        a = []
        for _ in range(3):
            a.append(1)
        time.sleep(0.002)
        tracer.stop()
        tracer.parse()
        self.assertEventNumber(tracer.data, 1)
