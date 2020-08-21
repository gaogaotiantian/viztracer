# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

import unittest
from viztracer import VizTracer
import time
import threading


def fib(n):
    if n < 2:
        return 1
    time.sleep(0.000001)
    return fib(n-1) + fib(n-2)


class MyThread(threading.Thread):
    def run(self):
        fib(10)


class TestMultithread(unittest.TestCase):
    def test_basic(self):
        tracer = VizTracer(max_stack_depth=4)
        tracer.start()

        thread1 = MyThread()
        thread2 = MyThread()
        thread3 = MyThread()
        thread4 = MyThread()

        thread1.start()
        thread2.start()
        thread3.start()
        thread4.start()

        threads = [thread1, thread2, thread3, thread4]

        for thread in threads:
            thread.join()

        tracer.stop()
        entries = tracer.parse()
        self.assertGreater(entries, 160)
