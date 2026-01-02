# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt


import json
import os
import selectors
import shutil
import socket
import subprocess
import sys
import tempfile

from .report_builder import ReportBuilder
from .util import same_line_print


class ReportServer:
    def __init__(self,
                 output_file: str,
                 minimize_memory: bool = False,
                 verbose: int = 1,
                 endpoint: str | None = None,
                 append_newline: bool = False) -> None:
        self._host = None
        self._port = None
        self.paths: list[str] = []
        self.output_file = output_file
        self.minimize_memory = minimize_memory
        self.verbose = verbose
        self.report_directory: str | None = tempfile.mkdtemp(prefix="viztracer_report_")
        self._socket: socket.socket | None = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._finish = False
        if endpoint is not None:
            self._host, port_str = endpoint.split(":")[:2]
            self._port = int(port_str)
        else:
            self._host, self._port = "127.0.0.1", 0
        if append_newline:
            # If ReportServer is started in a subprocess, make sure the parent process
            # can read each same_line_print in real time.
            from .util import set_same_line_print_end
            set_same_line_print_end("\n")

    @classmethod
    def start_process(
        cls,
        output_file: str,
        minimize_memory: bool = False,
        verbose: int = 1,
        report_endpoint: str | None = None,
        append_newline: bool = False,
    ) -> tuple["subprocess.Popen", str]:
        args = [sys.executable, "-u", "-m", "viztracer", "-o", output_file]

        # For now append_newline is only used for VizTracer save() function
        assert not (report_endpoint is not None and append_newline is True)

        if report_endpoint is not None:
            args.extend(["--report_server", report_endpoint])
        elif append_newline:
            args.extend(["--report_server", "append_newline"])
        else:
            args.append("--report_server")

        if minimize_memory:
            args.append("--minimize_memory")
        if verbose == 0:
            args.append("--quiet")

        proc = subprocess.Popen(args, bufsize=0, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        assert proc.stdout is not None
        line = proc.stdout.readline().strip()
        endpoint = line.decode().split()[-1]
        return proc, endpoint

    def __del__(self) -> None:
        self.clear()

    def run(self) -> None:
        if self._socket is None:
            raise RuntimeError("ReportServer has been cleared")
        self._socket.bind((self._host, self._port))
        self._host, self._port = self._socket.getsockname()
        self.collect()
        self.save()

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

    @property
    def endpoint(self) -> str:
        return f"{self._host}:{self._port}"

    def collect(self):
        self._socket.listen()
        print(f"Report server started at {self.endpoint}", flush=True)
        sel = selectors.DefaultSelector()
        sel.register(self._socket, selectors.EVENT_READ)
        if sys.platform != "win32":
            sel.register(sys.stdin, selectors.EVENT_READ)
        const_count = len(sel.get_map())

        started = False
        unfinished_children = 0

        try:
            while True:
                if started:
                    if len(sel.get_map()) == const_count:
                        # No active connections
                        break
                    else:
                        if len(sel.get_map()) - const_count != unfinished_children and self.verbose > 0:
                            unfinished_children = len(sel.get_map()) - const_count
                            same_line_print(f"Waiting for {unfinished_children} connections to send reports. "
                                            "Ctrl+C to ignore and dump now.")
                events = sel.select()
                for key, _ in events:
                    if key.fileobj is self._socket:
                        conn, _ = self._socket.accept()
                        sel.register(conn, selectors.EVENT_READ)
                        conn.sendall((self.report_directory + "\n").encode())
                        started = True
                    elif key.fileobj is sys.stdin:
                        # On Unix, we can use stdin to break the loop
                        data = key.fileobj.readline()
                        if data == "\n":
                            raise KeyboardInterrupt()
                    else:
                        try:
                            self._recv_info(key.fileobj)
                        except KeyboardInterrupt:  # pragma: no cover
                            raise
                        except Exception:
                            pass
                        finally:
                            sel.unregister(key.fileobj)
                            key.fileobj.close()
        except KeyboardInterrupt:
            pass
        finally:
            if self.verbose > 0:
                same_line_print("")
            sel.close()

    def _recv_info(self, conn: socket.socket) -> None:
        buffer = b""
        conn.settimeout(10)
        while d := conn.recv(1024):
            buffer += d
            if b"\n" in buffer:
                break
        if b"\n" in buffer:
            data = json.loads(buffer.decode().strip())
            if "output_file" in data:
                self.output_file = data["output_file"]
            if "path" in data:
                self.paths.append(data["path"])

    def save(self) -> None:
        if not self.paths:
            if self.verbose > 0:
                print("No reports collected, nothing to save.")
            return
        builder = ReportBuilder(
            self.paths,
            minimize_memory=self.minimize_memory,
            verbose=self.verbose)

        builder.save(output_file=self.output_file)
        self.paths = []
