# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt


from .cmdline_tmpl import CmdlineTmpl
import os
import signal
import socket
import subprocess
import sys
import time
import tempfile
import unittest.mock
import urllib.request


class Viewer(unittest.TestCase):
    def __init__(self, file_path, once=False):
        if os.getenv("COVERAGE_RUN"):
            self.cmd = ["coverage", "run", "-m", "--parallel-mode", "--pylib", "viztracer.viewer", "-s", file_path]
        else:
            self.cmd = ["vizviewer", "-s", file_path]

        if once:
            self.cmd.append("--once")
        self.process = None
        super().__init__()

    def run(self):
        self.process = subprocess.Popen(self.cmd)
        self._wait_until_socket_on()
        self.assertIs(self.process.poll(), None)

    def stop(self):
        self.process.send_signal(signal.SIGINT)
        self.process.wait()
        self.assertEqual(self.process.returncode, 0)

    def _wait_until_socket_on(self):
        for _ in range(10):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex(('127.0.0.1', 9001))
            sock.close()
            if result == 0:
                return
            time.sleep(1)
        self.fail("Can't connect to 127.0.0.1:9001")


class TestViewer(CmdlineTmpl):
    @unittest.skipIf(sys.platform == "win32", "Can't send Ctrl+C reliably on Windows")
    def test_json(self):
        json_script = '{"traceEvents":[{"ph":"M","pid":17088,"tid":17088,"name":"process_name","args":{"name":"MainProcess"}},{"ph":"M","pid":17088,"tid":17088,"name":"thread_name","args":{"name":"MainThread"}},{"pid":17088,"tid":17088,"ts":20889378694.06,"dur":1001119.1,"name":"time.sleep","caller_lineno":4,"ph":"X","cat":"FEE"},{"pid":17088,"tid":17088,"ts":20889378692.96,"dur":1001122.5,"name":"<module> (/home/gaogaotiantian/programs/codesnap/scrabble4.py:1)","caller_lineno":238,"ph":"X","cat":"FEE"},{"pid":17088,"tid":17088,"ts":20889378692.46,"dur":1001124.7,"name":"builtins.exec","caller_lineno":238,"ph":"X","cat":"FEE"}],"viztracer_metadata":{"version":"0.12.0"}}'  # noqa: E501
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
                f.write(json_script)
            v = Viewer(f.name)
            v.run()
            time.sleep(0.5)
            resp = urllib.request.urlopen("http://127.0.0.1:9001")
            v.stop()
            self.assertTrue(resp.code == 200)
        finally:
            os.remove(f.name)

    @unittest.skipIf(sys.platform == "win32", "Can't send Ctrl+C reliably on Windows")
    def test_html(self):
        html = '<html></html>'
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as f:
                f.write(html)
            v = Viewer(f.name)
            v.run()
            time.sleep(0.5)
            resp = urllib.request.urlopen("http://127.0.0.1:9001")
            v.stop()
            self.assertTrue(resp.code == 200)
        finally:
            os.remove(f.name)

    def test_once(self):
        html = '<html></html>'
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as f:
                f.write(html)
            v = Viewer(f.name, once=True)
            v.run()
            time.sleep(0.5)
            resp = urllib.request.urlopen("http://127.0.0.1:9001")
            v.process.wait()
            self.assertTrue(resp.code == 200)
            self.assertTrue(v.process.returncode == 0)
        finally:
            os.remove(f.name)

    def test_invalid(self):
        self.template(["vizviewer", "do_not_exist.json"], success=False, expected_output_file=None)
        self.template(["vizviewer", "README.md"], success=False, expected_output_file=None)
