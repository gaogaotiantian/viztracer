# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

import json
import logging
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
                 expected_stderr=None,
                 cleanup=True,
                 check_func=None,
                 concurrency=None,
                 send_sig=None):
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
        if send_sig is not None:
            if isinstance(send_sig, tuple):
                sig, wait = send_sig
            else:
                sig = send_sig
                if os.getenv("GITHUB_ACTIONS"):
                    # github action is slower
                    wait = 5
                else:
                    wait = 2
            p = subprocess.Popen(cmd_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if isinstance(wait, str):
                while True:
                    line = p.stdout.readline().decode("utf-8")
                    if wait in line:
                        time.sleep(0.5)
                        break
            elif isinstance(wait, (int, float)):
                time.sleep(wait)
            p.send_signal(sig)
            p.wait(timeout=60)
            stdout, stderr = p.stdout.read(), p.stderr.read()
            p.stdout.close()
            p.stderr.close()
            p.stdout, p.stderr = stdout, stderr
            result = p
            if sys.platform == "win32":
                # If we are on win32, we can't get anything useful from
                # terminating the process
                return None
        else:
            if os.getenv("COVERAGE_RUN"):
                timeout = 90
            else:
                timeout = 60
            try:
                result = subprocess.run(cmd_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
            except subprocess.TimeoutExpired as e:
                logging.error("Timeout!")
                logging.error(f"stdout: {e.stdout}")
                logging.error(f"stderr: {e.stderr}")
                raise e
        expected = (success ^ (result.returncode != 0))
        if not expected:
            logging.error(f"return code: {result.returncode}")
            logging.error(f"stdout:\n{result.stdout.decode('utf-8')}")
            logging.error(f"stderr:\n{result.stderr.decode('utf-8')}")
        self.assertTrue(expected)
        if expected:
            if success and expected_output_file:
                if type(expected_output_file) is list:
                    for f in expected_output_file:
                        self.assertFileExists(f)
                elif type(expected_output_file) is str:
                    self.assertFileExists(expected_output_file)

            if success and expected_entries:
                assert (type(expected_output_file) is str and expected_output_file.split(".")[-1] == "json")
                with open(expected_output_file) as f:
                    data = json.load(f)
                    self.assertEventNumber(data, expected_entries)

            if expected_stdout is not None:
                self.assertRegex(result.stdout.decode("utf-8"), expected_stdout)

            if expected_stderr is not None:
                self.assertRegex(result.stderr.decode("utf-8"), expected_stderr)

            if check_func:
                assert (type(expected_output_file) is str and expected_output_file.split(".")[-1] == "json")
                with open(expected_output_file) as f:
                    data = json.load(f)
                    check_func(data)

        if cleanup:
            self.cleanup(output_file=expected_output_file, script_name=script_name)
        return result
