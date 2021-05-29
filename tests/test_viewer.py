# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt


from .cmdline_tmpl import CmdlineTmpl
import json
import multiprocessing
import os
import signal
import socket
import subprocess
import sys
import time
import tempfile
import unittest.mock
import urllib.request
from viztracer.viewer import viewer_main
import webbrowser


class Viewer(unittest.TestCase):
    def __init__(self, file_path, once=False, flamegraph=False):
        if os.getenv("COVERAGE_RUN"):
            self.cmd = ["coverage", "run", "-m", "--parallel-mode", "--pylib", "viztracer.viewer", "-s", file_path]
        else:
            self.cmd = ["vizviewer", "-s", file_path]

        if once:
            self.cmd.append("--once")

        if flamegraph:
            self.cmd.append("--flamegraph")
        self.process = None
        super().__init__()

    def run(self):
        self.process = subprocess.Popen(self.cmd)
        self._wait_until_socket_on()
        self.assertIs(self.process.poll(), None)

    def stop(self):
        self.process.send_signal(signal.SIGINT)
        self.process.wait(timeout=20)
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


class MockOpen(unittest.TestCase):
    def __init__(self, file_content):
        self.p = None
        self.file_content = file_content
        super().__init__()

    def get_and_check(self, url, expected):
        time.sleep(0.5)
        resp = urllib.request.urlopen(url)
        self.assertEqual(resp.read().decode("utf-8"), expected)

    def __call__(self, url):
        self.p = multiprocessing.Process(target=self.get_and_check, args=(url, self.file_content))
        self.p.start()


class TestViewer(CmdlineTmpl):
    @unittest.skipIf(sys.platform == "win32", "Can't send Ctrl+C reliably on Windows")
    def test_json(self):
        json_script = '{"file_info": {}, "traceEvents": []}'
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
                f.write(json_script)
            v = Viewer(f.name)
            try:
                v.run()
                time.sleep(0.5)
                resp = urllib.request.urlopen("http://127.0.0.1:9001")
                self.assertTrue(resp.code == 200)
                resp = urllib.request.urlopen("http://127.0.0.1:9001/file_info")
                self.assertEqual(json.loads(resp.read().decode("utf-8")), {})
                resp = urllib.request.urlopen("http://127.0.0.1:9001/localtrace")
                self.assertEqual(json.loads(resp.read().decode("utf-8")), json.loads(json_script))
            finally:
                v.stop()
        finally:
            os.remove(f.name)

    @unittest.skipIf(sys.platform == "win32", "Can't send Ctrl+C reliably on Windows")
    def test_html(self):
        html = '<html></html>'
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as f:
                f.write(html)
            v = Viewer(f.name)
            try:
                v.run()
                time.sleep(0.5)
                resp = urllib.request.urlopen("http://127.0.0.1:9001")
                self.assertTrue(resp.code == 200)
            finally:
                v.stop()
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
            v.process.wait(timeout=20)
            self.assertTrue(resp.code == 200)
            self.assertTrue(v.process.returncode == 0)
        finally:
            os.remove(f.name)

        json_script = '{"file_info": {}, "traceEvents": []}'
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
                f.write(json_script)
            v = Viewer(f.name, once=True)
            v.run()
            try:
                time.sleep(0.5)
                resp = urllib.request.urlopen("http://127.0.0.1:9001")
                self.assertTrue(resp.code == 200)
                resp = urllib.request.urlopen("http://127.0.0.1:9001/file_info")
                self.assertEqual(json.loads(resp.read().decode("utf-8")), {})
                resp = urllib.request.urlopen("http://127.0.0.1:9001/localtrace")
                self.assertEqual(json.loads(resp.read().decode("utf-8")), json.loads(json_script))
            except Exception:
                v.stop()
                raise
            finally:
                try:
                    v.process.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    v.process.kill()
        finally:
            os.remove(f.name)

    def test_flamegraph(self):
        json_script = '{"file_info": {}, "traceEvents": []}'
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
                f.write(json_script)
            v = Viewer(f.name, once=True, flamegraph=True)
            v.run()
            try:
                time.sleep(0.5)
                resp = urllib.request.urlopen("http://127.0.0.1:9001/vizviewer_info")
                self.assertTrue(resp.code == 200)
                self.assertTrue(json.loads(resp.read().decode("utf-8"))["is_flamegraph"], True)
                resp = urllib.request.urlopen("http://127.0.0.1:9001/flamegraph")
                self.assertEqual(json.loads(resp.read().decode("utf-8")), [])
            except Exception:
                v.stop()
                raise
            finally:
                try:
                    v.process.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    v.process.kill()
        finally:
            os.remove(f.name)

    @unittest.skipIf(sys.platform == "darwin", "MacOS has a high security check for multiprocessing")
    def test_browser(self):
        html = '<html></html>'
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as f:
                f.write(html)
            with unittest.mock.patch.object(sys, "argv", ["vizviewer", "--once", f.name]):
                with unittest.mock.patch.object(webbrowser, "open_new_tab", MockOpen(html)) as mock_obj:
                    viewer_main()
                    mock_obj.p.join()
                    self.assertEqual(mock_obj.p.exitcode, 0)
        finally:
            os.remove(f.name)

    def test_invalid(self):
        self.template(["vizviewer", "do_not_exist.json"], success=False, expected_output_file=None)
        self.template(["vizviewer", "README.md"], success=False, expected_output_file=None)
        self.template(["vizviewer", "--flamegraph", "README.md"], success=False, expected_output_file=None)
