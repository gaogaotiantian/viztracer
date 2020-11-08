# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

import json
import os
import shutil
import subprocess
import unittest
from .base_tmpl import BaseTmpl


file_fib = \
"""
def fib(n):
    if n < 2:
        return 1
    return fib(n-1) + fib(n-2)
fib(5)
"""


class CmdlineTmpl(BaseTmpl):
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
                 cleanup=True,
                 check_func=None,
                 concurrency=None):
        if os.getenv("COVERAGE_RUN"):
            if "viztracer" in cmd_list:
                idx = cmd_list.index("viztracer")
            elif "python" in cmd_list:
                idx = cmd_list.index("python")
            if not concurrency:
                cmd_list = ["coverage", "run", "--parallel-mode", "--pylib", "-m"] + cmd_list[idx:]
            elif concurrency == "multiprocessing":
                cmd_list = ["coverage", "run", "--concurrency=multiprocessing", "-m"] + cmd_list[idx:]

        self.build_script(script)
        result = subprocess.run(cmd_list, stdout=subprocess.PIPE, timeout=15)
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

        if check_func:
            assert(type(expected_output_file) is str and expected_output_file.split(".")[-1] == "json")
            with open(expected_output_file) as f:
                data = json.load(f)
                check_func(data)

        if cleanup:
            self.cleanup(output_file=expected_output_file)
        return result