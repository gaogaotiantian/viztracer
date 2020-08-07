# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/codesnap/blob/master/NOTICE.txt

import unittest
from codesnap import CodeSnapTracer
from codesnap import CodeSnap


class TestTracerBasic(unittest.TestCase):
    def test_construct(self):
        def fib(n):
            if n == 1 or n == 0:
                return 1
            return fib(n-1) + fib(n-2)
        t = CodeSnapTracer()
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
        t = CodeSnapTracer()
        t.start()
        fun(10)
        t.stop()
        entries = t.parse()
        self.assertEqual(entries, 42)


class TestCodeSnapBasic(unittest.TestCase):
    def test_run(self):
        snap = CodeSnap()
        snap.run("import random; random.randrange(10)")
