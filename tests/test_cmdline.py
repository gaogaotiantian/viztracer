import unittest
import subprocess
import os

file_content = \
"""
def fib(n):
    if n < 2:
        return 1
    return fib(n-1) + fib(n-2)
fib(5)
"""
class TestCommandLineBasic(unittest.TestCase):
    def build_script(self):
        with open("cmdline_test.py", "w") as f:
            f.write(file_content)

    def cleanup(self, output_file="result.html"):
        os.remove("cmdline_test.py")
        os.remove(output_file)

    def template(self, cmd_list, expected_output_file="result.html", success=True):
        self.build_script()
        result = subprocess.run(cmd_list)
        self.assertTrue(success ^ (result.returncode != 0))
        self.assertTrue(os.path.exists(expected_output_file))
        self.cleanup(output_file=expected_output_file)

    def test_run(self):
        self.template(["python", "-m", "codesnap", "cmdline_test.py"])
    
    def test_outputfile(self):
        self.template(["python", "-m", "codesnap", "-o", "result.html", "cmdline_test.py"])
        self.template(["python", "-m", "codesnap", "-o", "result.json", "cmdline_test.py"], expected_output_file="result.json")
        self.template(["python", "-m", "codesnap", "--output_file", "result.html", "cmdline_test.py"])
        self.template(["python", "-m", "codesnap", "--output_file", "result.json", "cmdline_test.py"], expected_output_file="result.json")
    
    def test_tracer(self):
        self.template(["python", "-m", "codesnap", "--tracer", "c", "cmdline_test.py"])
        self.template(["python", "-m", "codesnap", "--tracer", "python", "cmdline_test.py"])