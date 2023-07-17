# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

import argparse
import atexit
import contextlib
import functools
import html
import http.server
import io
import json
import os
import socket
import socketserver
import subprocess
import sys
import traceback
import threading
import time
import urllib.parse
from http import HTTPStatus
from typing import Any, Callable, Dict, List, Optional

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


class ExternalProcessorHandler(HttpHandler):
    def __init__(
            self,
            server_thread: "ServerThread",
            *args, **kwargs) -> None:
        self.server_thread = server_thread
        super().__init__(*args, **kwargs)

    def do_GET(self):
        self.server.last_request = self.path
        self.server_thread.notify_active()
        self.directory = os.path.join(os.path.dirname(__file__), "web_dist")
        with chdir_temp(self.directory):
            return super().do_GET()


class PerfettoHandler(HttpHandler):
    def __init__(
            self,
            server_thread: "ServerThread",
            *args, **kwargs) -> None:
        self.server_thread = server_thread
        super().__init__(*args, **kwargs)

    def do_GET(self):
        self.server.last_request = self.path
        self.server_thread.notify_active()
        if self.path.endswith("vizviewer_info"):
            info = {
                "is_flamegraph": self.server_thread.flamegraph,
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
    def __init__(self, server_thread: "ServerThread", *args, **kwargs) -> None:
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
    def __init__(self, directory_viewer: "DirectoryViewer", *args, **kwargs) -> None:
        self.directory_viewer = directory_viewer
        kwargs["directory"] = directory_viewer.base_path
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
        title = f'Directory listing for {displaypath}'
        r.append('<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" '
                 '"http://www.w3.org/TR/html4/strict.dtd">')
        r.append('<html>\n<head>')
        r.append('<meta http-equiv="Content-Type" '
                 'content="text/html; charset=%s">' % enc)
        r.append(f'<title>{title}</title>\n</head>')
        r.append(f'<body>\n<h1>{title}</h1>')
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
        self.send_header("Content-type", f"text/html; charset={enc}")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        return f


class ExternalProcessorProcess:
    trace_processor_path = os.path.join(os.path.dirname(__file__), "web_dist", "trace_processor")

    def __init__(self, path: str) -> None:
        self.path = path
        self._process = subprocess.Popen(
            [
                sys.executable,
                self.trace_processor_path,
                self.path,
                "-D",
            ],
            stderr=subprocess.PIPE,
        )
        atexit.register(self.stop)
        self._wait_start()

    def _wait_start(self):
        print("Loading and parsing trace data, this could take a while...")
        while True:
            line = self._process.stderr.readline().decode("utf-8")
            if "This server can be used" in line:
                break

    def stop(self):
        self._process.terminate()
        try:
            self._process.wait(timeout=2)
        except subprocess.TimeoutExpired:  # pragma: no cover
            self._process.kill()
        atexit.unregister(self.stop)


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
            use_external_processor: bool = False,
            timeout: float = 10,
            quiet: bool = False) -> None:
        self.path = path
        self.port = port
        self.once = once
        self.timeout = timeout
        self.quiet = quiet
        self.link = f"http://127.0.0.1:{self.port}"
        self.flamegraph = flamegraph
        self.use_external_procesor = use_external_processor
        self.externel_processor_process: Optional[ExternalProcessorProcess] = None
        self.fg_data: Optional[List[Dict[str, Any]]] = None
        self.file_info = None
        self.httpd: Optional[VizViewerTCPServer] = None
        self.last_active = time.time()
        self.retcode: Optional[int] = None
        self.ready = threading.Event()
        self.ready.clear()
        super().__init__(daemon=True)

    def run(self) -> None:
        try:
            self.retcode = self.view()
        except Exception:
            self.retcode = 1
            traceback.print_exc()
        finally:
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
            if self.use_external_procesor:
                Handler = functools.partial(ExternalProcessorHandler, self)
                self.externel_processor_process = ExternalProcessorProcess(self.path)
            else:
                with open(self.path, encoding="utf-8", errors="ignore") as f:
                    trace_data = json.load(f)
                    self.file_info = trace_data.get("file_info", {})
                Handler = functools.partial(PerfettoHandler, self)
        elif filename.endswith("html"):
            Handler = functools.partial(HtmlHandler, self)
        else:
            print(f"Do not support file type {filename}")
            return 1

        if self.is_port_in_use():
            print(f'Error! Port {self.port} is already in use, try another port with "--port"')
            return 1

        socketserver.TCPServer.allow_reuse_address = True
        with VizViewerTCPServer(('0.0.0.0', self.port), Handler) as self.httpd:
            if not self.once and not self.quiet:
                print("Running vizviewer")
                print(f"You can also view your trace on http://localhost:{self.port}")
                print("Press Ctrl+C to quit", flush=True)
            self.ready.set()
            if self.once:
                self.httpd.timeout = self.timeout
                while not self.httpd.__dict__.get("trace_served", False):
                    self.httpd.handle_request()
            else:
                self.httpd.serve_forever()

        if self.externel_processor_process is not None:
            self.externel_processor_process.stop()

        return 0

    def notify_active(self) -> None:
        self.last_active = time.time()

    def is_port_in_use(self) -> bool:
        with contextlib.closing(
                socket.socket(socket.AF_INET,
                              socket.SOCK_STREAM)) as sock:
            return sock.connect_ex(('127.0.0.1', self.port)) == 0


class DirectoryViewer:
    def __init__(
            self,
            path: str,
            port: int,
            server_only: bool,
            flamegraph: bool,
            timeout: int,
            use_external_processor: bool) -> None:
        self.base_path = os.path.abspath(path)
        self.port = port
        self.server_only = server_only
        self.flamegraph = flamegraph
        self.timeout = timeout
        self.use_external_processor = use_external_processor
        self.max_port_number = 10
        self.servers: Dict[str, ServerThread] = {}

    def get_link(self, path: str) -> str:
        path = os.path.join(self.base_path, path)
        if path not in self.servers:
            self.servers[path] = self.create_server(path)

        server = self.servers[path]
        return server.link

    def create_server(self, path: str) -> ServerThread:
        max_port_number = self.max_port_number
        ports_used = set((serv.port for serv in self.servers.values()))
        if len(ports_used) == max_port_number:
            self.clean_servers(force=True)
        else:
            self.clean_servers(force=False)
        ports_used = set((serv.port for serv in self.servers.values()))
        for port in range(self.port + 1, self.port + max_port_number + 1):
            if port not in ports_used:
                t = ServerThread(
                    path,
                    port=port,
                    flamegraph=self.flamegraph,
                    use_external_processor=self.use_external_processor,
                    quiet=True)
                t.start()
                t.ready.wait()
                return t
        assert False, "Should always have a port available"  # pragma: no cover

    def clean_servers(self, force: bool = False) -> None:
        curr_time = time.time()
        removed_path = []
        for path, server in self.servers.items():
            if curr_time - server.last_active > self.timeout:
                if server.httpd is not None:
                    server.httpd.shutdown()
                removed_path.append(path)
                server.join()
        for path in removed_path:
            self.servers.pop(path)
        if len(removed_path) == 0 and force:
            max_idle_time, max_idle_path = max(
                (curr_time - server.last_active, path)
                for path, server in self.servers.items()
            )
            server = self.servers.pop(max_idle_path)
            if server.httpd:
                server.httpd.shutdown()
            server.join()

    def run(self) -> int:
        Handler = functools.partial(DirectoryHandler, self)
        socketserver.TCPServer.allow_reuse_address = True
        with VizViewerTCPServer(('0.0.0.0', self.port), Handler) as httpd:
            print("Running vizviewer")
            print(f"You can also view your trace on http://localhost:{self.port}")
            print("Press Ctrl+C to quit", flush=True)
            if not self.server_only:
                # import webbrowser only if necessary
                import webbrowser
                webbrowser.open_new_tab(f'http://127.0.0.1:{self.port}')
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                for server in self.servers.values():
                    if server.httpd:
                        server.httpd.shutdown()
                    server.join()
                self.servers = {}
        return 0


def viewer_main() -> int:
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
    parser.add_argument("--use_external_processor", default=False, action="store_true",
                        help="Use the more powerful external trace processor instead of WASM")

    options = parser.parse_args(sys.argv[1:])
    f = options.file[0]

    if options.use_external_processor:
        # Perfetto trace processor only accepts requests from localhost:10000
        options.port = 10000
        # external trace process won't work with once or flamegraph or directory
        if options.once:
            print("You can't use --once with --use_external_processor")
            return 1
        if options.flamegraph:
            print("You can't use --flamegraph with --use_external_processor")
            return 1
        if os.path.isdir(f):
            print("You can't use --use_external_processor on a directory")
            return 1

    if os.path.isdir(f):
        cwd = os.getcwd()
        try:
            directory_viewer = DirectoryViewer(
                path=f,
                port=options.port,
                server_only=options.server_only,
                flamegraph=options.flamegraph,
                timeout=options.timeout,
                use_external_processor=options.use_external_processor,
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
                timeout=options.timeout,
                use_external_processor=options.use_external_processor,
            )
            server.start()
            server.ready.wait()
            if server.retcode is not None:
                return server.retcode
            if not options.server_only:
                # import webbrowser only if necessary
                import webbrowser
                webbrowser.open_new_tab(f'http://127.0.0.1:{options.port}')
            while server.is_alive():
                server.join(timeout=1)
        except KeyboardInterrupt:
            if server.httpd is not None:
                server.httpd.shutdown()
            server.join(timeout=2)
        finally:
            os.chdir(cwd)
    else:
        print(f"File {f} does not exist!")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(viewer_main())
