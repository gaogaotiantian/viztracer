# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

import argparse
import http.server
import os
import socketserver
import sys


class HttpHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-store')
        return super().end_headers()

    def do_GET(self):
        self.server.last_request = self.path
        return super().do_GET()

    def log_message(self, format, *args):
        pass


def viewer_main():
    # import webbrowser only if necessary
    import webbrowser
    parser = argparse.ArgumentParser()
    parser.add_argument("file", nargs=1, help="html/json/gz file to open")
    parser.add_argument("-p", "--port", type=int, default=9001, help="port you want to host your html server")

    options = parser.parse_args(sys.argv[1:])
    f = options.file[0]
    if os.path.exists(f):
        path = os.path.abspath(options.file[0])
        os.chdir(os.path.dirname(path))
        filename = os.path.basename(path)
        port = options.port
        socketserver.TCPServer.allow_reuse_address = True
        while port < 65535:
            try:
                with socketserver.TCPServer(('127.0.0.1', port), HttpHandler) as httpd:
                    if filename.endswith("html"):
                        webbrowser.open_new_tab(
                            f'http://127.0.0.1:{port}/{filename}'
                        )
                    elif filename.endswith("json") or filename.endswith("gz"):
                        webbrowser.open_new_tab(
                            f'https://ui.perfetto.dev/#!/?url=http://127.0.0.1:{port}/{filename}'
                        )
                    else:
                        print(f"Do not support file type {filename}")
                        return 1
                    while httpd.__dict__.get('last_request') != '/' + filename:
                        httpd.handle_request()
                return 0
            except OSError:
                port += 1
        else:  # pragma: no cover
            print("No port is available!")
            return 1
    else:
        print(f"File {f} does not exist!")
        return 1


if __name__ == "__main__":
    exit(viewer_main())
