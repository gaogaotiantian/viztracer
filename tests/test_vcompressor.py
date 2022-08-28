# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt


import os
import tempfile

from .cmdline_tmpl import CmdlineTmpl
from .util import get_json_file_path


class TestVCompressor(CmdlineTmpl):
    def test_basic(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cvf_path = os.path.join(tmpdir, "result.cvf")
            dup_json_path = os.path.join(tmpdir, "result.json")
            self.template(
                ["viztracer", "-o", cvf_path, "--compress", get_json_file_path("multithread.json")],
                expected_output_file=cvf_path, cleanup=False
            )

            self.template(
                ["viztracer", "-o", dup_json_path, "--decompress", cvf_path],
                expected_output_file=dup_json_path
            )
