# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt


import multiprocessing
import os
import subprocess
import sys
import tempfile
import time

import viztracer
from viztracer import VizTracer, ignore_function

from .cmdline_tmpl import CmdlineTmpl
from .base_tmpl import BaseTmpl


class TestIssue1(BaseTmpl):
    def test_datetime(self):
        tracer = viztracer.VizTracer()
        tracer.start()
        from datetime import timedelta
        timedelta(hours=5)
        tracer.stop()
        tracer.parse()
        tracer.save(output_file="tmp.json")

        tracer = viztracer.VizTracer()
        tracer.start()
        from datetime import timedelta
        timedelta(hours=5)
        tracer.stop()
        tracer.parse()
        tracer.save(output_file="tmp.json")
        os.remove("tmp.json")


class TestStackOptimization(BaseTmpl):
    # There's an order issue in tracefunc to skip the FEE log
    # If the stack is empty(stack_top is NULL), and we entered
    # into an ignored function, ignore_stack_depth will increment.
    # However, when its corresponding exit comes, ignore_stack_depth
    # won't be decrement because the function is skipped when
    # stack is empty and it's a return function
    def test_instant(self):
        def s():
            return 0
        tracer = VizTracer()
        tracer.start()
        # This is a library function which will be ignored, but
        # this could trick the system into a ignoring status
        tracer.add_instant("name", {"a": 1})
        s()
        s()
        s()
        tracer.stop()
        entries = tracer.parse()
        tracer.save()
        self.assertEqual(entries, 4)


class TestSegFaultRegression(BaseTmpl):
    # Without parsing, cleanup of C function had caused segfault
    def test_cleanup(self):
        tracer = VizTracer()
        tracer.start()
        _ = len([1, 2, 3])
        _ = sum([2, 3, 4])
        try:
            raise Exception("lol")
        except Exception:
            pass
        tracer.stop()
        tracer.cleanup()


class TestFunctionArg(BaseTmpl):
    def test_functionarg(self):
        def f(n):
            tracer.add_func_args("input", n)
            if n < 2:
                return 1
            return f(n - 1) + f(n - 2)
        tracer = VizTracer()
        tracer.start()
        f(5)
        tracer.stop()
        tracer.parse()
        inputs = set()
        for d in tracer.data["traceEvents"]:
            if d["ph"] == "X":
                inputs.add(d["args"]["input"])
        self.assertEqual(inputs, set([0, 1, 2, 3, 4, 5]))


issue21_code = """
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--script_option", action="store_true")
parser.add_argument("-o", action="store_true")
options = parser.parse_args()
print(options)
if not options.script_option:
    exit(1)
"""


class TestIssue21(CmdlineTmpl):
    # viztracer --run my_script --script_option
    # is not parsed correctly because the program gets confused
    # about --script_option
    def test_issue21(self):
        self.template(["viztracer", "--include_files", "/", "--run", "cmdline_test.py", "--script_option"],
                      script=issue21_code)
        self.template(["viztracer", "--include_files", "/", "--", "cmdline_test.py", "--script_option"],
                      script=issue21_code)
        self.template(["viztracer", "cmdline_test.py", "--script_option"], script=issue21_code)
        self.template(["viztracer", "--run", "cmdline_test.py", "-o", "--script_option"], script=issue21_code)
        self.template(["viztracer", "--", "cmdline_test.py", "-o", "--script_option"], script=issue21_code)
        self.template(["viztracer", "--run"], script=issue21_code, success=False, expected_output_file=None)
        self.template(["viztracer", "--"], script=issue21_code, success=False, expected_output_file=None)


term_code = """
import time
a = []
a.append(1)
for i in range(10):
    time.sleep(1)
"""


class TestTermCaught(CmdlineTmpl):
    def test_term(self):
        if sys.platform == "win32":
            return

        self.build_script(term_code)
        cmd = ["viztracer", "-o", "term.json", "cmdline_test.py"]
        if os.getenv("COVERAGE_RUN"):
            cmd = ["coverage", "run", "--parallel-mode", "--pylib", "-m"] + cmd
        p = subprocess.Popen(cmd)
        time.sleep(1.5)
        p.terminate()
        p.wait(timeout=10)
        self.assertFileExists("term.json", 10)
        self.cleanup(output_file="term.json")


class TestIssue42(BaseTmpl):
    def test_issue42(self):

        @ignore_function
        def f():
            lst = []
            lst.append(1)

        tracer = VizTracer()
        tracer.start()
        f()
        tracer.stop()
        tracer.parse()
        self.assertEventNumber(tracer.data, 0)


issue47_code = """
import sys
import gc
class C:
    def __init__(self):
        self.data = bytearray()

    def change(self):
        b = memoryview(self.data).tobytes()
        self.data += b"123123"
        del self.data[:1]

c = C()
c.change()
"""


class TestIssue47(CmdlineTmpl):
    def test_issue47(self):
        self.template(["viztracer", "cmdline_test.py", "-o", "result.json"],
                      script=issue47_code,
                      expected_output_file="result.json",
                      expected_entries=7)


class TestIssue58(CmdlineTmpl):
    def test_issue58(self):
        if multiprocessing.get_start_method() == "fork":
            self.template(["viztracer", "--log_multiprocess", "-m", "tests.modules.issue58"],
                          expected_output_file="result.json")


class TestIssue83(CmdlineTmpl):
    def test_issue83(self):
        self.template(["viztracer", "--quiet", "-m", "tests.modules.issue83"],
                      expected_stdout="__main__")


issue119_code = """
import os
import tempfile
with tempfile.TemporaryDirectory() as name:
    os.chdir(name)
"""


class TestIssue119(CmdlineTmpl):
    def test_issue119(self):
        with tempfile.TemporaryDirectory() as name:
            filepath = os.path.join(name, "result.json")
            cwd = os.getcwd()
            os.chdir(name)
            try:
                self.template(
                    ["viztracer", "-o", "result.json", "cmdline_test.py"],
                    script=issue119_code,
                    expected_output_file=filepath
                )
            finally:
                os.chdir(cwd)
