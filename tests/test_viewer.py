# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt


import gzip
import json
import multiprocessing
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import unittest.mock
import urllib.request
import webbrowser

import viztracer
from viztracer.viewer import viewer_main

from .cmdline_tmpl import CmdlineTmpl


class Viewer(unittest.TestCase):
    def __init__(
        self,
        file_path,
        once=False,
        timeout=None,
        use_external_processor=None,
        expect_success=True,
        port=None,
    ):
        if os.getenv("COVERAGE_RUN"):
            self.cmd = ["coverage", "run", "--source", "viztracer", "--parallel-mode",
                        "-m", "viztracer.viewer", "-s", file_path]
        else:
            self.cmd = ["vizviewer", "-s", file_path]

        if once:
            self.cmd.append("--once")

        if timeout is not None:
            self.cmd.append("--timeout")
            self.cmd.append(f"{timeout}")

        if use_external_processor:
            self.cmd.append("--use_external_processor")

        if port:
            self.port = port
            self.cmd.append("--port")
            self.cmd.append(f"{self.port}")
        elif use_external_processor:
            self.port = 10000
        else:
            self.port = 9001

        self.process = None
        self.stopped = False
        self.once = once
        self.use_external_processor = use_external_processor
        self.expect_success = expect_success
        super().__init__()

    def __enter__(self):
        self.run()
        return self

    def __exit__(self, type, value, traceback):
        self.stop()

    def run(self):
        self.stopped = False
        self.process = subprocess.Popen(self.cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8")
        if self.expect_success and not self.once:
            self._wait_until_stdout_ready()
        self._wait_until_socket_on()
        self.assertIs(self.process.poll(), None)

    def stop(self):
        if not self.stopped:
            try:
                if self.process.poll() is None:
                    self.process.send_signal(signal.SIGINT)
                    self.process.wait(timeout=20)
                out, err = self.process.communicate()
                if self.expect_success:
                    self.assertEqual(self.process.returncode, 0, msg=f"stdout:\n{out}\nstderr\n{err}\n")
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
                out, err = self.process.communicate()
                self.fail(f"Process timeout - stdout:\n{out}\nstderr\n{err}\n")
            finally:
                self.process.stdout.close()
                self.process.stderr.close()
                self.stopped = True

    def wait(self, timeout=20):
        assert self.process is not None
        self.process.wait(timeout=timeout)

    def _wait_until_stdout_ready(self):
        while True:
            line = self.process.stdout.readline()
            if "view your trace" in line:
                break

    def _wait_until_socket_on(self):
        port = self.port
        for _ in range(10):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            if result == 0:
                return
            time.sleep(1)
        self.fail(f"Can't connect to 127.0.0.1:{port}")

    def url(self, offset: int = 0) -> str:
        return f'http://127.0.0.1:{self.port + offset}'


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
        # fork in a multi-threaded program could result in dead lock
        ctx = multiprocessing.get_context("spawn")
        self.p = ctx.Process(target=self.get_and_check, args=(url, self.file_content))
        self.p.start()


class TestViewer(CmdlineTmpl):
    def _find_a_free_port(self) -> int:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('', 0))
        port = sock.getsockname()[1]
        sock.close()

        return port

    @unittest.skipIf(sys.platform == "win32", "Can't send Ctrl+C reliably on Windows")
    def test_custom_port(self):
        json_script = '{"file_info": {}, "traceEvents": []}'
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                f.write(json_script)
            with Viewer(f.name, port=self._find_a_free_port()) as v:
                time.sleep(0.5)
                resp = urllib.request.urlopen(v.url())
                self.assertTrue(resp.code == 200)
                resp = urllib.request.urlopen(f"{v.url()}/file_info")
                self.assertEqual(json.loads(resp.read().decode("utf-8")), {})
                resp = urllib.request.urlopen(f"{v.url()}/localtrace")
                self.assertEqual(json.loads(resp.read().decode("utf-8")), json.loads(json_script))
        finally:
            os.remove(f.name)

    @unittest.skipIf(sys.platform == "win32", "Can't send Ctrl+C reliably on Windows")
    def test_json(self):
        json_script = '{"file_info": {}, "traceEvents": []}'
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
                f.write(json_script)
            with Viewer(f.name) as v:
                time.sleep(0.5)
                resp = urllib.request.urlopen(v.url())
                self.assertTrue(resp.code == 200)
                resp = urllib.request.urlopen(f"{v.url()}/file_info")
                self.assertEqual(json.loads(resp.read().decode("utf-8")), {})
                resp = urllib.request.urlopen(f"{v.url()}/localtrace")
                self.assertEqual(json.loads(resp.read().decode("utf-8")), json.loads(json_script))
        finally:
            os.remove(f.name)

    @unittest.skipIf(sys.platform == "win32", "Can't send Ctrl+C reliably on Windows")
    def test_gz(self):
        json_script = '{"file_info": {}, "traceEvents": []}'
        with tempfile.TemporaryDirectory() as tmpdir:
            filename = os.path.join(tmpdir, "test.json.gz")
            with gzip.open(filename, "wt") as f:
                f.write(json_script)
            with Viewer(filename) as v:
                time.sleep(0.5)
                resp = urllib.request.urlopen(v.url())
                self.assertTrue(resp.code == 200)
                resp = urllib.request.urlopen(f"{v.url()}/file_info")
                self.assertEqual(json.loads(resp.read().decode("utf-8")), {})
                resp = urllib.request.urlopen(f"{v.url()}/localtrace")
                self.assertEqual(json.loads(gzip.decompress(resp.read()).decode("utf-8")),
                                 json.loads(json_script))

    @unittest.skipIf(sys.platform == "win32", "Can't send Ctrl+C reliably on Windows")
    def test_html(self):
        html = '<html></html>'
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as f:
                f.write(html)
            with Viewer(f.name) as v:
                time.sleep(0.5)
                resp = urllib.request.urlopen(v.url())
                self.assertTrue(resp.code == 200)
        finally:
            os.remove(f.name)

    @unittest.skipIf(sys.platform == "win32", "Can't send Ctrl+C reliably on Windows")
    def test_use_external_processor(self):
        json_script = '{"file_info": {}, "traceEvents": []}'
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
                f.write(json_script)
            with Viewer(f.name, use_external_processor=True) as v:
                time.sleep(0.5)
                resp = urllib.request.urlopen(v.url(), timeout=10)
                self.assertTrue(resp.code == 200)
        finally:
            os.remove(f.name)

    def test_external_processor_version(self):
        root_path = os.path.dirname(viztracer.__file__)
        web_dist_path = os.path.join(root_path, "web_dist")
        for path in os.listdir(web_dist_path):
            # match the version number in the file name (v47.0-deadbeef)
            if (match := re.match(r"v(\d+\.\d+)-[0-9a-f]+$", path)) is not None:
                perfetto_version = match.group(1)
                with open(os.path.join(web_dist_path, "trace_processor")) as f:
                    match = re.search(r"tools/roll-prebuilts v(\d+\.\d+)", f.read())
                if match is None:
                    self.fail("Can't find perfetto version in trace_processor")
                processor_version = match.group(1)
                # We need processor version to match exactly. The release branch of perfetto
                # does not have the trace_processor at the same version and we need to
                # dig it up.
                self.assertEqual(perfetto_version, processor_version)
                break

    @unittest.skipIf(sys.platform == "win32", "Can't send Ctrl+C reliably on Windows")
    def test_port_in_use_error(self):
        json_script = '{"file_info": {}, "traceEvents": []}'
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
                f.write(json_script)
            with Viewer(f.name) as v:
                time.sleep(0.5)
                resp = urllib.request.urlopen(v.url())
                self.assertTrue(resp.code == 200)
                with Viewer(f.name, expect_success=False, port=v.port) as v2:
                    self.assertNotEqual(v2.process.returncode, 0)
                    stdout = v2.process.stdout.read()
                    self.assertIn("Error", stdout)
        finally:
            os.remove(f.name)

    def test_once(self):
        html = '<html></html>'
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as f:
                f.write(html)
            with Viewer(f.name, once=True) as v:
                time.sleep(0.5)
                resp = urllib.request.urlopen(v.url())
                v.wait()
                self.assertTrue(resp.code == 200)
                self.assertTrue(v.process.returncode == 0)
        finally:
            os.remove(f.name)

        json_script = '{"file_info": {}, "traceEvents": []}'
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
                f.write(json_script)
            with Viewer(f.name, once=True) as v:
                time.sleep(0.5)
                resp = urllib.request.urlopen(v.url())
                self.assertTrue(resp.code == 200)
                resp = urllib.request.urlopen(f"{v.url()}/localtrace")
                self.assertEqual(json.loads(resp.read().decode("utf-8")), json.loads(json_script))
                resp = urllib.request.urlopen(f"{v.url()}/file_info")
                self.assertEqual(json.loads(resp.read().decode("utf-8")), {})
                v.wait()
        finally:
            os.remove(f.name)

    def test_once_timeout(self):
        json_script = '{"file_info": {}, "traceEvents": []}'
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
                f.write(json_script)

            # --once won't work with --use_external_processor
            self.template(["vizviewer", "--once", "--use_external_processor", f.name],
                          success=False, expected_output_file=None)

            with Viewer(f.name, once=True, timeout=3) as v:
                try:
                    v.wait(timeout=6)
                except subprocess.TimeoutExpired:
                    self.fail("--once did not timeout correctly")
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

    def test_vizviewer_info(self):
        json_script = '{"file_info": {}, "traceEvents": []}'
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
                f.write(json_script)

            with Viewer(f.name, once=True) as v:
                time.sleep(0.5)
                resp = urllib.request.urlopen(f"{v.url()}/vizviewer_info")
                self.assertTrue(resp.code == 200)
                self.assertEqual(json.loads(resp.read().decode("utf-8")), {})
                resp = urllib.request.urlopen(f"{v.url()}/localtrace")
                self.assertEqual(json.loads(resp.read().decode("utf-8")), json.loads(json_script))
                v.wait()
        finally:
            os.remove(f.name)

    @unittest.skipIf(sys.platform == "win32", "Can't send Ctrl+C reliably on Windows")
    def test_directory(self):
        test_data_dir = os.path.join(os.path.dirname(__file__), "data")
        # --use_external_processor won't work with directory
        self.template(["vizviewer", "--use_external_processor", test_data_dir], success=False, expected_output_file=None)

        with Viewer(test_data_dir) as v:
            time.sleep(0.5)
            resp = urllib.request.urlopen(v.url())
            self.assertEqual(resp.code, 200)
            self.assertIn("fib.json", resp.read().decode("utf-8"))
            resp = urllib.request.urlopen(f"{v.url()}/fib.json")
            self.assertEqual(resp.url, f"{v.url(1)}/")
            resp = urllib.request.urlopen(f"{v.url()}/old.json")
            self.assertEqual(resp.url, f"{v.url(2)}/")

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
    def test_directory_timeout(self):
        test_data_dir = os.path.join(os.path.dirname(__file__), "data")
        with Viewer(test_data_dir, timeout=2) as v:
            time.sleep(0.5)
            resp = urllib.request.urlopen(v.url())
            self.assertEqual(resp.code, 200)
            self.assertIn("fib.json", resp.read().decode("utf-8"))
            resp = urllib.request.urlopen(f"{v.url()}/fib.json")
            self.assertEqual(resp.url, f"{v.url(1)}/")
            time.sleep(2.5)
            resp = urllib.request.urlopen(f"{v.url()}/old.json")
            self.assertEqual(resp.url, f"{v.url(1)}/")

    @unittest.skipIf(sys.platform == "win32", "Can't send Ctrl+C reliably on Windows")
    def test_directory_max_port(self):
        try:
            tmp_dir = tempfile.mkdtemp()
            json_data = {"traceEvents": []}
            for i in range(15):
                with open(os.path.join(tmp_dir, f"{i}.json"), "w") as f:
                    json.dump(json_data, f)
            with Viewer(tmp_dir) as v:
                time.sleep(0.5)
                resp = urllib.request.urlopen(v.url())
                self.assertEqual(resp.code, 200)
                for i in range(15):
                    time.sleep(0.02)
                    resp = urllib.request.urlopen(f"{v.url()}/{i}.json")
                    self.assertEqual(resp.code, 200)
                    self.assertRegex(resp.url, "http://127.0.0.1:90[0-1][0-9]/")
        finally:
            shutil.rmtree(tmp_dir)

    def test_exception(self):
        test_data_dir = os.path.join(os.path.dirname(__file__), "data")
        self.template(["vizviewer", "--port", "-3", os.path.join(test_data_dir, "fib.json")],
                      success=False, expected_output_file=None, expected_stderr=".*Traceback.*")

    def test_invalid(self):
        self.template(["vizviewer", "do_not_exist.json"], success=False, expected_output_file=None)
        self.template(["vizviewer", "README.md"], success=False, expected_output_file=None)
        self.template(["vizviewer", "--flamegraph", "README.md"], success=False, expected_output_file=None)
        self.template(["vizviewer", "--flamegraph", "example/json/multithread.md"],
                      success=False, expected_output_file=None, expected_stdout="--flamegraph is removed.*")
