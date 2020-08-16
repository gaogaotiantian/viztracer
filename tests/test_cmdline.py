import unittest
import subprocess
import os

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


class TestCommandLineBasic(unittest.TestCase):
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
                os.remove(output_file)
            else:
                raise Exception("Unexpected output file argument")

    def template(self, cmd_list, expected_output_file="result.html", success=True, script=file_fib):
        self.build_script(script)
        result = subprocess.run(cmd_list, stdout=subprocess.PIPE)
        self.assertTrue(success ^ (result.returncode != 0))
        if expected_output_file:
            if type(expected_output_file) is list:
                for f in expected_output_file:
                    self.assertTrue(os.path.exists(f))
            elif type(expected_output_file) is str:
                self.assertTrue(os.path.exists(expected_output_file))
        self.cleanup(output_file=expected_output_file)
        return result

    def test_no_file(self):
        result = self.template(["python", "-m", "viztracer"], expected_output_file=None)
        self.assertIn("help", result.stdout.decode("utf8"))

    def test_run(self):
        self.template(["python", "-m", "viztracer", "cmdline_test.py"])

    def test_outputfile(self):
        self.template(["python", "-m", "viztracer", "-o", "result.html", "cmdline_test.py"])
        self.template(["python", "-m", "viztracer", "-o", "result.json", "cmdline_test.py"], expected_output_file="result.json")
        self.template(["python", "-m", "viztracer", "--output_file", "result.html", "cmdline_test.py"])
        self.template(["python", "-m", "viztracer", "--output_file", "result.json", "cmdline_test.py"], expected_output_file="result.json")

    def test_tracer(self):
        self.template(["python", "-m", "viztracer", "--tracer", "c", "cmdline_test.py"])
        self.template(["python", "-m", "viztracer", "--tracer", "python", "cmdline_test.py"])

    def test_verbose(self):
        result = self.template(["python", "-m", "viztracer", "cmdline_test.py"])
        self.assertTrue("Dumping trace data" in result.stdout.decode("utf8"))
        result = self.template(["python", "-m", "viztracer", "--quiet", "cmdline_test.py"])
        self.assertFalse("Dumping trace data" in result.stdout.decode("utf8"))

    def test_max_stack_depth(self):
        self.template(["python", "-m", "viztracer", "--max_stack_depth", "5", "cmdline_test.py"])

    def test_include_files(self):
        result = self.template(["python", "-m", "viztracer", "--include_files", "./abcd", "cmdline_test.py"], expected_output_file=None)
        self.assertIn("help", result.stdout.decode("utf8"))
        self.template(["python", "-m", "viztracer", "--include_files", "./", "--run", "cmdline_test.py"])
        self.template(["python", "-m", "viztracer", "--include_files", "./", "--max_stack_depth", "5", "cmdline_test.py"])
        self.template(["python", "-m", "viztracer", "--include_files", "./abcd", "--run", "cmdline_test.py"])

    def test_exclude_files(self):
        result = self.template(["python", "-m", "viztracer", "--exclude_files", "./abcd", "cmdline_test.py"], expected_output_file=None)
        self.assertIn("help", result.stdout.decode("utf8"))
        self.template(["python", "-m", "viztracer", "--exclude_files", "./", "--run", "cmdline_test.py"])
        self.template(["python", "-m", "viztracer", "--exclude_files", "./abcd", "--run", "cmdline_test.py"])

    def test_ignore_c_function(self):
        self.template(["python", "-m", "viztracer", "--ignore_c_function", "cmdline_test.py"], script=file_c_function)

    def test_flamegraph(self):
        self.template(["python", "-m", "viztracer", "--save_flamegraph", "cmdline_test.py"], expected_output_file=["result.html", "result_flamegraph.html"])