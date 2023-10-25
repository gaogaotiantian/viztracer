# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

import multiprocessing
import os
import signal
import sys
import tempfile
import unittest

from .cmdline_tmpl import CmdlineTmpl


file_grandparent = """
import subprocess
subprocess.run(["python", "parent.py"])
"""


file_parent = """
import subprocess
subprocess.run(["python", "child.py"])
subprocess.run(("python", "child.py"))
subprocess.run("python child.py")
"""


file_child = """
def fib(n):
    if n < 2:
        return 1
    return fib(n-1) + fib(n-2)
fib(5)
"""

file_subprocess_term = """
import time
while True:
    time.sleep(0.5)
"""

file_subprocess_module = """
import subprocess
print(subprocess.call(["python", "-m", "timeit", "-n", "100", "'1+1'"]))
"""

file_fork = """
import os
import time

pid = os.fork()

if pid > 0:
    time.sleep(0.1)
    print("parent")
else:
    print("child")
"""

file_fork_wait = """
import os
import time

pid = os.fork()

if pid > 0:
    time.sleep(0.1)
    print("parent")
else:
    time.sleep(4.5)
    print("child")
"""

file_multiprocessing = """
import multiprocessing
from multiprocessing import Process
import time


def fib(n):
    if n < 2:
        return 1
    return fib(n-1) + fib(n-2)

def f():
    fib(5)

if __name__ == "__main__":
    fib(2)
    p = Process(target=f)
    p.start()
    p.join()
    time.sleep(0.1)
"""

file_nested_multiprocessing = """
import multiprocessing
from multiprocessing import Process
import time


def fib(n):
    if n < 2:
        return 1
    return fib(n-1) + fib(n-2)

def f():
    fib(5)

def spawn():
    p = Process(target=f)
    p.start()
    p.join()

if __name__ == "__main__":
    fib(2)
    p = Process(target=spawn)
    p.start()
    p.join()
    time.sleep(0.1)
"""

file_multiprocessing_overload_run = """
import multiprocessing
from multiprocessing import Process
import time


class MyProcess(Process):
    def run(self):
        self.fib(5)

    def fib(self, n):
        if n < 2:
            return 1
        return self.fib(n-1) + self.fib(n-2)

if __name__ == "__main__":
    p = MyProcess()
    p.start()
    p.join()
    time.sleep(0.1)
"""

file_multiprocessing_stack_limit = """
import multiprocessing
from multiprocessing import Process
import time
from viztracer import get_tracer


def fib(n):
    if n < 2:
        return 1
    return fib(n-1) + fib(n-2)

def f():
    fib(5)

def cb(tracer):
    print(tracer)
    tracer.max_stack_depth = 2

if __name__ == "__main__":
    get_tracer().set_afterfork(cb)
    p = Process(target=f)
    p.start()
    p.join()
    time.sleep(0.1)
"""

file_pool = """
import gc
from multiprocessing import Process, Pool
import os
import time

def f(x):
    return x*x

if __name__ == "__main__":
    process_num = 2
    # gc seems to cause SegFault with multithreading
    # Pool creates a couple of thread and it's failing the test
    # https://github.com/python/cpython/issues/101975

    gc.disable()
    with Pool(processes=process_num) as pool:
        print(pool.map(f, range(10)))

        for i in pool.imap_unordered(f, range(10)):
            print(i)

        res = pool.apply_async(f, (20,))      # runs in *only* one process
        print(res.get(timeout=1))             # prints "400"

        res = pool.apply_async(os.getpid, ()) # runs in *only* one process
        print(res.get(timeout=1))             # prints the PID of that process

        multiple_results = [pool.apply_async(os.getpid, ()) for i in range(process_num)]
        print([res.get(timeout=1) for res in multiple_results])
    gc.enable()
"""

file_loky = """
from loky import get_reusable_executor
import time
import random


def my_function(*args):
   duration = random.uniform(0.1, 0.3)
   time.sleep(duration)


e = get_reusable_executor(max_workers=4)
e.map(my_function, range(5))
"""


class TestSubprocess(CmdlineTmpl):
    def setUp(self):
        with open("child.py", "w") as f:
            f.write(file_child)

    def tearDown(self):
        os.remove("child.py")

    def test_basic(self):
        def check_func(data):
            pids = set()
            for entry in data["traceEvents"]:
                pids.add(entry["pid"])
            self.assertEqual(len(pids), 4)
        self.template(["viztracer", "-o", "result.json", "cmdline_test.py"],
                      expected_output_file="result.json", script=file_parent, check_func=check_func)

    def test_child_process(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self.template(["viztracer", "-o", os.path.join(tmpdir, "result.json"), "--subprocess_child", "child.py"],
                          expected_output_file=None)
            self.assertEqual(len(os.listdir(tmpdir)), 1)

    def test_module(self):
        self.template(["viztracer", "-o", "result.json", "cmdline_test.py"],
                      expected_output_file="result.json",
                      expected_stdout=".*100 loops.*",
                      script=file_subprocess_module)

    def test_nested(self):
        def check_func(data):
            pids = set()
            for entry in data["traceEvents"]:
                pids.add(entry["pid"])
            self.assertEqual(len(pids), 5)
        with open("parent.py", "w") as f:
            f.write(file_parent)
        self.template(["viztracer", "-o", "result.json", "cmdline_test.py"],
                      expected_output_file="result.json", script=file_grandparent, check_func=check_func)
        os.remove("parent.py")

    def test_nested_multiproessing(self):
        def check_func(data):
            pids = set()
            for entry in data["traceEvents"]:
                pids.add(entry["pid"])
            self.assertEqual(len(pids), 3)
        with open("parent.py", "w") as f:
            f.write(file_multiprocessing)
        self.template(["viztracer", "-o", "result.json", "cmdline_test.py"],
                      expected_output_file="result.json", script=file_grandparent, check_func=check_func)
        os.remove("parent.py")

    @unittest.skipIf(sys.platform == "win32", "Can't get anything on Windows with SIGTERM")
    def test_term(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self.template(["viztracer", "-o", os.path.join(tmpdir, "result.json"), "--subprocess_child", "cmdline_test.py"],
                          script=file_subprocess_term, expected_output_file=None, send_sig=signal.SIGTERM)
            self.assertEqual(len(os.listdir(tmpdir)), 1)


class TestMultiprocessing(CmdlineTmpl):
    def test_os_fork(self):
        def check_func(data):
            pids = set()
            for entry in data["traceEvents"]:
                pids.add(entry["pid"])
            self.assertGreater(len(pids), 1)

        if sys.platform in ["linux", "linux2"]:
            self.template(["viztracer", "-o", "result.json", "cmdline_test.py"],
                          expected_output_file="result.json", script=file_fork, check_func=check_func)

    @unittest.skipIf(sys.platform not in ["linux", "linux2"], "Only works on Linux")
    def test_os_fork_term(self):
        def check_func_wrapper(process_num):
            def check_func(data):
                pids = set()
                for entry in data["traceEvents"]:
                    pids.add(entry["pid"])
                self.assertEqual(len(pids), process_num)
            return check_func

        result = self.template(["viztracer", "-o", "result.json", "cmdline_test.py"],
                               expected_output_file="result.json", script=file_fork_wait,
                               check_func=check_func_wrapper(2))
        self.assertIn("Wait for child process", result.stdout.decode())

        result = self.template(["viztracer", "-o", "result.json", "cmdline_test.py"],
                               send_sig=(signal.SIGINT, 3.5), expected_output_file="result.json", script=file_fork_wait,
                               check_func=check_func_wrapper(1))

    def test_multiprosessing(self):
        def check_func(data):
            pids = set()
            for entry in data["traceEvents"]:
                pids.add(entry["pid"])
            self.assertGreater(len(pids), 1)

        self.template(["viztracer", "-o", "result.json", "cmdline_test.py"],
                      expected_output_file="result.json",
                      script=file_multiprocessing,
                      check_func=check_func,
                      concurrency="multiprocessing")

    def test_nested_multiprosessing(self):
        def check_func(data):
            pids = set()
            for entry in data["traceEvents"]:
                pids.add(entry["pid"])
            self.assertEqual(len(pids), 3)

        self.template(["viztracer", "-o", "result.json", "cmdline_test.py"],
                      expected_output_file="result.json",
                      script=file_nested_multiprocessing,
                      check_func=check_func,
                      concurrency="multiprocessing")

    def test_multiprocessing_entry_limit(self):
        result = self.template(["viztracer", "-o", "result.json", "--tracer_entries", "10", "cmdline_test.py"],
                               expected_output_file="result.json",
                               script=file_multiprocessing,
                               expected_entries=20,
                               concurrency="multiprocessing")
        self.assertIn("buffer is full", result.stdout.decode())

    def test_ignore_multiprosessing(self):
        def check_func(data):
            pids = set()
            for entry in data["traceEvents"]:
                pids.add(entry["pid"])
            self.assertEqual(len(pids), 1)

        self.template(["viztracer", "-o", "result.json", "--ignore_multiprocess", "cmdline_test.py"],
                      expected_output_file="result.json",
                      script=file_multiprocessing,
                      check_func=check_func,
                      concurrency="multiprocessing")

    def test_multiprocessing_overload(self):
        def check_func(data):
            fib_count = 0
            pids = set()
            for entry in data["traceEvents"]:
                pids.add(entry["pid"])
                fib_count += 1 if "fib" in entry["name"] else 0
            self.assertGreater(len(pids), 1)
            self.assertEqual(fib_count, 15)

        self.template(["viztracer", "-o", "result.json", "cmdline_test.py"],
                      expected_output_file="result.json",
                      script=file_multiprocessing_overload_run,
                      check_func=check_func,
                      concurrency="multiprocessing")

    @unittest.skipIf("win32" in sys.platform, "Does not support Windows")
    def test_multiprocessing_pool(self):
        # I could not reproduce the stuck failure locally. This is only for
        # coverage anyway, just skip it on 3.8+
        def check_func(data):
            pids = set()
            for entry in data["traceEvents"]:
                pids.add(entry["pid"])
            self.assertGreater(len(pids), 1)

        try:
            self.template(["viztracer", "-o", "result.json", "cmdline_test.py"],
                          expected_output_file="result.json",
                          script=file_pool,
                          check_func=check_func,
                          concurrency="multiprocessing")
        except Exception as e:
            # coveragepy has some issue with multiprocess pool
            if not os.getenv("COVERAGE_RUN"):
                raise e

    def test_multiprosessing_stack_depth(self):
        def check_func(data):
            for entry in data["traceEvents"]:
                self.assertNotIn("fib", entry["name"].split())
        if multiprocessing.get_start_method() == "fork":
            self.template(["viztracer", "-o", "result.json", "cmdline_test.py"],
                          expected_output_file="result.json",
                          script=file_multiprocessing_stack_limit,
                          check_func=check_func,
                          concurrency="multiprocessing")


class TestLoky(CmdlineTmpl):
    def test_loky_basic(self):
        def check_func(data):
            pids = set()
            for event in data["traceEvents"]:
                pids.add(event["pid"])
            # main, 4 workers, and a forked main on Linux
            self.assertGreaterEqual(len(pids), 5)
        self.template(["viztracer", "cmdline_test.py"], script=file_loky,
                      check_func=check_func, concurrency="multiprocessing")
