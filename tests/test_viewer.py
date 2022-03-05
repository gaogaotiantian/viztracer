# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt


import shutil
from .cmdline_tmpl import CmdlineTmpl
import json
import multiprocessing
import os
import re
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
    def __init__(self, file_path, once=False, flamegraph=False, timeout=None):
        if os.getenv("COVERAGE_RUN"):
            self.cmd = ["coverage", "run", "--source", "viztracer", "--parallel-mode",
                        "-m", "viztracer.viewer", "-s", file_path]
        else:
            self.cmd = ["vizviewer", "-s", file_path]

        if once:
            self.cmd.append("--once")

        if flamegraph:
            self.cmd.append("--flamegraph")

        if timeout is not None:
            self.cmd.append("--timeout")
            self.cmd.append(f"{timeout}")

        self.process = None
        self.stopped = False
        super().__init__()

    def __enter__(self):
        self.run()

    def __exit__(self, type, value, traceback):
        self.stop()

    def run(self):
        self.stopped = False
        self.process = subprocess.Popen(self.cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self._wait_until_socket_on()
        self.assertIs(self.process.poll(), None)

    def stop(self):
        if not self.stopped:
            try:
                if self.process.poll() is None:
                    self.process.send_signal(signal.SIGINT)
                    self.process.wait(timeout=20)
                out, err = self.process.stdout.read().decode("utf-8"), self.process.stderr.read().decode("utf-8")
                self.assertEqual(self.process.returncode, 0, msg=f"stdout:\n{out}\nstderr\n{err}\n")
            finally:
                self.process.stdout.close()
                self.process.stderr.close()
                self.stopped = True

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
    def __init__(self, file_content, int_pid=None):
        self.p = None
        self.file_content = file_content
        self.int_pid = int_pid
        super().__init__()

    def get_and_check(self, url, expected):
        for _ in range(4):
            time.sleep(0.5)
            try:
                resp = urllib.request.urlopen(url, timeout=2)
            except Exception:
                continue
            self.assertRegex(resp.read().decode("utf-8"), re.compile(expected, re.DOTALL))
        if self.int_pid is not None:
            os.kill(self.int_pid, signal.SIGINT)

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
            v.stop()
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
                    v.stop()
                except subprocess.TimeoutExpired:
                    v.stop()
                    v.process.kill()
        finally:
            os.remove(f.name)

    def test_once_timeout(self):
        json_script = '{"file_info": {}, "traceEvents": []}'
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
                f.write(json_script)
            v = Viewer(f.name, once=True, timeout=1)
            v.run()
            try:
                v.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                v.stop()
                self.fail("--once did not timeout correctly")
            finally:
                try:
                    v.process.wait(timeout=20)
                    v.stop()
                except subprocess.TimeoutExpired:
                    v.stop()
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
                    v.stop()
                except subprocess.TimeoutExpired:
                    v.stop()
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

    @unittest.skipIf(sys.platform == "win32", "Can't send Ctrl+C reliably on Windows")
    def test_directory(self):
        test_data_dir = os.path.join(os.path.dirname(__file__), "data")
        with Viewer(test_data_dir):
            time.sleep(0.5)
            resp = urllib.request.urlopen("http://127.0.0.1:9001/")
            self.assertEqual(resp.code, 200)
            self.assertIn("fib.json", resp.read().decode("utf-8"))
            resp = urllib.request.urlopen("http://127.0.0.1:9001/fib.json")
            self.assertEqual(resp.url, "http://127.0.0.1:9002/")
            resp = urllib.request.urlopen("http://127.0.0.1:9001/old.json")
            self.assertEqual(resp.url, "http://127.0.0.1:9003/")

    @unittest.skipIf(sys.platform in ("darwin", "win32"),
                     "MacOS has a high security check for multiprocessing, Windows can't handle SIGINT")
    def test_directory_browser(self):
        html = '<html></html>'
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as f:
                f.write(html)
            tmp_dir = os.path.dirname(f.name)
            with unittest.mock.patch.object(sys, "argv", ["vizviewer", tmp_dir]):
                with unittest.mock.patch.object(
                        webbrowser, "open_new_tab",
                        MockOpen(r".*" + os.path.basename(f.name) + r".*", int_pid=os.getpid())) as mock_obj:
                    viewer_main()
                    mock_obj.p.join()
                    self.assertEqual(mock_obj.p.exitcode, 0)
        finally:
            os.remove(f.name)

    @unittest.skipIf(sys.platform == "win32", "Can't send Ctrl+C reliably on Windows")
    def test_directory_flamegraph(self):
        test_data_dir = os.path.join(os.path.dirname(__file__), "data")
        with Viewer(test_data_dir, flamegraph=True):
            time.sleep(0.5)
            resp = urllib.request.urlopen("http://127.0.0.1:9001/")
            self.assertEqual(resp.code, 200)
            self.assertIn("fib.json", resp.read().decode("utf-8"))
            resp = urllib.request.urlopen("http://127.0.0.1:9001/fib.json")
            self.assertEqual(resp.url, "http://127.0.0.1:9002/")
            resp = urllib.request.urlopen("http://127.0.0.1:9002/vizviewer_info")
            self.assertTrue(resp.code == 200)
            self.assertTrue(json.loads(resp.read().decode("utf-8"))["is_flamegraph"], True)
            resp = urllib.request.urlopen("http://127.0.0.1:9002/flamegraph")
            self.assertEqual(len(json.loads(resp.read().decode("utf-8"))[0]["flamegraph"]), 2)

    @unittest.skipIf(sys.platform == "win32", "Can't send Ctrl+C reliably on Windows")
    def test_directory_timeout(self):
        test_data_dir = os.path.join(os.path.dirname(__file__), "data")
        with Viewer(test_data_dir, timeout=2):
            time.sleep(0.5)
            resp = urllib.request.urlopen("http://127.0.0.1:9001/")
            self.assertEqual(resp.code, 200)
            self.assertIn("fib.json", resp.read().decode("utf-8"))
            resp = urllib.request.urlopen("http://127.0.0.1:9001/fib.json")
            self.assertEqual(resp.url, "http://127.0.0.1:9002/")
            time.sleep(2.5)
            resp = urllib.request.urlopen("http://127.0.0.1:9001/old.json")
            self.assertEqual(resp.url, "http://127.0.0.1:9002/")

    @unittest.skipIf(sys.platform == "win32", "Can't send Ctrl+C reliably on Windows")
    def test_directory_max_port(self):
        try:
            tmp_dir = tempfile.mkdtemp()
            json_data = {"traceEvents": []}
            for i in range(15):
                with open(os.path.join(tmp_dir, f"{i}.json"), "w") as f:
                    json.dump(json_data, f)
            with Viewer(tmp_dir):
                time.sleep(0.5)
                resp = urllib.request.urlopen("http://127.0.0.1:9001/")
                self.assertEqual(resp.code, 200)
                for i in range(15):
                    time.sleep(0.02)
                    resp = urllib.request.urlopen(f"http://127.0.0.1:9001/{i}.json")
                    self.assertEqual(resp.code, 200)
                    self.assertRegex(resp.url, "http://127.0.0.1:90[0-1][0-9]/")
        finally:
            shutil.rmtree(tmp_dir)

    def test_invalid(self):
        self.template(["vizviewer", "do_not_exist.json"], success=False, expected_output_file=None)
        self.template(["vizviewer", "README.md"], success=False, expected_output_file=None)
        self.template(["vizviewer", "--flamegraph", "README.md"], success=False, expected_output_file=None)
