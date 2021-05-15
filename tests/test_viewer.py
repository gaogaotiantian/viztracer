# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt


from .cmdline_tmpl import CmdlineTmpl
import os
import signal
import subprocess
import sys
import time
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

    def run(self):
        self.process = subprocess.Popen(self.cmd)

    def stop(self):
        self.process.send_signal(signal.SIGINT)
        self.process.wait()
        self.assertTrue(self.process.returncode == 0)


class TestViewer(CmdlineTmpl):
    @unittest.skipIf(sys.platform == "darwin", "MacOS has a high security check for multiprocessing")
    def test_json(self):
        json_script = '{"traceEvents":[{"ph":"M","pid":17088,"tid":17088,"name":"process_name","args":{"name":"MainProcess"}},{"ph":"M","pid":17088,"tid":17088,"name":"thread_name","args":{"name":"MainThread"}},{"pid":17088,"tid":17088,"ts":20889378694.06,"dur":1001119.1,"name":"time.sleep","caller_lineno":4,"ph":"X","cat":"FEE"},{"pid":17088,"tid":17088,"ts":20889378692.96,"dur":1001122.5,"name":"<module> (/home/gaogaotiantian/programs/codesnap/scrabble4.py:1)","caller_lineno":238,"ph":"X","cat":"FEE"},{"pid":17088,"tid":17088,"ts":20889378692.46,"dur":1001124.7,"name":"builtins.exec","caller_lineno":238,"ph":"X","cat":"FEE"}],"viztracer_metadata":{"version":"0.12.0"}}'  # noqa: E501
        try:
            with open("test.json", "w") as f:
                f.write(json_script)
            v = Viewer("test.json")
            v.run()
            time.sleep(0.5)
            resp = urllib.request.urlopen("http://127.0.0.1:9001")
            self.assertTrue(resp.code == 200)
            v.stop()
        finally:
            os.remove("test.json")

    @unittest.skipIf(sys.platform == "darwin", "MacOS has a high security check for multiprocessing")
    def test_html(self):
        html = '<html></html>'
        try:
            with open("test.html", "w") as f:
                f.write(html)
            v = Viewer("test.html")
            v.run()
            time.sleep(0.5)
            resp = urllib.request.urlopen("http://127.0.0.1:9001")
            self.assertTrue(resp.code == 200)
            v.stop()
        finally:
            os.remove("test.html")

    def test_once(self):
        html = '<html></html>'
        try:
            with open("test.html", "w") as f:
                f.write(html)
            v = Viewer("test.html", once=True)
            v.run()
            time.sleep(0.5)
            resp = urllib.request.urlopen("http://127.0.0.1:9001")
            self.assertTrue(resp.code == 200)
            v.process.wait()
            self.assertTrue(v.process.returncode == 0)
        finally:
            os.remove("test.html")

    def test_invalid(self):
        self.template(["vizviewer", "do_not_exist.json"], success=False, expected_output_file=None)
        self.template(["vizviewer", "README.md"], success=False, expected_output_file=None)
