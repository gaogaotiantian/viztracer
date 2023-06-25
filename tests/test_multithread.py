# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

import threading
import time

from viztracer import VizTracer, get_tracer

from .base_tmpl import BaseTmpl
from .cmdline_tmpl import CmdlineTmpl


def fib(n):
    if n < 2:
        return 1
    time.sleep(0.000001)
    return fib(n - 1) + fib(n - 2)


class MyThread(threading.Thread):
    def run(self):
        fib(10)


class MyThreadTraceAware(threading.Thread):
    def run(self):
        get_tracer().enable_thread_tracing()
        fib(10)


class TestMultithread(BaseTmpl):
    def test_basic(self):
        tracer = VizTracer(max_stack_depth=4, verbose=0)
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
        self.assertGreater(entries, 170)

        metadata = [e for e in tracer.data["traceEvents"] if e["ph"] == "M"]
        self.assertEqual(len([e for e in metadata if e["name"] == "process_name"]), 1)
        self.assertEqual(len([e for e in metadata if e["name"] == "thread_name"]), 5)

    def test_with_small_buffer(self):
        tracer = VizTracer(tracer_entries=300, verbose=0)
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
        self.assertEqual(entries, 300)

    def test_manual_tracefunc(self):
        tracer = VizTracer(max_stack_depth=4, verbose=0)
        # Force disable threading trace
        threading.setprofile(None)
        tracer.start()

        threads = [MyThread() for _ in range(4)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        tracer.stop()
        entries = tracer.parse()
        self.assertLess(entries, 180)

        metadata = [e for e in tracer.data["traceEvents"] if e["ph"] == "M"]
        self.assertEqual(len([e for e in metadata if e["name"] == "process_name"]), 1)
        self.assertEqual(len([e for e in metadata if e["name"] == "thread_name"]), 1)

        tracer.clear()

        tracer.start()

        threads = [MyThreadTraceAware() for _ in range(4)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        tracer.stop()
        entries = tracer.parse()
        self.assertGreater(entries, 180)

        metadata = [e for e in tracer.data["traceEvents"] if e["ph"] == "M"]
        self.assertEqual(len([e for e in metadata if e["name"] == "process_name"]), 1)
        self.assertEqual(len([e for e in metadata if e["name"] == "thread_name"]), 5)


file_log_sparse = """
import threading
from viztracer import log_sparse

class MyThreadSparse(threading.Thread):
    def run(self):
        self.sparse_func()

    @log_sparse
    def sparse_func(self):
        return 0

thread1 = MyThreadSparse()
thread2 = MyThreadSparse()

thread1.start()
thread2.start()

threads = [thread1, thread2]

for thread in threads:
    thread.join()
"""


class TestMultithreadCmdline(CmdlineTmpl):
    def test_with_log_sparse(self):
        self.template(["viztracer", "-o", "result.json", "--log_sparse", "cmdline_test.py"],
                      expected_output_file="result.json",
                      script=file_log_sparse,
                      expected_entries=2)
