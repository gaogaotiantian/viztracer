# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/codesnap/blob/master/NOTICE.txt

import unittest
from codesnap import CodeSnapTracer


class TestTracer(unittest.TestCase):
    def test_double_parse(self):
        def fib(n):
            if n <= 1:
                return 1
            return fib(n-1) + fib(n-2)
        tracer = CodeSnapTracer()
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
        def fib(n):
            if n <= 1:
                return 1
            return fib(n-1) + fib(n-2)
        tracer = CodeSnapTracer(tracer="c")
        tracer.start()
        fib(5)
        tracer.stop()
        tracer.parse()
        with open("result.html", "w") as f:
            f.write(tracer.generate_report())

    def test_c_run_after_clear(self):
        def fib(n):
            if n <= 1:
                return 1
            return fib(n-1) + fib(n-2)
        tracer = CodeSnapTracer(tracer="c")
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
        def fib(n):
            if n <= 1:
                return 1
            return fib(n-1) + fib(n-2)
        tracer = CodeSnapTracer(tracer="c")
        tracer.start()
        fib(5)
        tracer.stop()
        tracer.cleanup()
        tracer.clear()
        tracer.cleanup()
