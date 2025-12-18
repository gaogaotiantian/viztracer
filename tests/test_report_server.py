# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt


import os
import tempfile

from viztracer.report_server import ReportServer

from .base_tmpl import BaseTmpl


class TestReportServer(BaseTmpl):
    def test_before_start(self):
        with tempfile.NamedTemporaryFile() as tmpfile:
            rs = ReportServer(output_file=tmpfile.name)
            rs.clear()
            with self.assertRaises(RuntimeError):
                _ = rs.endpoint

            with self.assertRaises(RuntimeError):
                rs.collect()

    def test_remove_output_dir(self):
        with tempfile.NamedTemporaryFile() as tmpfile:
            rs = ReportServer(output_file=tmpfile.name)
            rs.start()
            report_dir = rs.report_directory
            self.assertTrue(os.path.exists(report_dir))
            rs.clear()
            self.assertFalse(os.path.exists(report_dir))
            # Make sure double clear() is safe
            rs.clear()

            with self.assertRaises(RuntimeError):
                rs.start()
