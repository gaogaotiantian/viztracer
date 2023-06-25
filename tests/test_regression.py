# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt


import multiprocessing
import os
import signal
import sys
import tempfile
import unittest

import viztracer
from viztracer import VizTracer, ignore_function

from .base_tmpl import BaseTmpl
from .cmdline_tmpl import CmdlineTmpl


class TestIssue1(BaseTmpl):
    def test_datetime(self):
        tracer = viztracer.VizTracer(verbose=0)
        tracer.start()
        from datetime import timedelta
        timedelta(hours=5)
        tracer.stop()
        tracer.parse()
        tracer.save(output_file="tmp.json")

        tracer = viztracer.VizTracer(verbose=0)
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
        tracer = VizTracer(verbose=0)
        tracer.start()
        # This is a library function which will be ignored, but
        # this could trick the system into a ignoring status
        tracer.add_instant('name = {"a": 1}')
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
        tracer = VizTracer(verbose=0)
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


term_code = """
import time
a = []
a.append(1)
for i in range(10):
    time.sleep(1)
"""


class TestTermCaught(CmdlineTmpl):
    @unittest.skipIf(sys.platform == "win32", "windows does not have graceful term")
    def test_term(self):
        self.template(["viztracer", "-o", "term.json", "cmdline_test.py"],
                      expected_output_file="term.json", script=term_code, send_sig=signal.SIGTERM)


class TestIssue42(BaseTmpl):
    def test_issue42(self):

        @ignore_function
        def f():
            lst = []
            lst.append(1)

        tracer = VizTracer(verbose=0)
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
            self.template(["viztracer", "-m", "tests.modules.issue58"],
                          expected_output_file="result.json")


class TestIssue83(CmdlineTmpl):
    def test_issue83(self):
        self.template(["viztracer", "--quiet", "-m", "tests.modules.issue83"],
                      expected_stdout="__main__")


issue119_code = """
import os
import sys
import tempfile
os.chdir(sys.argv[1])
"""


class TestIssue119(CmdlineTmpl):
    def test_issue119(self):
        with tempfile.TemporaryDirectory() as name:
            filepath = os.path.join(name, "result.json")
            cwd = os.getcwd()
            os.chdir(name)
            with tempfile.TemporaryDirectory() as script_dir:
                try:
                    self.template(
                        ["viztracer", "-o", "result.json", "cmdline_test.py", script_dir],
                        script=issue119_code,
                        expected_output_file=filepath)
                finally:
                    os.chdir(cwd)


issue121_code = """
import atexit

def fib(n):
    if n <= 2:
        return 1
    return fib(n - 1) + fib(n - 2)

atexit.register(fib, 6)
"""


class TestIssue121(CmdlineTmpl):
    def test_issue121(self):

        def check_func(data):
            fib_count = sum(["fib" in event["name"] for event in data["traceEvents"]])
            self.assertEqual(fib_count, 15)

        self.template(["viztracer", "cmdline_test.py", "--log_exit"],
                      script=issue121_code,
                      check_func=check_func)


issue141_code = """
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor
import time


def my_function(*args):
   time.sleep(0.5)


if __name__ == '__main__':
    e = ProcessPoolExecutor(max_workers=3)
    e.map(my_function, range(1))
"""


class TestIssue141(CmdlineTmpl):
    def test_issue141(self):
        self.template(
            ["viztracer", "cmdline_test.py"],
            script=issue141_code,
        )


class TestIssue160(CmdlineTmpl):
    def test_issue160(self):

        def check_func(data):
            pids = set()
            for entry in data["traceEvents"]:
                pids.add(entry["pid"])
            self.assertEqual(len(pids), 2)

        self.template(["viztracer", "-m", "tests.modules.issue160"],
                      expected_output_file="result.json", check_func=check_func)


issue162_code = """
from concurrent.futures import ProcessPoolExecutor
def work(d):
    return d * 2

if __name__ == "__main__":
    output = 0
    data = range(10)
    with ProcessPoolExecutor(2) as executor:
        for _, data_collected in zip(data, executor.map(work, data)):
            output += data_collected
    print(output)
"""


issue162_code_os_popen = """
import os
print(os.popen("echo test_issue162").read())
"""


class TestIssue162(CmdlineTmpl):
    def test_issue162(self):
        self.template(["viztracer", "cmdline_test.py"], expected_output_file="result.json",
                      script=issue162_code, expected_stdout=r"90\s*Saving.*")

    @unittest.skipIf(sys.platform == "win32", "Windows does not have echo")
    def test_issue162_os_popen(self):
        self.template(["viztracer", "cmdline_test.py"], expected_output_file="result.json",
                      script=issue162_code_os_popen, expected_stdout=r".*test_issue162.*")


file_timestamp_disorder = """
def g():
    pass

g()
g()
g()
g()
g()
g()
g()
g()
g()
g()
g()
"""


class TestTimestampDisorder(CmdlineTmpl):
    def test_timestamp_overlap(self):
        def check_func(data):
            counter = 0
            curr_time = 0
            for event in data["traceEvents"]:
                if event["ph"] == "X" and event["name"].startswith("g"):
                    counter += 1
                    self.assertGreaterEqual(event["ts"], curr_time)
                    self.assertGreater(event["dur"], 0)
                    curr_time = event["ts"] + event["dur"]
        self.template(["viztracer", "cmdline_test.py"], script=file_timestamp_disorder,
                      expected_output_file="result.json", check_func=check_func)


issue285_code = """
import threading
from viztracer import get_tracer, VizCounter, VizObject


def fib(n):
    if n < 2:
        return 1
    return fib(n - 1) + fib(n - 2)


class MyThread(threading.Thread):
    def run(self):
        fib(7)


tracer = get_tracer()

# test object event name escape with and without args
obj = VizObject(tracer, "test \\\\ \\\" \\b \\f \\n \\r \\t")
obj.test = "test \\\\ \\\" \\b \\f \\n \\r \\t"

# test counter event name escape with and without args
counter = VizCounter(tracer, "test \\\\ \\\" \\b \\f \\n \\r \\t")
counter.test = 10

# test instant event name escape with and without args
tracer.log_instant("test \\\\ \\\" \\b \\f \\n \\r \\t")
tracer.log_instant("test \\\\ \\\" \\b \\f \\n \\r \\t", "test \\\\ \\\" \\b \\f \\n \\r \\t")

# test thread name escape
test_thread = MyThread(name = "test \\\\ \\\" \\b \\f \\n \\r \\t")
test_thread.start()
test_thread.join()

"""


class TestEscapeString(CmdlineTmpl):
    def test_escape_string(self):
        self.template(["viztracer", "-o", "result.json", "--dump_raw", "cmdline_test.py"],
                      expected_output_file="result.json",
                      script=issue285_code,
                      expected_stdout=".*Total Entries:.*")
