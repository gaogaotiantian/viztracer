# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt


from .cmdline_tmpl import CmdlineTmpl
import os
import shutil
import re


file_spawn = """
import multiprocessing
import io
import os
from multiprocessing.spawn import reduction, spawn_main
from multiprocessing.context import set_spawning_popen
import sys
from viztracer.patch import patch_spawned_process


def foo():
    return 0


process = multiprocessing.Process(target=foo)
fp = io.BytesIO()
set_spawning_popen(process._Popen)
reduction.dump({}, fp)
reduction.dump(process, fp)
set_spawning_popen(None)
child_r, parent_w = os.pipe()

patch_spawned_process({}, "./test_spawn")
pid = os.getpid()

argv = sys.argv
sys.argv = ["python", "--multiprocessing-fork"]

with open(parent_w, 'wb', closefd=False) as f:
    f.write(fp.getbuffer())

spawn_main(pipe_handle=child_r)
"""


class TestPatchSpawn(CmdlineTmpl):
    def test_patch_cmdline(self):
        self.template(["python", "cmdline_test.py"], expected_output_file=None, script=file_spawn)

        files = os.listdir("./test_spawn")
        self.assertEqual(len(files), 1)
        self.assertTrue(re.match(r"result_[0-9]*\.json", files[0]))
        shutil.rmtree("./test_spawn")
