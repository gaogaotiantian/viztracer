# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

from .cmdline_tmpl import CmdlineTmpl
import multiprocessing


file_basic = """
from viztracer import log_sparse

@log_sparse
def f():
    return 1

def g():
    return f()

g()
"""


file_pool = """
from multiprocessing import Process, Pool
from viztracer import log_sparse
import os
import time

@log_sparse
def f(x):
    return x*x

if __name__ == "__main__":
    process_num = 5
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


class TestLogSparse(CmdlineTmpl):
    def test_basic(self):
        def check_func(data):
            for entry in data["traceEvents"]:
                self.assertNotEqual(entry["name"], "f")

        self.template(["viztracer", "-o", "result.json", "--log_sparse", "cmdline_test.py"],
                      script=file_basic,
                      expected_output_file="result.json",
                      expected_entries=1)
        self.template(["viztracer", "-o", "result.json", "cmdline_test.py"],
                      script=file_basic,
                      expected_output_file="result.json",
                      check_func=check_func)

    def test_without_tracer(self):
        self.template(["python", "cmdline_test.py"], script=file_basic, expected_output_file=None)

    def test_multiprocess(self):
        if multiprocessing.get_start_method() == "fork":
            self.template(["viztracer", "-o", "result.json", "--log_sparse", "cmdline_test.py"],
                          script=file_pool,
                          expected_output_file="result.json",
                          expected_entries=21,
                          concurrency="multiprocessing")
