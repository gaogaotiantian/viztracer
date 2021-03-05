# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt


from .cmdline_tmpl import CmdlineTmpl
import multiprocessing
import os
import re
import socketserver
import sys
import time
import unittest.mock
import urllib.request
import webbrowser

from viztracer import viewer_main


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
        if url.endswith("json"):
            m = re.search("url=(.*)", url)
            self.p = multiprocessing.Process(target=self.get_and_check, args=(m.group(1), self.file_content))
        elif url.endswith("html"):
            self.p = multiprocessing.Process(target=self.get_and_check, args=(url, self.file_content))
        self.p.start()


class MyTCPHandler(socketserver.BaseRequestHandler):
    def handle(self):
        pass


class TestViewer(CmdlineTmpl):
    def test_json(self):
        json_script = '{"traceEvents":[{"ph":"M","pid":17088,"tid":17088,"name":"process_name","args":{"name":"MainProcess"}},{"ph":"M","pid":17088,"tid":17088,"name":"thread_name","args":{"name":"MainThread"}},{"pid":17088,"tid":17088,"ts":20889378694.06,"dur":1001119.1,"name":"time.sleep","caller_lineno":4,"ph":"X","cat":"FEE"},{"pid":17088,"tid":17088,"ts":20889378692.96,"dur":1001122.5,"name":"<module> (/home/gaogaotiantian/programs/codesnap/scrabble4.py:1)","caller_lineno":238,"ph":"X","cat":"FEE"},{"pid":17088,"tid":17088,"ts":20889378692.46,"dur":1001124.7,"name":"builtins.exec","caller_lineno":238,"ph":"X","cat":"FEE"}],"viztracer_metadata":{"version":"0.12.0"}}'  # noqa: E501
        try:
            with open("test.json", "w") as f:
                f.write(json_script)
            with unittest.mock.patch.object(sys, "argv", ["vizviewer", "test.json"]):
                with unittest.mock.patch.object(webbrowser, "open_new_tab", MockOpen(json_script)) as mock_obj:
                    viewer_main()
                    mock_obj.p.join()
                    self.assertEqual(mock_obj.p.exitcode, 0)
        finally:
            os.remove("test.json")

    def test_html(self):
        html = '<html></html>'
        try:
            with open("test.html", "w") as f:
                f.write(html)
            with unittest.mock.patch.object(sys, "argv", ["vizviewer", "test.html"]):
                with unittest.mock.patch.object(webbrowser, "open_new_tab", MockOpen(html)) as mock_obj:
                    viewer_main()
                    mock_obj.p.join()
                    self.assertEqual(mock_obj.p.exitcode, 0)
        finally:
            os.remove("test.html")

    def test_port_occupied(self):
        html = '<html></html>'
        try:
            with open("test.html", "w") as f:
                f.write(html)
            with unittest.mock.patch.object(sys, "argv", ["vizviewer", "test.html"]):
                with socketserver.TCPServer(("127.0.0.1", 9001), MyTCPHandler) as _:
                    with unittest.mock.patch.object(webbrowser, "open_new_tab", MockOpen(html)) as mock_obj:
                        viewer_main()
                        mock_obj.p.join()
                        self.assertEqual(mock_obj.p.exitcode, 0)
        finally:
            os.remove("test.html")

    def test_invalid(self):
        self.template(["vizviewer", "do_not_exist.json"], success=False, expected_output_file=None)
        self.template(["vizviewer", "README.md"], success=False, expected_output_file=None)
