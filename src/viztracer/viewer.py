# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

import argparse
import contextlib
import functools
import html
from http import HTTPStatus
import http.server
import io
import json
import os
import socketserver
import sys
import threading
import time
from typing import Any, Callable, Dict, List, Optional
import urllib.parse

from .flamegraph import FlameGraph


dir_lock = threading.Lock()


@contextlib.contextmanager
def chdir_temp(d):
    with dir_lock:
        curr_cwd = os.getcwd()
        os.chdir(d)
        try:
            yield
        finally:
            os.chdir(curr_cwd)


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
            server_thread: "ServerThread",
            *args, **kwargs):
        self.server_thread = server_thread
        super().__init__(*args, **kwargs)

    def do_GET(self):
        self.server.last_request = self.path
        self.server_thread.notify_active()
        if self.path.endswith("vizviewer_info"):
            info = {
                "is_flamegraph": self.server_thread.flamegraph
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
            self.wfile.write(json.dumps(self.server_thread.file_info).encode("utf-8"))
            self.wfile.flush()
        elif self.path.endswith("localtrace"):
            # self.directory is used after 3.8
            # os.getcwd() is used on 3.6
            self.directory = os.path.dirname(self.server_thread.path)
            with chdir_temp(self.directory):
                filename = os.path.basename(self.server_thread.path)
                self.path = f"/{filename}"
                self.server.trace_served = True
                return super().do_GET()
        elif self.path.endswith("flamegraph"):
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(self.server_thread.fg_data).encode("utf-8"))
            self.wfile.flush()
            self.server.trace_served = True
        else:
            self.directory = os.path.join(os.path.dirname(__file__), "web_dist")
            with chdir_temp(self.directory):
                return super().do_GET()


class HtmlHandler(HttpHandler):
    def __init__(self, server_thread: "ServerThread", *args, **kwargs):
        self.server_thread = server_thread
        super().__init__(*args, **kwargs)

    def do_GET(self):
        self.directory = os.path.dirname(self.server_thread.path)
        with chdir_temp(self.directory):
            filename = os.path.basename(self.server_thread.path)
            self.path = f"/{filename}"
            self.server.trace_served = True
            return super().do_GET()


class DirectoryHandler(HttpHandler):
    def __init__(self, directory_viewer: "DirectoryViewer", *args, **kwargs):
        self.directory_viewer = directory_viewer
        # py3.6 does not have directory in kwargs
        if sys.version_info >= (3, 7):
            kwargs["directory"] = directory_viewer.base_path
        else:
            self.directory = directory_viewer.base_path
        super().__init__(*args, **kwargs)

    def do_GET(self):
        if self.path.endswith("json"):
            # self.path starts with '/', we need to remove it
            self.send_response(302)
            self.send_header("Location", self.directory_viewer.get_link(self.path[1:]))
            self.end_headers()
        else:
            with chdir_temp(self.directory):
                super().do_GET()

    def send_head(self):  # pragma: no cover
        """
        Return list_directory even if there's an index.html in the dir
        """
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            parts = urllib.parse.urlsplit(self.path)
            if not parts.path.endswith('/'):
                # redirect browser - doing basically what apache does
                self.send_response(HTTPStatus.MOVED_PERMANENTLY)
                new_parts = (parts[0], parts[1], parts[2] + '/',
                             parts[3], parts[4])
                new_url = urllib.parse.urlunsplit(new_parts)
                self.send_header("Location", new_url)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return None
            else:
                return self.list_directory(path)
        return super().send_head()

    def list_directory(self, path):  # pragma: no cover
        """
        Almost the same as SimpleHTTPRequestHandler.list_directory, but
            * Does not display file that does not end with json
            * Created a new tab when click
        """
        try:
            list = os.listdir(path)
        except OSError:
            self.send_error(
                HTTPStatus.NOT_FOUND,
                "No permission to list directory")
            return None
        list.sort(key=lambda a: a.lower())
        r = []
        try:
            displaypath = urllib.parse.unquote(self.path,
                                               errors='surrogatepass')
        except UnicodeDecodeError:
            displaypath = urllib.parse.unquote(path)
        displaypath = html.escape(displaypath, quote=False)
        enc = sys.getfilesystemencoding()
        title = 'Directory listing for %s' % displaypath
        r.append('<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" '
                 '"http://www.w3.org/TR/html4/strict.dtd">')
        r.append('<html>\n<head>')
        r.append('<meta http-equiv="Content-Type" '
                 'content="text/html; charset=%s">' % enc)
        r.append('<title>%s</title>\n</head>' % title)
        r.append('<body>\n<h1>%s</h1>' % title)
        r.append('<hr>\n<ul>')
        for name in list:
            fullname = os.path.join(path, name)
            displayname = linkname = name
            # Append / for directories or @ for symbolic links
            if os.path.isdir(fullname):
                displayname = name + "/"
                linkname = name + "/"
            elif not name.endswith("json") and not name.endswith("html"):
                # Do not display files that we can't handle
                continue
            if os.path.islink(fullname):
                displayname = name + "@"
                # Note: a link to a directory displays with @ and links with /
            if os.path.isdir(fullname):
                r.append('<li><a href="%s">%s</a></li>'
                         % (urllib.parse.quote(linkname,
                                               errors='surrogatepass'),
                            html.escape(displayname, quote=False)))
            else:
                # Open a new tab
                r.append('<li><a href="%s" target="_blank">%s</a></li>'
                         % (urllib.parse.quote(linkname,
                                               errors='surrogatepass'),
                            html.escape(displayname, quote=False)))
        r.append('</ul>\n<hr>\n</body>\n</html>\n')
        encoded = '\n'.join(r).encode(enc, 'surrogateescape')
        f = io.BytesIO()
        f.write(encoded)
        f.seek(0)
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-type", "text/html; charset=%s" % enc)
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        return f


class VizViewerTCPServer(socketserver.TCPServer):
    def handle_timeout(self) -> None:
        self.trace_served = True
        return super().handle_timeout()


class ServerThread(threading.Thread):
    def __init__(
            self,
            path: str,
            port: int = 9001,
            once: bool = False,
            flamegraph: bool = False,
            timeout: float = 10,
            quiet: bool = False):
        self.path = path
        self.port = port
        self.once = once
        self.timeout = timeout
        self.quiet = quiet
        self.link = f"http://127.0.0.1:{self.port}"
        self.flamegraph = flamegraph
        self.fg_data: Optional[List[Dict[str, Any]]] = None
        self.file_info = None
        self.httpd: Optional[VizViewerTCPServer] = None
        self.last_active = time.time()
        self.retcode = None
        self.ready = threading.Event()
        self.ready.clear()
        super().__init__(daemon=True)

    def run(self):
        self.retcode = self.view()
        # If it returns from view(), also set ready
        self.ready.set()

    def view(self) -> int:
        # Get file data
        filename = os.path.basename(self.path)

        Handler: Callable[..., HttpHandler]
        if self.flamegraph:
            if filename.endswith("json"):
                with open(self.path, encoding="utf-8", errors="ignore") as f:
                    trace_data = json.load(f)
                fg = FlameGraph(trace_data)
                self.fg_data = fg.dump_to_perfetto()
                Handler = functools.partial(PerfettoHandler, self)
            else:
                print(f"Do not support flamegraph for file type {filename}")
                return 1
        elif filename.endswith("json"):
            trace_data = None
            with open(self.path, encoding="utf-8", errors="ignore") as f:
                trace_data = json.load(f)
                self.file_info = trace_data.get("file_info", {})
            Handler = functools.partial(PerfettoHandler, self)
        elif filename.endswith("html"):
            Handler = functools.partial(HtmlHandler, self)
        else:
            print(f"Do not support file type {filename}")
            return 1

        socketserver.TCPServer.allow_reuse_address = True
        with VizViewerTCPServer(('0.0.0.0', self.port), Handler) as self.httpd:
            if not self.once and not self.quiet:
                print("Running vizviewer")
                print(f"You can also view your trace on http://localhost:{self.port}")
                print("Press Ctrl+C to quit")
            self.ready.set()
            if self.once:
                self.httpd.timeout = self.timeout
                while not self.httpd.__dict__.get("trace_served", False):
                    self.httpd.handle_request()
            else:
                self.httpd.serve_forever()

        return 0

    def notify_active(self):
        self.last_active = time.time()


class DirectoryViewer:
    def __init__(self, path: str, port: int, server_only: bool, flamegraph: bool, timeout: int):
        self.base_path = os.path.abspath(path)
        self.port = port
        self.server_only = server_only
        self.flamegraph = flamegraph
        self.timeout = timeout
        self.max_port_number = 10
        self.servers: Dict[str, ServerThread] = {}

    def get_link(self, path: str) -> str:
        path = os.path.join(self.base_path, path)
        if path not in self.servers:
            self.servers[path] = self.create_server(path)

        server = self.servers[path]
        return server.link

    def create_server(self, path) -> ServerThread:
        max_port_number = self.max_port_number
        ports_used = set((serv.port for serv in self.servers.values()))
        if len(ports_used) == max_port_number:
            self.clean_servers(force=True)
        else:
            self.clean_servers(force=False)
        ports_used = set((serv.port for serv in self.servers.values()))
        for port in range(self.port + 1, self.port + max_port_number + 1):
            if port not in ports_used:
                t = ServerThread(path, port=port, flamegraph=self.flamegraph, quiet=True)
                t.start()
                t.ready.wait()
                return t
        assert False, "Should always have a port available"  # pragma: no cover

    def clean_servers(self, force=False):
        curr_time = time.time()
        removed_path = []
        for path, server in self.servers.items():
            if curr_time - server.last_active > self.timeout:
                server.httpd.shutdown()
                removed_path.append(path)
                server.join()
        for path in removed_path:
            self.servers.pop(path)
        if len(removed_path) == 0 and force:
            max_idle_time, max_idle_path = 0, None
            for path, server in self.servers.items():
                if curr_time - server.last_active > max_idle_time:
                    max_idle_time, max_idle_path = curr_time - server.last_active, path
            server = self.servers.pop(max_idle_path)
            server.httpd.shutdown()
            server.join()

    def run(self):
        Handler = functools.partial(DirectoryHandler, self)
        socketserver.TCPServer.allow_reuse_address = True
        with VizViewerTCPServer(('0.0.0.0', self.port), Handler) as httpd:
            print("Running vizviewer")
            print(f"You can also view your trace on http://localhost:{self.port}")
            print("Press Ctrl+C to quit")
            if not self.server_only:
                # import webbrowser only if necessary
                import webbrowser
                webbrowser.open_new_tab(f'http://127.0.0.1:{self.port}')
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                for server in self.servers.values():
                    server.httpd.shutdown()
                    server.join()
                self.servers = {}
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
                        help="Timeout in seconds to stop the server without trace data requests")
    parser.add_argument("--flamegraph", default=False, action="store_true",
                        help="Show flamegraph of data")

    options = parser.parse_args(sys.argv[1:])
    f = options.file[0]
    if os.path.isdir(f):
        cwd = os.getcwd()
        try:
            directory_viewer = DirectoryViewer(
                path=f,
                port=options.port,
                server_only=options.server_only,
                flamegraph=options.flamegraph,
                timeout=options.timeout
            )
            directory_viewer.run()
        finally:
            os.chdir(cwd)
    elif os.path.exists(f):
        path = os.path.abspath(options.file[0])
        cwd = os.getcwd()
        try:
            server = ServerThread(
                path,
                port=options.port,
                once=options.once,
                flamegraph=options.flamegraph,
                timeout=options.timeout
            )
            server.start()
            server.ready.wait()
            if server.retcode is not None:
                return server.retcode
            if not options.server_only:
                # import webbrowser only if necessary
                import webbrowser
                webbrowser.open_new_tab(f'http://127.0.0.1:{options.port}')
            server.join()
        except KeyboardInterrupt:
            server.httpd.shutdown()
            server.join(timeout=2)
        finally:
            os.chdir(cwd)
        return 0
    else:
        print(f"File {f} does not exist!")
        return 1


if __name__ == "__main__":
    exit(viewer_main())
