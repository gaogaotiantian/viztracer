# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt


import json
import os
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

    def test_report_server_env_variable(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            report_server_cmd = cmd_with_coverage(
                [
                    "viztracer",
                    "--report_server",
                    "-o",
                    f"{tmpdir}/result.json",
                ]
            )

            port = get_free_port()

            report_server_proc = subprocess.Popen(
                report_server_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env={
                    "VIZTRACER_REPORT_SERVER_ENDPOINT": f"127.0.0.1:{port}",
                    **os.environ,
                },
                text=True,
            )

            script_cmd = cmd_with_coverage(["viztracer", "-c", "print('hello')"])

            line = report_server_proc.stdout.readline()
            self.assertIn(f"127.0.0.1:{port}", line)

            script_proc = subprocess.Popen(
                script_cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env={
                    "VIZTRACER_REPORT_SERVER_ENDPOINT": f"127.0.0.1:{port}",
                    **os.environ,
                },
                text=True,
            )

            script_proc.wait()

            report_server_proc.wait()
            report_server_proc.stdout.close()

            self.assertFileExists(f"{tmpdir}/result.json")

            with open(f"{tmpdir}/result.json") as f:
                data = json.load(f)
                self.assertTrue(
                    any("print" in event["name"] for event in data["traceEvents"])
                )

    @unittest.skipIf(
        sys.platform == "win32",
        "Skip Windows because we can't send SIGINT to subprocess properly",
    )
    def test_report_server_devnull_stdin(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cmd = cmd_with_coverage(
                [
                    "viztracer",
                    "--report_server",
                    "-o",
                    f"{tmpdir}/result.json",
                ]
            )

            report_server_proc = subprocess.Popen(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )

            report_server_proc.stdout.readline()  # Read the starting line
            report_server_proc.send_signal(signal.SIGINT)

            report_server_proc.wait()
            report_server_proc.stdout.close()

            self.assertEqual(0, report_server_proc.returncode)

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
