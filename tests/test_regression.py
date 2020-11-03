# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

import unittest
import viztracer
import subprocess
import os
import time
import sys
import platform
from viztracer import VizTracer
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
        tracer.generate_json()

        tracer = viztracer.VizTracer()
        tracer.start()
        from datetime import timedelta
        timedelta(hours=5)
        tracer.stop()
        tracer.parse()
        tracer.generate_json()


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
            tracer.add_functionarg("input", n)
            if n < 2:
                return 1
            return f(n-1) + f(n-2)
        tracer = VizTracer()
        tracer.start()
        f(5)
        tracer.stop()
        tracer.parse()
        inputs = set()
        for d in tracer.data["traceEvents"]:
            inputs.add(d["args"]["input"])
        self.assertEqual(inputs, set([0, 1, 2, 3, 4, 5]))


issue21_code = \
"""
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
        self.template(["viztracer", "--include_files", "/", "--run", "cmdline_test.py", "--script_option"], script=issue21_code)
        self.template(["viztracer", "--include_files", "/", "--", "cmdline_test.py", "--script_option"], script=issue21_code)
        self.template(["viztracer", "cmdline_test.py", "--script_option"], script=issue21_code)
        self.template(["viztracer", "--run", "cmdline_test.py", "-o", "--script_option"], script=issue21_code)
        self.template(["viztracer", "--", "cmdline_test.py", "-o", "--script_option"], script=issue21_code)
        self.template(["viztracer", "--run"], script=issue21_code, success=False, expected_output_file=None)
        self.template(["viztracer", "--"], script=issue21_code, success=False, expected_output_file=None)


term_code = \
"""
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
            if "linux" in sys.platform and int(platform.python_version_tuple()[1]) >= 8:
                # I could not reproduce the stuck failure locally. This is only for
                # coverage anyway, just skip it on 3.8+
                return
            cmd = ["coverage", "run", "--parallel-mode", "--pylib", "-m"] + cmd
        p = subprocess.Popen(cmd)
        time.sleep(0.5)
        p.terminate()
        p.wait(timeout=10)
        self.assertTrue(os.path.exists("term.json"))
        self.cleanup(output_file="term.json")
