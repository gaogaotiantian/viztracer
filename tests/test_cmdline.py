# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

import os
import sys
import platform
import re
from .cmdline_tmpl import CmdlineTmpl


file_c_function = """
lst = []
lst.append(1)
"""


file_main = """
if __name__ == '__main__':
    lst = []
    lst.append(1)
"""


file_argv = """
import sys
assert(sys.argv)
"""


file_gc = """
import gc
lst = []
gc.collect()
"""


file_exit = """
lst = []
lst.append(1)
exit(0)
"""


file_log_var = """
class Stub:
    def __init__(self):
        self.b = 0

def f1(a, *a2, a3, **a4):
    return None

for a_in_for in [1,2]:
    pass

(a): int = 1
a = [1, 2]
abc = 1
a[1] = 0
a[1] += 1
a = Stub()
a.b = 1
abc = 2
abc += 1
abc: int = 1
a, abc = (1, 2)
unrelated, *a = 1, 2, 3
[abc, d] = 3, 4
f1(2, 3, a3=4, test=5)
"""


file_log_attr = """
class Stub:
    def __init__(self):
        self.a = 0
        self.b = 0
        self.c = 0
        self.alst = [1,2,3]

s = Stub()
s.a = [1, 2]
s.alst[1] = 0
lst = [s, 2]
lst[0].a = 1
s.b += 1
a, abc = (1, 2)
unrelated, *s.a = 1, 2, 3
[abc, d] = 3, 4
"""


file_log_func_exec = """
def a():
    n = 2
    n += 3

def aba():
    __viz_tracer__.add_func_args("place", "holder")
    n2 = 3
    n2 += 5

def b():
    t = 0

a()
aba()
b()
"""


file_log_exception = """
try:
    raise Exception("lol")
except Exception:
    pass
"""


file_ignore_function = """
from viztracer import ignore_function

@ignore_function
def f():
    return 1

def g():
    return f()

g()
"""


file_log_async = """
import asyncio

async def compute(x, y):
    await asyncio.sleep(0.03)
    return x + y

async def print_sum(x, y):
    t1 =  asyncio.create_task(compute(x, y))
    t2 = asyncio.create_task( compute(x+1, y) )

    await t1
    await t2

loop = asyncio.get_event_loop()
loop.run_until_complete(print_sum(1, 2))
loop.close()
"""


class TestCommandLineBasic(CmdlineTmpl):
    def test_no_file(self):
        result = self.template(["python", "-m", "viztracer"], expected_output_file=None)
        self.assertIn("help", result.stdout.decode("utf8"))

    def test_run(self):
        self.template(["python", "-m", "viztracer", "cmdline_test.py"])
        self.template(["viztracer", "cmdline_test.py"])

    def test_cmd_string(self):
        self.template(["viztracer", "-c", "lst=[]; lst.append(1)"], expected_entries=3)

    def test_outputfile(self):
        self.template(["python", "-m", "viztracer", "-o", "result.html", "cmdline_test.py"],
                      expected_output_file="result.html")
        self.template(["python", "-m", "viztracer", "-o", "result.json", "cmdline_test.py"])
        self.template(["python", "-m", "viztracer", "-o", "result.json.gz", "cmdline_test.py"],
                      expected_output_file="result.json.gz")
        self.template(["python", "-m", "viztracer", "--output_file", "result.html", "cmdline_test.py"],
                      expected_output_file="result.html")
        self.template(["python", "-m", "viztracer", "--output_file", "result.json", "cmdline_test.py"],
                      expected_output_file="result.json")
        self.template(["python", "-m", "viztracer", "--output_file", "result.json.gz", "cmdline_test.py"],
                      expected_output_file="result.json.gz")
        self.template(["viztracer", "-o", "result.html", "cmdline_test.py"], expected_output_file="result.html")
        self.template(["viztracer", "-o", "result.json", "cmdline_test.py"], expected_output_file="result.json")
        self.template(["viztracer", "-o", "result.json.gz", "cmdline_test.py"], expected_output_file="result.json.gz")

    def test_verbose(self):
        result = self.template(["python", "-m", "viztracer", "cmdline_test.py"])
        self.assertTrue("Use the following command" in result.stdout.decode("utf8"))
        result = self.template(["python", "-m", "viztracer", "--quiet", "cmdline_test.py"])
        self.assertFalse("Use the following command" in result.stdout.decode("utf8"))

    def test_max_stack_depth(self):
        self.template(["python", "-m", "viztracer", "--max_stack_depth", "5", "cmdline_test.py"])
        self.template(["viztracer", "--max_stack_depth", "5", "cmdline_test.py"])

    def test_include_files(self):
        result = self.template(["python", "-m", "viztracer", "--include_files", "./abcd", "cmdline_test.py"],
                               expected_output_file=None)
        self.assertIn("help", result.stdout.decode("utf8"))
        self.template(["python", "-m", "viztracer", "-o", "result.json", "--include_files", "./", "--run", "cmdline_test.py"],
                      expected_output_file="result.json", expected_entries=17)
        self.template(["python", "-m", "viztracer", "-o", "result.json", "--include_files", "./", "--", "cmdline_test.py"],
                      expected_output_file="result.json", expected_entries=17)
        self.template(["python", "-m", "viztracer", "--include_files", "./", "--max_stack_depth", "5", "cmdline_test.py"])
        self.template(["python", "-m", "viztracer", "--include_files", "./abcd", "--run", "cmdline_test.py"])

    def test_exclude_files(self):
        result = self.template(["python", "-m", "viztracer", "--exclude_files", "./abcd", "cmdline_test.py"],
                               expected_output_file=None)
        self.assertIn("help", result.stdout.decode("utf8"))
        self.template(["python", "-m", "viztracer", "--exclude_files", "./", "-o", "result.json", "cmdline_test.py"],
                      expected_output_file="result.json", expected_entries=1)
        self.template(["python", "-m", "viztracer", "--exclude_files", "./abcd", "--run", "cmdline_test.py"])
        self.template(["python", "-m", "viztracer", "--exclude_files", "./abcd", "--", "cmdline_test.py"])

    def test_ignore_c_function(self):
        self.template(["python", "-m", "viztracer", "--ignore_c_function", "cmdline_test.py"], script=file_c_function)

    def test_log_func_retval(self):
        self.template(["python", "-m", "viztracer", "--log_func_retval", "cmdline_test.py"], script=file_c_function)

    def test_vdb(self):
        self.template(["python", "-m", "viztracer", "--vdb", "cmdline_test.py"])

    def test_log_func_args(self):
        self.template(["python", "-m", "viztracer", "--log_func_args", "cmdline_test.py"])

    def test_minimize_memory(self):
        self.template(["python", "-m", "viztracer", "--minimize_memory", "cmdline_test.py"])

    def test_combine(self):
        example_json_dir = os.path.join(os.path.dirname(__file__), "../", "example/json")
        self.template(["python", "-m", "viztracer", "--combine",
                       os.path.join(example_json_dir, "multithread.json"),
                       os.path.join(example_json_dir, "different_sorts.json")],
                      expected_output_file="result.json")
        self.template(["python", "-m", "viztracer", "-o", "my_result.html", "--combine",
                       os.path.join(example_json_dir, "multithread.json"),
                       os.path.join(example_json_dir, "different_sorts.json")],
                      expected_output_file="my_result.html")
        self.template(["python", "-m", "viztracer", "--align_combine",
                       os.path.join(example_json_dir, "multithread.json"),
                       os.path.join(example_json_dir, "different_sorts.json")],
                      expected_output_file="result.json")

    def test_tracer_entries(self):
        self.template(["python", "-m", "viztracer", "--tracer_entries", "1000", "cmdline_test.py"])
        self.template(["python", "-m", "viztracer", "--tracer_entries", "50", "cmdline_test.py"])

    def test_trace_self(self):
        def check_func(data):
            self.assertGreater(len(data["traceEvents"]), 10000)

        example_json_dir = os.path.join(os.path.dirname(__file__), "../", "example/json")
        self.template(["viztracer", "--trace_self", "vizviewer", "--flamegraph", "--server_only",
                       os.path.join(example_json_dir, "multithread.json")],
                      send_term=True, expected_output_file="result.json", check_func=check_func)

    def test_min_duration(self):
        self.template(["python", "-m", "viztracer", "--min_duration", "1s", "cmdline_test.py"], expected_entries=0)
        self.template(["python", "-m", "viztracer", "--min_duration", "0.0.3s", "cmdline_test.py"], success=False)

    def test_pid_suffix(self):
        self.template(["python", "-m", "viztracer", "--pid_suffix", "--output_dir", "./suffix_tmp", "cmdline_test.py"],
                      expected_output_file="./suffix_tmp")

    def test_path_finding(self):
        if sys.platform in ["linux", "linux2", "darwin"]:
            # path finding only works on Unix
            self.template(["viztracer", "vdb"], success=False)

    def test_module(self):
        self.template(["viztracer", "-m", "numbers"])

    def test_log_gc(self):
        self.template(["viztracer", "--log_gc", "cmdline_test.py"], script=file_gc)

    def test_log_var(self):
        self.template(["viztracer", "--log_var", "lst", "-o", "result.json", "cmdline_test.py"],
                      script=file_c_function,
                      expected_output_file="result.json",
                      expected_entries=4)
        self.template(["viztracer", "--log_var", "a.*", "-o", "result.json", "cmdline_test.py"],
                      script=file_log_var,
                      expected_output_file="result.json",
                      expected_entries=26)
        self.template(["viztracer", "--log_number", "ab[cd]", "-o", "result.json", "cmdline_test.py"],
                      script=file_log_var,
                      expected_output_file="result.json",
                      expected_entries=12)

    def test_log_attr(self):
        self.template(["viztracer", "--log_attr", "a.*", "-o", "result.json", "cmdline_test.py"],
                      script=file_log_attr,
                      expected_output_file="result.json",
                      expected_entries=9)

    def test_log_func_exec(self):
        def check_func(data):
            for entry in data["traceEvents"]:
                if entry["name"].startswith("a"):
                    self.assertIn("exec_steps", entry["args"])
                    self.assertEqual(len(entry["args"]["exec_steps"]), 2)
        self.template(["viztracer", "--log_func_exec", "a.*", "-o", "result.json", "cmdline_test.py"],
                      script=file_log_func_exec,
                      expected_output_file="result.json",
                      check_func=check_func)

    def test_log_func_entry(self):
        self.template(["viztracer", "--log_func_entry", "a.*", "-o", "result.json", "cmdline_test.py"],
                      script=file_log_func_exec,
                      expected_output_file="result.json",
                      expected_entries=7)

    def test_log_exception(self):
        self.template(["viztracer", "--log_exception", "-o", "result.json", "cmdline_test.py"],
                      script=file_log_exception,
                      expected_output_file="result.json",
                      expected_entries=3)
        # Coverage for visit_Raise without change
        self.template(["viztracer", "--log_var", "a", "-o", "result.json", "cmdline_test.py"],
                      script=file_log_exception,
                      expected_output_file="result.json",
                      expected_entries=2)

    def test_log_async(self):
        def check_func(data):
            tids = set()
            for entry in data["traceEvents"]:
                tids.add(entry["tid"])
            self.assertGreaterEqual(len(tids), 4)

        if int(platform.python_version_tuple()[1]) >= 7:
            self.template(["viztracer", "--log_async", "-o", "result.json", "cmdline_test.py"],
                          script=file_log_async,
                          expected_output_file="result.json",
                          check_func=check_func)
        else:
            self.template(["viztracer", "--log_async", "-o", "result.json", "cmdline_test.py"],
                          script=file_log_async,
                          expected_output_file="result.json",
                          success=False)

    def test_ignore_function(self):
        def check_func(data):
            for entry in data["traceEvents"]:
                self.assertNotEqual(entry["name"], "f")
        self.template(["viztracer", "-o", "result.json", "cmdline_test.py"],
                      script=file_ignore_function,
                      expected_output_file="result.json",
                      check_func=check_func)

    def test_show_version(self):
        result = self.template(["viztracer", "--version"], script=None, expected_output_file=None)
        m = re.match(r".*\..*\..*", result.stdout.decode("utf-8").strip())
        self.assertNotEqual(m, None)

    def test_invalid_file(self):
        self.template(["viztracer", "no_such_file.py"], success=False, expected_output_file=[])


class TestPossibleFailures(CmdlineTmpl):
    def test_main(self):
        self.template(["python", "-m", "viztracer", "-o", "main.json", "cmdline_test.py"],
                      expected_output_file="main.json",
                      script=file_main,
                      expected_entries=3)

    def test_argv(self):
        self.template(["python", "-m", "viztracer", "cmdline_test.py"], script=file_argv)

    def test_exit(self):
        self.template(["python", "-m", "viztracer", "cmdline_test.py"], script=file_exit)
