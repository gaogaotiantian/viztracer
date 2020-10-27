# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt


import os
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
