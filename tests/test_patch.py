# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt


from .cmdline_tmpl import CmdlineTmpl
import os
import shutil
import re
import sys
import tempfile
import unittest
from string import Template


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

patch_spawned_process({'output_file': "$tmpdir/result.json", 'pid_suffix': True})
pid = os.getpid()

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
    while(True):
        time.sleep(0.5)
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
                      send_term=True)

        files = os.listdir(tmpdir)
        self.assertEqual(len(files), 1)
        self.assertTrue(re.match(r"result_[0-9]*\.json", files[0]))
        shutil.rmtree(tmpdir)
