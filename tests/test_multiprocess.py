# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt


import os
import sys
import multiprocessing
from .cmdline_tmpl import CmdlineTmpl


file_parent = \
"""
import subprocess
subprocess.run(["python", "child.py"])
"""


file_child = \
"""
def fib(n):
    if n < 2:
        return 1
    return fib(n-1) + fib(n-2)
fib(5)
"""

file_fork = \
"""
import os
import time

pid = os.fork()

if pid > 0:
    time.sleep(0.1)
    print("parent")
else:
    print("child")
"""

file_multiprocessing = \
"""
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
            self.assertGreater(len(pids), 1)
        self.template(["viztracer", "--log_subprocess", "-o", "result.json", "cmdline_test.py"], expected_output_file="result.json", script=file_parent, check_func=check_func)


class TestMultiprocessing(CmdlineTmpl):
    def test_os_fork(self):
        def check_func(data):
            pids = set()
            for entry in data["traceEvents"]:
                pids.add(entry["pid"])
            self.assertGreater(len(pids), 1)
        if sys.platform in ["linux", "linux2"]:
            self.template(["viztracer", "--log_multiprocess", "-o", "result.json", "cmdline_test.py"], expected_output_file="result.json", script=file_fork, check_func=check_func)

    def test_multiprosessing(self):
        def check_func(data):
            pids = set()
            for entry in data["traceEvents"]:
                pids.add(entry["pid"])
            self.assertGreater(len(pids), 1)
        
        if multiprocessing.get_start_method() == "fork":
            self.template(["viztracer", "--log_multiprocess", "-o", "result.json", "cmdline_test.py"], expected_output_file="result.json", script=file_multiprocessing, check_func=check_func, concurrency="multiprocessing")
        else:
            self.template(["viztracer", "--log_multiprocess", "-o", "result.json", "cmdline_test.py"], script=file_multiprocessing, success=False, expected_output_file=None)
