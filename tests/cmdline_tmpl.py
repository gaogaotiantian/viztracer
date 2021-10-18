# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

import json
import os
import shutil
import subprocess
import sys
import time
from .base_tmpl import BaseTmpl


file_fib = """
def fib(n):
    if n < 2:
        return 1
    return fib(n-1) + fib(n-2)
fib(5)
"""


class CmdlineTmpl(BaseTmpl):
    def build_script(self, script, name="cmdline_test.py"):
        with open(name, "w") as f:
            f.write(script)

    def cleanup(self, output_file="result.json", script_name="cmdline_test.py"):
        if os.path.exists(script_name):
            os.remove(script_name)
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
                 expected_output_file="result.json",
                 success=True,
                 script=file_fib,
                 script_name="cmdline_test.py",
                 expected_entries=None,
                 expected_stdout=None,
                 cleanup=True,
                 check_func=None,
                 concurrency=None,
                 send_term=False):
        if os.getenv("COVERAGE_RUN"):
            if "viztracer" in cmd_list:
                idx = cmd_list.index("viztracer")
                if not concurrency:
                    cmd_list = ["coverage", "run", "--source", "viztracer", "--parallel-mode", "-m"] \
                        + cmd_list[idx:]
                elif concurrency == "multiprocessing":
                    # Specification needs to be in config file
                    cmd_list = ["coverage", "run", "--concurrency=multiprocessing", "-m"] \
                        + cmd_list[idx:]
            elif "vizviewer" in cmd_list:
                idx = cmd_list.index("vizviewer")
                cmd_list = ["coverage", "run", "--source", "viztracer", "--parallel-mode", "-m"] + ["viztracer.viewer"] \
                    + cmd_list[idx + 1:]
            elif "python" in cmd_list:
                idx = cmd_list.index("python")
                cmd_list = ["coverage", "run", "--source", "viztracer", "--parallel-mode"] \
                    + cmd_list[idx + 1:]

        if script:
            self.build_script(script, script_name)
        if send_term:
            p = subprocess.Popen(cmd_list)
            time.sleep(2)
            p.terminate()
            p.wait()
            result = p
            if sys.platform == "win32":
                # If we are on win32, we can't get anything useful from
                # terminating the process
                return None
        else:
            result = subprocess.run(cmd_list, stdout=subprocess.PIPE, timeout=30)
        if not (success ^ (result.returncode != 0)):
            print(success, result.returncode)
            print(result.stdout)
        self.assertTrue(success ^ (result.returncode != 0))
        if success:
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
                    self.assertEventNumber(data, expected_entries)

            if expected_stdout:
                self.assertRegex(result.stdout.decode("utf-8"), expected_stdout)

            if check_func:
                assert(type(expected_output_file) is str and expected_output_file.split(".")[-1] == "json")
                with open(expected_output_file) as f:
                    data = json.load(f)
                    check_func(data)

        if cleanup:
            self.cleanup(output_file=expected_output_file, script_name=script_name)
        return result
