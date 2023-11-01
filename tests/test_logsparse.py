# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

import functools
import multiprocessing
import os

from .cmdline_tmpl import CmdlineTmpl


file_basic = """
from viztracer import log_sparse

@log_sparse
def f():
    return 1

def g():
    return f()

assert g() == 1
"""


file_stack = """
from viztracer import log_sparse

def h():
    return 1

def f():
    return h()

@log_sparse(stack_depth=2)
def g():
    return f()

assert g() == 1
assert g() == 1
"""


file_stack_nested = """
from viztracer import log_sparse

@log_sparse(stack_depth=2)
def h():
    return 1

def f():
    return h()

@log_sparse(stack_depth=2)
def g():
    return f()

assert g() == 1
assert g() == 1
"""


file_multiprocess = """
from multiprocessing import Process
from viztracer import log_sparse
import time

@log_sparse
def f(x):
    return x*x

if __name__ == "__main__":
    for i in range(3):
        p = Process(target=f, args=(i,))
        p.start()
        p.join()
        time.sleep(0.1)
"""

file_context_manager = """
from viztracer import VizTracer, log_sparse

@log_sparse(dynamic_tracer_check=True)
def f():
    return 1

def g():
    return f()

@log_sparse
def h():
    return 2

@log_sparse(dynamic_tracer_check=True, stack_depth=1)
def q():
    return 3

if __name__ == "__main__":
    with VizTracer(output_file="result.json"):
        assert g() == 1
        assert h() == 2
        assert q() == 3
"""

file_context_manager_logsparse = """
from viztracer import VizTracer, log_sparse

@log_sparse(dynamic_tracer_check=True)
def f():
    return 1

def g():
    return f()

@log_sparse
def h():
    return 2

@log_sparse(dynamic_tracer_check=True, stack_depth=1)
def q():
    return 3

if __name__ == "__main__":
    with VizTracer(output_file="result.json", log_sparse=True):
        assert g() == 1
        assert h() == 2
        assert q() == 3
"""

file_context_manager_logsparse_stack = """
from viztracer import VizTracer, log_sparse

@log_sparse(dynamic_tracer_check=True)
def f():
    return 1

@log_sparse(dynamic_tracer_check=True, stack_depth=1)
def g():
    return f()

@log_sparse(dynamic_tracer_check=True)
def h():
    return 2

if __name__ == "__main__":
    assert g() == 1
    assert h() == 2

    with VizTracer(output_file="result.json", log_sparse=True):
        assert g() == 1
        assert h() == 2
"""


class TestLogSparse(CmdlineTmpl):
    def check_func(self, data, target):
        names = [entry["name"] for entry in data["traceEvents"]]
        function_names = [name.split(' ')[0] for name in names if name not in ['process_name', 'thread_name']]

        self.assertEqual(function_names, target)

    def test_basic(self):
        self.template(["viztracer", "-o", "result.json", "--log_sparse", "cmdline_test.py"],
                      script=file_basic,
                      expected_output_file="result.json",
                      expected_entries=1,
                      check_func=functools.partial(self.check_func, target=['f']))
        self.template(["viztracer", "-o", "result.json", "cmdline_test.py"],
                      script=file_basic,
                      expected_output_file="result.json")

    def test_stack(self):
        self.template(["viztracer", "-o", "result.json", "--log_sparse", "cmdline_test.py"],
                      script=file_stack,
                      expected_output_file="result.json",
                      expected_entries=4,
                      check_func=functools.partial(self.check_func, target=['f', 'g', 'f', 'g']))

        self.template(["viztracer", "-o", "result.json", "--log_sparse", "cmdline_test.py"],
                      script=file_stack_nested,
                      expected_output_file="result.json",
                      expected_entries=4,
                      check_func=functools.partial(self.check_func, target=['f', 'g', 'f', 'g']))

    def test_without_tracer(self):
        self.template(["python", "cmdline_test.py"], script=file_basic, expected_output_file=None)
        self.template(["python", "cmdline_test.py"], script=file_stack, expected_output_file=None)

    def test_multiprocess(self):
        if multiprocessing.get_start_method() == "fork":
            try:
                self.template(["viztracer", "-o", "result.json", "--log_sparse", "cmdline_test.py"],
                              script=file_multiprocess,
                              expected_output_file="result.json",
                              expected_entries=3,
                              check_func=functools.partial(self.check_func, target=['f', 'f', 'f']),
                              concurrency="multiprocessing")
            except Exception as e:
                # coveragepy has some issue with multiprocess pool
                if not os.getenv("COVERAGE_RUN"):
                    raise e

    def test_context_manager(self):
        self.template(["python", "cmdline_test.py"], script=file_context_manager,
                      expected_output_file="result.json", expected_entries=4,
                      check_func=functools.partial(self.check_func, target=['f', 'g', 'h', 'q']))

        self.template(["python", "cmdline_test.py"], script=file_context_manager_logsparse,
                      expected_output_file="result.json", expected_entries=2,
                      check_func=functools.partial(self.check_func, target=['f', 'q']))

        self.template(["python", "cmdline_test.py"], script=file_context_manager_logsparse_stack,
                      expected_output_file="result.json", expected_entries=2,
                      check_func=functools.partial(self.check_func, target=['g', 'h']))
