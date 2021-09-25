# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

import argparse
import functools
import http.server
import json
import os
import socketserver
import sys
from typing import Any, Callable, Dict, List, Optional

from .flamegraph import FlameGraph


class HttpHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-store')
        return super().end_headers()

    def log_message(self, format, *args):
        # To quiet the http server
        pass


class PerfettoHandler(HttpHandler):
    def __init__(
            self,
            file_info: Optional[Dict[str, Any]],
            tracefile_path: str,
            flamegraph: List[Dict[str, Any]],
            *args, **kwargs):
        self.file_info = file_info
        self.tracefile_path = tracefile_path
        self.flamegraph = flamegraph
        super().__init__(*args, **kwargs)

    def do_GET(self):
        self.server.last_request = self.path
        if self.path.endswith("vizviewer_info"):
            info = {
                "is_flamegraph": self.flamegraph is not None
            }
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(info).encode("utf-8"))
            self.wfile.flush()
        elif self.path.endswith("file_info"):
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(self.file_info).encode("utf-8"))
            self.wfile.flush()
        elif self.path.endswith("localtrace"):
            # self.directory is used after 3.8
            # os.getcwd() is used on 3.6
            self.directory = os.path.dirname(self.tracefile_path)
            os.chdir(self.directory)
            filename = os.path.basename(self.tracefile_path)
            self.path = f"/{filename}"
            self.server.trace_served = True
            return super().do_GET()
        elif self.path.endswith("flamegraph"):
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(self.flamegraph).encode("utf-8"))
            self.wfile.flush()
            self.server.trace_served = True
        else:
            self.directory = os.path.join(os.path.dirname(__file__), "web_dist")
            os.chdir(self.directory)
            return super().do_GET()


class HtmlHandler(HttpHandler):
    def __init__(self, tracefile_path: str, *args, **kwargs):
        self.tracefile_path = tracefile_path
        super().__init__(*args, **kwargs)

    def do_GET(self):
        os.chdir(os.path.dirname(self.tracefile_path))
        filename = os.path.basename(self.tracefile_path)
        self.path = f"/{filename}"
        self.server.trace_served = True
        return super().do_GET()


class VizViewerTCPServer(socketserver.TCPServer):
    def handle_timeout(self) -> None:
        self.trace_served = True
        return super().handle_timeout()


def view(
        path: str,
        server_only: bool = False,
        port: int = 9001,
        once: bool = False,
        flamegraph: bool = False,
        timeout: float = 10) -> int:

    # Get file data
    os.chdir(os.path.dirname(path))
    filename = os.path.basename(path)

    Handler: Callable[..., HttpHandler]
    if flamegraph:
        if filename.endswith("json"):
            with open(filename) as f:
                trace_data = json.load(f)
            fg = FlameGraph(trace_data)
            fg_data = fg.dump_to_perfetto()
            Handler = functools.partial(PerfettoHandler, None, path, fg_data)
        else:
            print(f"Do not support flamegraph for file type {filename}")
            return 1
    elif filename.endswith("json"):
        trace_data = None
        with open(filename) as f:
            trace_data = json.load(f)
            file_info = trace_data.get("file_info", {})
        Handler = functools.partial(PerfettoHandler, file_info, path, None)
    elif filename.endswith("html"):
        Handler = functools.partial(HtmlHandler, path)
    else:
        print(f"Do not support file type {filename}")
        return 1

    socketserver.TCPServer.allow_reuse_address = True
    with VizViewerTCPServer(('0.0.0.0', port), Handler) as httpd:
        if not once:
            print("Running vizviewer")
            print(f"You can also view your trace on http://localhost:{port}")
            print("Press Ctrl+C to quit")
        if not server_only:
            # import webbrowser only if necessary
            import webbrowser
            webbrowser.open_new_tab(f'http://127.0.0.1:{port}')
        try:
            if once:
                httpd.timeout = timeout
                while not httpd.__dict__.get("trace_served", False):
                    httpd.handle_request()
            else:
                httpd.serve_forever()
        except KeyboardInterrupt:
            return 0

    return 0


def viewer_main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file", nargs=1, help="html/json/gz file to open")
    parser.add_argument("--server_only", "-s", default=False, action="store_true",
                        help="Only start the server, do not open webpage")
    parser.add_argument("--port", "-p", nargs="?", type=int, default=9001,
                        help="Specify the port vizviewer will use")
    parser.add_argument("--once", default=False, action="store_true",
                        help="Only serve trace data once, then exit.")
    parser.add_argument("--timeout", nargs="?", type=int, default=10,
                        help="Timeout in seconds to stop the server without trace data requests, only works with --once")
    parser.add_argument("--flamegraph", default=False, action="store_true",
                        help="Show flamegraph of data")

    options = parser.parse_args(sys.argv[1:])
    f = options.file[0]
    if os.path.exists(f):
        path = os.path.abspath(options.file[0])
        cwd = os.getcwd()
        try:
            ret_code = view(
                path,
                server_only=options.server_only,
                port=options.port,
                once=options.once,
                flamegraph=options.flamegraph,
                timeout=options.timeout
            )
        finally:
            os.chdir(cwd)
        return ret_code
    else:
        print(f"File {f} does not exist!")
        return 1


if __name__ == "__main__":
    exit(viewer_main())
