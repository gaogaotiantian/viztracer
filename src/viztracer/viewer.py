# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

import argparse
import functools
import http.server
import json
import os
import socketserver
import sys


class HttpHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-store')
        return super().end_headers()

    def log_message(self, format, *args):
        # To quiet the http server
        pass


class PerfettoHandler(HttpHandler):
    def __init__(self, file_info, tracefile_path, *args, **kwargs):
        self.file_info = file_info
        self.tracefile_path = tracefile_path
        super().__init__(*args, **kwargs)

    def do_GET(self):
        self.server.last_request = self.path
        if self.path.endswith("file_info"):
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
        else:
            self.directory = os.path.join(os.path.dirname(__file__), "web_dist")
            os.chdir(self.directory)
            return super().do_GET()


class HtmlHandler(HttpHandler):
    def __init__(self, tracefile_path, *args, **kwargs):
        self.tracefile_path = tracefile_path
        super().__init__(*args, **kwargs)

    def do_GET(self):
        os.chdir(os.path.dirname(self.tracefile_path))
        filename = os.path.basename(self.tracefile_path)
        self.path = f"/{filename}"
        self.server.trace_served = True
        return super().do_GET()


def view(path, server_only=False, once=False):
    # For official perfetto, only localhost:9001 is allowed
    port = 9001

    # Get file data
    os.chdir(os.path.dirname(path))
    filename = os.path.basename(path)

    if filename.endswith("json"):
        trace_data = None
        with open(filename) as f:
            trace_data = json.load(f)
            file_info = trace_data.get("file_info", {})
        Handler = functools.partial(PerfettoHandler, file_info, path)
    elif filename.endswith("html"):
        Handler = functools.partial(HtmlHandler, path)
    else:
        print(f"Do not support file type {filename}")
        return 1

    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(('127.0.0.1', port), Handler) as httpd:
        if not once:
            print("Running vizviewer")
            print("You can also view your trace on http://localhost:9001")
            print("Press Ctrl+C to quit")
        if not server_only:
            # import webbrowser only if necessary
            import webbrowser
            webbrowser.open_new_tab(f'http://127.0.0.1:{port}')
        try:
            if once:
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
    parser.add_argument("--once", default=False, action="store_true",
                        help="Only serve trace data once, then exit")

    options = parser.parse_args(sys.argv[1:])
    f = options.file[0]
    if os.path.exists(f):
        path = os.path.abspath(options.file[0])
        cwd = os.getcwd()
        try:
            ret_code = view(
                path,
                server_only=options.server_only,
                once=options.once
            )
        finally:
            os.chdir(cwd)
        return ret_code
    else:
        print(f"File {f} does not exist!")
        return 1


if __name__ == "__main__":
    exit(viewer_main())
