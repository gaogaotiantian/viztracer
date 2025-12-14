# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt


import os
import shutil
import socket
import tempfile

from .report_builder import ReportBuilder


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
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.bind(("127.0.0.1", 0))
        self._host, self._port = self._socket.getsockname()

    def __del__(self) -> None:
        self.clear()

    def clear(self) -> None:
        if self._socket is not None:
            self._socket.close()
        if self.report_directory and os.path.exists(self.report_directory):
            try:
                shutil.rmtree(self.report_directory)
            except OSError:
                pass
        self.report_directory = None
        self.paths = []

    def start(self) -> None:
        self._socket.listen()

    @property
    def endpoint(self) -> str:
        if self._host is None or self._port is None or self.report_directory is None:
            raise RuntimeError("ReportServer is not started")
        return f"{self._host}:{self._port}:{self.report_directory}"

    def collect(self):
        if self._socket is None:
            raise RuntimeError("ReportServer is not started")
        self._socket.setblocking(False)
        while True:
            try:
                conn, _ = self._socket.accept()
                try:
                    # Ensure we close the accepted connection even if receiving fails
                    self._recv_info(conn)
                except ConnectionError:
                    pass
                finally:
                    conn.close()
            except BlockingIOError:
                break

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
        self._socket.close()
        self.report_directory = None
        self.paths = []
