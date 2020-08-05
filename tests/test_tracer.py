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