# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

import os
import sys
import multiprocessing
import unittest
from .cmdline_tmpl import CmdlineTmpl


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
    print("parent")
else:
    time.sleep(0.2)
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
from multiprocessing import Process, Pool
import os
import time

def f(x):
    return x*x

if __name__ == "__main__":
    process_num = 2
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

        if sys.platform in ["linux", "linux2"]:
            self.template(["viztracer", "-o", "result.json", "cmdline_test.py"],
                          expected_output_file="result.json", script=file_fork_wait, check_func=check_func)

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

    def test_ignore_multiprosessing(self):
        def check_func(data):
            pids = set()
            for entry in data["traceEvents"]:
                pids.add(entry["pid"])
            self.assertEqual(len(pids), 1)

        self.template(["viztracer", "-o", "result.json", "--ignore_multiproces", "cmdline_test.py"],
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

        self.template(["viztracer", "-o", "result.json", "cmdline_test.py"],
                      expected_output_file="result.json",
                      script=file_pool,
                      check_func=check_func,
                      concurrency="multiprocessing")

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
