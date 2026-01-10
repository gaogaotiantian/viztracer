# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt


import json
import os
import re
import shutil
import signal
import sys
import tempfile
import unittest
from string import Template

from viztracer.report_server import ReportServer

from .cmdline_tmpl import CmdlineTmpl

file_spawn_tmpl = Template("""
import multiprocessing
import io
import os
from multiprocessing.spawn import reduction, spawn_main
from multiprocessing.context import set_spawning_popen
import sys
from viztracer.patch import patch_spawned_process

$foo

process = multiprocessing.Process(target=foo)
fp = io.BytesIO()
set_spawning_popen(process._Popen)
reduction.dump({}, fp)
reduction.dump(process, fp)
set_spawning_popen(None)
child_r, parent_w = os.pipe()

patch_spawned_process({'report_endpoint': "$report_endpoint", 'pid_suffix': True}, [])
pid = os.getpid()

assert multiprocessing.spawn._main.__qualname__ == "_main"
assert multiprocessing.spawn._main.__module__ == "multiprocessing.spawn"

argv = sys.argv
sys.argv = [sys.executable, "--multiprocessing-fork"]

with open(parent_w, 'wb', closefd=False) as f:
    f.write(fp.getbuffer())

spawn_main(pipe_handle=child_r)
""")


foo_normal = """
def foo():
    return 0
"""


foo_infinite = """
import time
def foo():
    print("ready", flush=True)
    while(True):
        time.sleep(0.5)
"""


check_output = r"""
import os
import subprocess
import sys

with open("check_output_echo.py", "w") as f:
    f.write("import sys; print(sys.argv)")

print("PATCH TEST START")
print(subprocess.check_output([sys.executable, "--version"], text=True).strip())
print(subprocess.check_output([sys.executable, "-cprint(5)"]))
print(subprocess.check_output([sys.executable, "check_output_echo.py"], text=True))
print(subprocess.check_output([sys.executable, "-v", "--", "check_output_echo.py", "-a", "42"]))
print(subprocess.check_output([sys.executable, "-Es", "check_output_echo.py", "-v", "--my_arg=foo bar"], text=True))
print(subprocess.check_output([sys.executable, "-Esm", "check_output_echo", "-abc"]))
print(subprocess.check_output([sys.executable, "-c", r"import sys; sys.stdout.buffer.write(b'\0\1\2\3\4')"]))
print(subprocess.check_output([sys.executable, "-", "foo"], input=b"import sys; print(sys.argv)"))
print(subprocess.check_output([sys.executable], input=b"import sys; print(sys.argv)"))
print(subprocess.check_output([sys.executable, "-im", "check_output_echo", "asdf"], input=b"import sys; print(sys.argv)"))
print(subprocess.check_output([sys.executable, "check_output_echo.py", "test.py", "--output_dir", "test", "--other", "abc"]))
print(subprocess.check_output([sys.executable, "-X", "dev", "check_output_echo.py", "-abc"]))
print(subprocess.check_output([sys.executable, "-m", "viztracer", "check_output_echo.py"]))
print(subprocess.check_output(
    [sys.executable, "-m", "check_output_echo", "test.py", "--output_dir", "test", "--other", "abc"]
))

# Invalid invocations
print("No module named" in subprocess.run([sys.executable, "-m", ""], stdout=subprocess.PIPE, text=True).stdout)
print("usage:" in subprocess.run([sys.executable, "-m"], stdout=subprocess.PIPE, text=True).stdout)
print("Argument expected:" in subprocess.run([sys.executable, "-W"], stdout=subprocess.PIPE, text=True).stdout)
print("PATCH TEST END")

os.remove("check_output_echo.py")
"""


file_after_patch_check = """
import multiprocessing.spawn
import subprocess
assert multiprocessing.spawn.get_command_line.__module__ == "multiprocessing.spawn"
assert multiprocessing.spawn.get_command_line.__qualname__ == "get_command_line"
assert subprocess.Popen.__init__.__qualname__ == "Popen.__init__"
assert subprocess.Popen.__init__.__module__ == "subprocess"
"""


class TestPatchSpawn(CmdlineTmpl):
    @unittest.skipIf(sys.platform == "win32", "pipe is different on windows so skip it")
    def test_patch_cmdline(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            server_proc, endpoint = ReportServer.start_process(
                f"{tmpdir}/result.json"
            )

            self.template(
                [sys.executable, "cmdline_test.py"],
                expected_output_file=None,
                script=file_spawn_tmpl.substitute(foo=foo_normal, report_endpoint=endpoint),
            )

            server_proc.wait(timeout=5)
            server_proc.stdout.close()

            files = os.listdir(tmpdir)
            self.assertEqual(len(files), 1)
            self.assertFileExists(f"{tmpdir}/result.json")

    @unittest.skipIf(sys.platform == "win32", "pipe is different on windows so skip it")
    def test_patch_terminate(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            server_proc, endpoint = ReportServer.start_process(
                f"{tmpdir}/result.json"
            )

            self.template(
                [sys.executable, "cmdline_test.py"],
                expected_output_file=None,
                script=file_spawn_tmpl.substitute(foo=foo_infinite, report_endpoint=endpoint),
                send_sig=(signal.SIGTERM, "ready"),
            )

            server_proc.wait(timeout=5)
            server_proc.stdout.close()

            files = os.listdir(tmpdir)
            self.assertEqual(len(files), 1)
            self.assertFileExists(f"{tmpdir}/result.json")

    def test_patch_args(self):
        a = self.template(
            [sys.executable, "cmdline_test.py"],
            expected_output_file=None,
            script=check_output,
        )
        b = self.template(
            ["viztracer", "--quiet", "cmdline_test.py"],
            expected_output_file="result.json",
            script=check_output,
        )
        a_content = re.search(
            r"PATCH TEST START(.*)PATCH TEST END", a.stdout.decode("utf-8"), re.DOTALL
        ).group(1)

        b_content = re.search(
            r"PATCH TEST START(.*)PATCH TEST END", b.stdout.decode("utf-8"), re.DOTALL
        ).group(1)

        self.assertEqual(a_content, b_content)


class TestPatchOnly(CmdlineTmpl):
    @unittest.skipIf(sys.platform == "win32", "Windows does not have fork")
    def test_patch_only(self):
        script = """
            import os
            pid = os.fork()
            def foo():
                pass
            def bar():
                pass
            if pid > 0:
                foo()
            else:
                bar()
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            server_proc, endpoint = ReportServer.start_process(f"{tmpdir}/result.json")
            self.template(
                [
                    "viztracer",
                    "--patch_only",
                    "--report_endpoint",
                    endpoint,
                    "cmdline_test.py",
                ],
                expected_output_file=None,
                script=script,
            )
            server_proc.wait(timeout=5)
            server_proc.stdout.close()

            self.assertFileExists(f"{tmpdir}/result.json")
            with open(f"{tmpdir}/result.json", "r") as f:
                data = json.load(f)
                self.assertEqual(self.getProcessNumber(data), 1)
                self.assertFunctionNotInEvents(data, "foo")
                self.assertFunctionInEvents(data, "bar")


class TestPatchSideEffect(CmdlineTmpl):
    def test_func_names(self):
        self.template(
            ["viztracer", "cmdline_test.py"],
            expected_output_file="result.json",
            script=file_after_patch_check,
        )
