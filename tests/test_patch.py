# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt


import os
import re
import shutil
import signal
import sys
import tempfile
import unittest
from string import Template

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

patch_spawned_process({'output_file': "$tmpdir/result.json", 'pid_suffix': True}, [])
pid = os.getpid()

assert multiprocessing.spawn._main.__qualname__ == "_main"
assert multiprocessing.spawn._main.__module__ == "multiprocessing.spawn"

argv = sys.argv
sys.argv = ["python", "--multiprocessing-fork"]

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

with open("check_output_echo.py", "w") as f:
    f.write("import sys; print(sys.argv)")

print(subprocess.check_output(["python", "--version"], text=True).strip())
print(subprocess.check_output(["python", "-cprint(5)"]))
print(subprocess.check_output(["python", "check_output_echo.py"], text=True))
print(subprocess.check_output(["python", "-v", "--", "check_output_echo.py", "-a", "42"]))
print(subprocess.check_output(["python", "-Es", "check_output_echo.py", "-v", "--my_arg=foo bar"], text=True))
print(subprocess.check_output(["python", "-Esm", "check_output_echo", "-abc"]))
print(subprocess.check_output(["python", "-c", r"import sys; sys.stdout.buffer.write(b'\0\1\2\3\4')"]))
print(subprocess.check_output(["python", "-", "foo"], input=b"import sys; print(sys.argv)"))
print(subprocess.check_output(["python"], input=b"import sys; print(sys.argv)"))
print(subprocess.check_output(["python", "-im", "check_output_echo", "asdf"], input=b"import sys; print(sys.argv)"))
print(subprocess.check_output(["python", "check_output_echo.py", "test.py", "--output_dir", "test", "--other", "abc"]))
print(subprocess.check_output(["python", "-m", "check_output_echo", "test.py", "--output_dir", "test", "--other", "abc"]))

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
        tmpdir = tempfile.mkdtemp()
        self.template(["python", "cmdline_test.py"],
                      expected_output_file=None,
                      script=file_spawn_tmpl.substitute(foo=foo_normal, tmpdir=tmpdir))

        files = os.listdir(tmpdir)
        self.assertEqual(len(files), 1)
        self.assertTrue(re.match(r"result_[0-9]*\.json", files[0]))
        shutil.rmtree(tmpdir)

    @unittest.skipIf(sys.platform == "win32", "pipe is different on windows so skip it")
    def test_patch_terminate(self):
        tmpdir = tempfile.mkdtemp()
        self.template(["python", "cmdline_test.py"],
                      expected_output_file=None,
                      script=file_spawn_tmpl.substitute(foo=foo_infinite, tmpdir=tmpdir),
                      send_sig=(signal.SIGTERM, "ready"))

        files = os.listdir(tmpdir)
        self.assertEqual(len(files), 1)
        self.assertTrue(re.match(r"result_[0-9]*\.json", files[0]))
        shutil.rmtree(tmpdir)

    def test_patch_args(self):
        a = self.template(["python", "cmdline_test.py"],
                          expected_output_file=None,
                          script=check_output)
        b = self.template(["viztracer", "--quiet", "cmdline_test.py"],
                          expected_output_file="result.json",
                          script=check_output)
        self.assertEqual(a.stdout, b.stdout)


class TestPatchSideEffect(CmdlineTmpl):
    def test_func_names(self):
        self.template(["viztracer", "cmdline_test.py"],
                      expected_output_file="result.json",
                      script=file_after_patch_check)
