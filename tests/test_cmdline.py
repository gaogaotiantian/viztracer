# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

import unittest
import subprocess
import os
import sys
import json
import shutil
from .util import get_json_file_path


file_fib = \
"""
def fib(n):
    if n < 2:
        return 1
    return fib(n-1) + fib(n-2)
fib(5)
"""

file_c_function = \
"""
lst = []
lst.append(1)
"""

file_main = \
"""
if __name__ == '__main__':
    lst = []
    lst.append(1)
"""

file_argv = \
"""
import sys
assert(sys.argv)
"""

file_gc = \
"""
import gc
lst = []
gc.collect()
"""

file_exit = \
"""
lst = []
lst.append(1)
exit(0)
"""


class Tmpl(unittest.TestCase):
    def build_script(self, script):
        with open("cmdline_test.py", "w") as f:
            f.write(script)

    def cleanup(self, output_file="result.html"):
        os.remove("cmdline_test.py")
        if output_file:
            if type(output_file) is list:
                for f in output_file:
                    os.remove(f)
            elif type(output_file) is str:
                if os.path.exists(output_file):
                    if os.path.isdir(output_file):
                        shutil.rmtree(output_file)
                    elif os.path.isfile(output_file):
                        os.remove(output_file)
            else:
                raise Exception("Unexpected output file argument")

    def template(self, 
                 cmd_list, 
                 expected_output_file="result.html", 
                 success=True, 
                 script=file_fib, 
                 expected_entries=None, 
                 cleanup=True):
        if os.getenv("COVERAGE_RUN"):
            idx = cmd_list.index("viztracer")
            cmd_list = ["coverage", "run", "--parallel-mode", "--pylib", "-m"] + cmd_list[idx:]

        self.build_script(script)
        result = subprocess.run(cmd_list, stdout=subprocess.PIPE)
        self.assertTrue(success ^ (result.returncode != 0))
        if expected_output_file:
            if type(expected_output_file) is list:
                for f in expected_output_file:
                    self.assertTrue(os.path.exists(f))
            elif type(expected_output_file) is str:
                self.assertTrue(os.path.exists(expected_output_file))

        if expected_entries:
            assert(type(expected_output_file) is str and expected_output_file.split(".")[-1] == "json")
            with open(expected_output_file) as f:
                data = json.load(f)
                self.assertEqual(len(data["traceEvents"]), expected_entries)

        if cleanup:
            self.cleanup(output_file=expected_output_file)
        return result


class TestCommandLineBasic(Tmpl):
    def test_no_file(self):
        result = self.template(["python", "-m", "viztracer"], expected_output_file=None)
        self.assertIn("help", result.stdout.decode("utf8"))

    def test_run(self):
        self.template(["python", "-m", "viztracer", "cmdline_test.py"])
        self.template(["viztracer", "cmdline_test.py"])

    def test_outputfile(self):
        self.template(["python", "-m", "viztracer", "-o", "result.html", "cmdline_test.py"])
        self.template(["python", "-m", "viztracer", "-o", "result.json", "cmdline_test.py"], expected_output_file="result.json")
        self.template(["python", "-m", "viztracer", "-o", "result.json.gz", "cmdline_test.py"], expected_output_file="result.json.gz")
        self.template(["python", "-m", "viztracer", "--output_file", "result.html", "cmdline_test.py"])
        self.template(["python", "-m", "viztracer", "--output_file", "result.json", "cmdline_test.py"], expected_output_file="result.json")
        self.template(["python", "-m", "viztracer", "--output_file", "result.json.gz", "cmdline_test.py"], expected_output_file="result.json.gz")
        self.template(["viztracer", "-o", "result.html", "cmdline_test.py"])
        self.template(["viztracer", "-o", "result.json", "cmdline_test.py"], expected_output_file="result.json")
        self.template(["viztracer", "-o", "result.json.gz", "cmdline_test.py"], expected_output_file="result.json.gz")

    def test_verbose(self):
        result = self.template(["python", "-m", "viztracer", "cmdline_test.py"])
        self.assertTrue("Dumping trace data" in result.stdout.decode("utf8"))
        result = self.template(["python", "-m", "viztracer", "--quiet", "cmdline_test.py"])
        self.assertFalse("Dumping trace data" in result.stdout.decode("utf8"))

    def test_max_stack_depth(self):
        self.template(["python", "-m", "viztracer", "--max_stack_depth", "5", "cmdline_test.py"])
        self.template(["viztracer", "--max_stack_depth", "5", "cmdline_test.py"])

    def test_include_files(self):
        result = self.template(["python", "-m", "viztracer", "--include_files", "./abcd", "cmdline_test.py"], expected_output_file=None)
        self.assertIn("help", result.stdout.decode("utf8"))
        self.template(["python", "-m", "viztracer", "-o", "result.json", "--include_files", "./", "--run", "cmdline_test.py"], expected_output_file="result.json", expected_entries=17)
        self.template(["python", "-m", "viztracer", "--include_files", "./", "--max_stack_depth", "5", "cmdline_test.py"])
        self.template(["python", "-m", "viztracer", "--include_files", "./abcd", "--run", "cmdline_test.py"])

    def test_exclude_files(self):
        result = self.template(["python", "-m", "viztracer", "--exclude_files", "./abcd", "cmdline_test.py"], expected_output_file=None)
        self.assertIn("help", result.stdout.decode("utf8"))
        self.template(["python", "-m", "viztracer", "--exclude_files", "./", "-o", "result.json", "cmdline_test.py"], expected_output_file="result.json", expected_entries=1)
        self.template(["python", "-m", "viztracer", "--exclude_files", "./abcd", "--run", "cmdline_test.py"])

    def test_ignore_c_function(self):
        self.template(["python", "-m", "viztracer", "--ignore_c_function", "cmdline_test.py"], script=file_c_function)

    def test_log_return_value(self):
        self.template(["python", "-m", "viztracer", "--log_return_value", "cmdline_test.py"], script=file_c_function)

    def test_novdb(self):
        self.template(["python", "-m", "viztracer", "--novdb", "cmdline_test.py"])

    def test_log_function_args(self):
        self.template(["python", "-m", "viztracer", "--log_function_args", "cmdline_test.py"])

    def test_flamegraph(self):
        self.template(["python", "-m", "viztracer", "--save_flamegraph", "cmdline_test.py"], expected_output_file=["result.html", "result_flamegraph.html"])

    def test_combine(self):
        example_json_dir = os.path.join(os.path.dirname(__file__), "../", "example/json")
        self.template(["python", "-m", "viztracer", "--combine", os.path.join(example_json_dir, "multithread.json"),
                os.path.join(example_json_dir, "different_sorts.json")], expected_output_file="result.html")
        self.template(["python", "-m", "viztracer", "-o", "my_result.html", "--combine", os.path.join(example_json_dir, "multithread.json"),
                os.path.join(example_json_dir, "different_sorts.json")], expected_output_file="my_result.html")

    def test_tracer_entries(self):
        self.template(["python", "-m", "viztracer", "--tracer_entries", "1000", "cmdline_test.py"])
        self.template(["python", "-m", "viztracer", "--tracer_entries", "50", "cmdline_test.py"])

    def test_pid_suffix(self):
        self.template(["python", "-m", "viztracer", "--pid_suffix", "--output_dir", "./suffix_tmp", "cmdline_test.py"], expected_output_file="./suffix_tmp")

    def test_path_finding(self):
        if sys.platform in ["linux", "linux2", "darwin"]:
            # path finding only works on Unix
            self.template(["viztracer", "vdb"], success=False)

    def test_generate_flamegraph(self):
        self.template(["viztracer", "--generate_flamegraph", get_json_file_path("multithread.json")], expected_output_file="./result_flamegraph.html")
        self.template(["viztracer", "-o", "result_flamegraph.html", "--generate_flamegraph", get_json_file_path("multithread.json")], expected_output_file="./result_flamegraph.html")

    def test_module(self):
        self.template(["viztracer", "-m", "numbers"])

    def test_log_gc(self):
        self.template(["viztracer", "--log_gc", "cmdline_test.py"], script=file_gc)

    def test_open(self):
        self.template(["viztracer", "--open", "cmdline_test.py"])

    def test_log_var(self):
        self.template(["viztracer", "--log_var", "lst", "-o", "result.json", "cmdline_test.py"], script=file_c_function, expected_output_file="result.json", expected_entries=4)

    def test_invalid_file(self):
        self.template(["viztracer", "no_such_file.py"], success=False, expected_output_file=[])


class TestPossibleFailures(Tmpl):
    def test_main(self):
        self.template(["python", "-m", "viztracer", "-o", "main.json", "cmdline_test.py"], expected_output_file="main.json", script=file_main, expected_entries=3)

    def test_argv(self):
        self.template(["python", "-m", "viztracer", "cmdline_test.py"], script=file_argv)

    def test_exit(self):
        self.template(["python", "-m", "viztracer", "cmdline_test.py"], script=file_exit)
