# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt


from .cmdline_tmpl import CmdlineTmpl
import os
import signal
import socket
import subprocess
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
        self.assertTrue(self.process.returncode == 0)

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
    def test_json(self):
        json_script = '{"traceEvents":[{"ph":"M","pid":17088,"tid":17088,"name":"process_name","args":{"name":"MainProcess"}},{"ph":"M","pid":17088,"tid":17088,"name":"thread_name","args":{"name":"MainThread"}},{"pid":17088,"tid":17088,"ts":20889378694.06,"dur":1001119.1,"name":"time.sleep","caller_lineno":4,"ph":"X","cat":"FEE"},{"pid":17088,"tid":17088,"ts":20889378692.96,"dur":1001122.5,"name":"<module> (/home/gaogaotiantian/programs/codesnap/scrabble4.py:1)","caller_lineno":238,"ph":"X","cat":"FEE"},{"pid":17088,"tid":17088,"ts":20889378692.46,"dur":1001124.7,"name":"builtins.exec","caller_lineno":238,"ph":"X","cat":"FEE"}],"viztracer_metadata":{"version":"0.12.0"}}'  # noqa: E501
        try:
            _, path = tempfile.mkstemp(suffix=".json", text=True)
            with open(path, "w") as f:
                f.write(json_script)
            v = Viewer(path)
            v.run()
            time.sleep(0.5)
            resp = urllib.request.urlopen("http://127.0.0.1:9001")
            self.assertTrue(resp.code == 200)
            v.stop()
        finally:
            os.remove(path)

    def test_html(self):
        html = '<html></html>'
        try:
            _, path = tempfile.mkstemp(suffix=".html", text=True)
            with open(path, "w") as f:
                f.write(html)
            v = Viewer(path)
            v.run()
            time.sleep(0.5)
            resp = urllib.request.urlopen("http://127.0.0.1:9001")
            self.assertTrue(resp.code == 200)
            v.stop()
        finally:
            os.remove(path)

    def test_once(self):
        html = '<html></html>'
        try:
            _, path = tempfile.mkstemp(suffix=".html", text=True)
            with open(path, "w") as f:
                f.write(html)
            v = Viewer(path, once=True)
            v.run()
            time.sleep(0.5)
            resp = urllib.request.urlopen("http://127.0.0.1:9001")
            self.assertTrue(resp.code == 200)
            v.process.wait()
            self.assertTrue(v.process.returncode == 0)
        finally:
            os.remove(path)

    def test_invalid(self):
        self.template(["vizviewer", "do_not_exist.json"], success=False, expected_output_file=None)
        self.template(["vizviewer", "README.md"], success=False, expected_output_file=None)
