# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt


import json
import signal
import subprocess
import sys
import tempfile
import textwrap
import unittest

from viztracer import VizTracer
from viztracer.report_server import ReportServer

from .cmdline_tmpl import CmdlineTmpl
from .util import cmd_with_coverage, get_free_port


class TestReportServer(CmdlineTmpl):
    def test_report_server_with_endpoint(self):
        script = textwrap.dedent("""
            def foo():
                pass
            foo()
        """)

        with tempfile.TemporaryDirectory() as tmpdir:
            endpoint = f"127.0.0.1:{get_free_port()}"
            server_proc, actual_endpoint = ReportServer.start_process(
                output_file=f"{tmpdir}/result.json",
                report_endpoint=endpoint,
            )
            self.assertEqual(endpoint, actual_endpoint)

            self.template(
                ["viztracer", "--report_endpoint", endpoint, "cmdline_test.py"],
                script=script,
                expected_output_file=None,
            )
            server_proc.__exit__(None, None, None)

            with open(f"{tmpdir}/result.json") as f:
                data = json.load(f)
                self.assertTrue(
                    any("foo" in event["name"] for event in data["traceEvents"])
                )

    def test_cleared(self):
        server = ReportServer(
            output_file="result.json",
        )

        server.clear()

        with self.assertRaises(RuntimeError):
            server.run()

    @unittest.skipIf(
        sys.platform == "win32",
        "Skip Windows due to subprocess signal handling differences",
    )
    def test_no_data(self):
        cmd = cmd_with_coverage(
            [
                "viztracer",
                "--report_server",
                "-o",
                "result.json",
            ]
        )
        p = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        out, _ = p.communicate("\n")
        self.assertIn("No reports collected, nothing to save.", out)

    @unittest.skipIf(
        sys.platform == "win32",
        "Windows terminate will kill the process without cleanup",
    )
    def test_server_shutdown_before_save(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            server_proc, endpoint = ReportServer.start_process(
                output_file=f"{tmpdir}/result.json",
            )

            tracer = VizTracer(report_endpoint=endpoint, verbose=0)
            tracer.start()
            server_proc.send_signal(signal.SIGINT)
            server_proc.__exit__(None, None, None)
            with self.assertWarns(RuntimeWarning):
                tracer.save()

    def test_invalid_report_server_argument(self):
        for arg in ["invalid_endpoint", "|invalid_config", "127.0.0.1"]:
            cmd = cmd_with_coverage(
                [
                    "viztracer",
                    "--report_server",
                    arg,
                    "-o",
                    "result.json",
                ]
            )
            p = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )

            p.communicate("\n")
            self.assertNotEqual(0, p.returncode)
