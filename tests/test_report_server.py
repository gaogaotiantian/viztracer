# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt


import os
import sys
import tempfile
import textwrap
import unittest

from viztracer.report_server import ReportServer

from .cmdline_tmpl import CmdlineTmpl


class TestReportServer(CmdlineTmpl):
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

    @unittest.skipIf(sys.platform == "win32", "Windows does not support stdin multiplexing")
    def test_enter_skip(self):
        script = textwrap.dedent("""
            import socket
            import sys
            import os
            from viztracer.report_server import ReportServer

            rs = ReportServer("result.json")
            rs.start()
            host, port, _ = rs.endpoint.split(":")

            with socket.socket() as s1, socket.socket() as s2:
                s1.connect((host, int(port)))
                s2.connect((host, int(port)))

            r_fd, w_fd = os.pipe()
            sys.stdin = os.fdopen(r_fd, "r")
            os.write(w_fd, b"\\n")

            rs.collect()
        """)

        self.template(
            cmd_list=[sys.executable, "cmdline_test.py"],
            script=script,
            expected_output_file=None,
            expected_stdout="Skipped remaining child processes"
        )
