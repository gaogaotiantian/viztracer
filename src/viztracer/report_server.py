# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt


import os
import selectors
import shutil
import socket
import sys
import tempfile
import threading

from .report_builder import ReportBuilder
from .util import same_line_print


class ReportServer:
    def __init__(self,
                 output_file: str,
                 minimize_memory: bool = False,
                 verbose: int = 1) -> None:
        self._host = None
        self._port = None
        self.paths: list[str] = []
        self.output_file = output_file
        self.minimize_memory = minimize_memory
        self.verbose = verbose
        self.report_directory: str | None = tempfile.mkdtemp(prefix="viztracer_report_")
        self._conns = set()
        self._socket: socket.socket | None = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.bind(("127.0.0.1", 0))
        self._thread: threading.Thread | None = None
        self._finish = False
        self._host, self._port = self._socket.getsockname()

    def __del__(self) -> None:
        self.clear()

    def clear(self) -> None:
        if self._socket is not None:
            self._socket.close()
            self._socket = None
        if self.report_directory and os.path.exists(self.report_directory):
            try:
                shutil.rmtree(self.report_directory)
            except Exception:  # pragma: no cover
                pass
        self.report_directory = None
        self.paths = []

    def start(self) -> None:
        if self._socket is None:
            raise RuntimeError("ReportServer has been cleared")
        self._socket.listen()
        self._thread = threading.Thread(target=self.handle_connections, name="_VizTracer_ReportServer", daemon=True)
        self._thread.start()

    def handle_connections(self) -> None:
        if self._socket is None:
            raise RuntimeError("ReportServer has been cleared")
        while True:
            conn, _ = self._socket.accept()
            self._conns.add(conn)
            if self._finish:
                conn.close()
                break

    @property
    def endpoint(self) -> str:
        if self._host is None or self._port is None or self.report_directory is None:
            raise RuntimeError("ReportServer has been cleared")
        return f"{self._host}:{self._port}:{self.report_directory}"

    def collect(self):
        if self._socket is None:
            raise RuntimeError("ReportServer has been cleared")

        # Notify the server to finish
        self._finish = True
        finish_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        finish_socket.connect((self._host, self._port))
        finish_socket.close()

        assert self._thread is not None
        self._thread.join()

        sel = selectors.DefaultSelector()
        for conn in self._conns:
            sel.register(conn, selectors.EVENT_READ)

        if len(self._conns) >= 2 and self.verbose > 0:
            if sys.platform == "win32":
                same_line_print("Wait for child processes to finish, Ctrl+C to skip")
            else:
                same_line_print("Wait for child processes to finish, Ctrl+C/Enter to skip")
                sel.register(sys.stdin, selectors.EVENT_READ)

        try:
            while self._conns:
                events = sel.select()
                for key, _ in events:
                    if key.fileobj is sys.stdin:
                        data = key.fileobj.readline()
                        if data == "\n":
                            raise KeyboardInterrupt()
                        else:
                            continue
                    try:
                        self._recv_info(key.fileobj)
                    except ConnectionError:
                        pass
                    finally:
                        sel.unregister(key.fileobj)
                        key.fileobj.close()
                        self._conns.remove(key.fileobj)
        except KeyboardInterrupt:
            if self.verbose > 0:
                same_line_print("Skipped remaining child processes\n")
        finally:
            try:
                sel.unregister(sys.stdin)
            except Exception:
                pass
            for conn in self._conns:
                sel.unregister(conn)
                conn.close()

    def __enter__(self) -> "ReportServer":
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.collect()
        self.save()
        self.clear()

    def _recv_info(self, conn: socket.socket) -> None:
        raw_data = b""
        conn.setblocking(True)
        conn.settimeout(120)
        while d := conn.recv(1024):
            raw_data += d
            if b"\n" in raw_data:
                break
        if b"\n" in raw_data:
            path = raw_data.decode("utf-8").split("\n")[0]
            self.paths.append(path)

    def save(self, output_file: str | None = None) -> None:
        builder = ReportBuilder(
            self.paths,
            minimize_memory=self.minimize_memory,
            verbose=self.verbose)
        if output_file is None:
            output_file = self.output_file

        builder.save(output_file=output_file)
        self.paths = []

    def discard(self) -> None:
        # Discard this server, without removing the temporary files
        # This is useful for forked child processes
        if self._socket is not None:
            self._socket.close()
            self._socket = None
        self.report_directory = None
        self.paths = []
