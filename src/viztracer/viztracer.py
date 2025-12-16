# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

import builtins
import gc
import inspect
import io
import multiprocessing
import os
import platform
import socket
import signal
import sys
from typing import Any, Callable, Literal, Sequence
from viztracer.snaptrace import Tracer

from . import __version__
from .patch import install_all_hooks, uninstall_all_hooks
from .report_builder import ReportBuilder
from .report_server import ReportServer
from .util import frame_stack_has_func, unique_path
from .vizevent import VizEvent
from .vizplugin import VizPluginBase, VizPluginManager


# This is the interface of the package. Almost all user should use this
# class for the functions
class VizTracer(Tracer):
    def __init__(self,
                 tracer_entries: int = 1000000,
                 verbose: int = 1,
                 max_stack_depth: int = -1,
                 include_files: list[str] | None = None,
                 exclude_files: list[str] | None = None,
                 ignore_c_function: bool = False,
                 ignore_frozen: bool = False,
                 log_func_retval: bool = False,
                 log_func_args: bool = False,
                 log_func_repr: Callable[..., str] | None = None,
                 log_func_with_objprint: bool = False,
                 log_print: bool = False,
                 log_gc: bool = False,
                 log_sparse: bool = False,
                 log_async: bool = False,
                 log_torch: bool = False,
                 log_audit: Sequence[str] | None = None,
                 ignore_multiprocess: bool = True,
                 pid_suffix: bool = False,
                 file_info: bool = True,
                 register_global: bool = True,
                 report_endpoint: str | None = None,
                 trace_self: bool = False,
                 min_duration: float = 0,
                 minimize_memory: bool = False,
                 dump_raw: bool = False,
                 sanitize_function_name: bool = False,
                 process_name: str | None = None,
                 output_file: str = "result.json",
                 plugins: Sequence[VizPluginBase | str] | None = None) -> None:
        super().__init__(tracer_entries)

        # Members of C Tracer object
        self.verbose = verbose
        self.max_stack_depth = max_stack_depth
        self.ignore_c_function = ignore_c_function
        self.ignore_frozen = ignore_frozen
        self.log_func_args = log_func_args
        self.log_func_retval = log_func_retval
        self.log_async = log_async
        self.log_gc = log_gc
        self.log_print = log_print
        self.trace_self = trace_self
        self.lib_file_path = os.path.dirname(sys._getframe().f_code.co_filename)
        self.process_name = process_name
        self.min_duration = min_duration

        if include_files is None:
            self.include_files = include_files
        else:
            self.include_files = include_files[:] + [os.path.abspath(f) for f in include_files if not f.startswith("/")]

        if exclude_files is None:
            self.exclude_files = exclude_files
        else:
            self.exclude_files = exclude_files[:] + [os.path.abspath(f) for f in exclude_files if not f.startswith("/")]

        # Members of VizTracer object
        self.pid_suffix = pid_suffix
        self.file_info = file_info
        self.log_sparse = log_sparse
        self.log_audit = log_audit
        self.log_torch = log_torch
        self.ignore_multiprocess = ignore_multiprocess
        self.torch_profile = None
        self.dump_raw = dump_raw
        self.sanitize_function_name = sanitize_function_name
        self.minimize_memory = minimize_memory
        self.report_endpoint = report_endpoint
        self.system_print = builtins.print

        if self.pid_suffix:
            output_file_parts = output_file.split(".")
            output_file_parts[-2] = output_file_parts[-2] + "_" + str(os.getpid())
            output_file = ".".join(output_file_parts)

        self.output_file = output_file

        # Members for the collected data
        self.enable = False
        self.parsed = False
        self.tracer_entries = tracer_entries
        self.data: dict[str, Any] = {}
        self.total_entries = 0
        self.gc_start_args: dict[str, int] = {}

        self._exiting = False
        if register_global:
            self.register_global()

        self.cwd = os.getcwd()

        self.log_func_with_objprint = log_func_with_objprint
        if log_func_with_objprint:
            import objprint  # type: ignore
            if log_func_repr:
                raise ValueError("log_func_repr and log_func_with_objprint can't be both set")
            log_func_repr = objprint.objstr
        self.log_func_repr = log_func_repr

        self._afterfork_cb: Callable | None = None
        self._afterfork_args: tuple = tuple()
        self._afterfork_kwargs: dict = {}

        self.report_socket: socket.socket | None = None
        self.report_server: ReportServer | None
        if self.report_endpoint is None:
            self.report_server = ReportServer(
                output_file=self.output_file,
                minimize_memory=self.minimize_memory,
                verbose=self.verbose
            )
            self.report_endpoint = self.report_server.endpoint
        else:
            self.report_server = None

        # load in plugins
        self.plugins = plugins
        self._plugin_manager = VizPluginManager(self, plugins)

        if log_torch:
            # To generate an import error if torch is not installed
            import torch  # type: ignore  # noqa: F401

    def __del__(self):
        if (report_socket := getattr(self, "report_socket", None)) is not None:
            report_socket.close()

        if not self.ignore_multiprocess:
            uninstall_all_hooks()

    def get_args(self) -> list[str]:
        args = []
        signature = inspect.signature(VizTracer)
        for name, param in signature.parameters.items():
            if (attr := getattr(self, name)) != param.default:
                if name == "verbose" and attr == 0:
                    args.append("--quiet")
                    continue

                if name in ("process_name",):
                    continue

                if isinstance(attr, bool):
                    if attr:
                        args.append(f"--{name}")
                elif isinstance(attr, (int, str)):
                    args.append(f"--{name}")
                    args.append(str(attr))
                elif isinstance(attr, list) and attr and all(isinstance(i, (int, str)) for i in attr):
                    args.append(f"--{name}")
                    for item in attr:
                        args.append(str(item))
        return args

    @property
    def pid_suffix(self) -> bool:
        return self.__pid_suffix

    @pid_suffix.setter
    def pid_suffix(self, pid_suffix: bool) -> None:
        if type(pid_suffix) is bool:
            self.__pid_suffix = pid_suffix
        else:
            raise ValueError(f"pid_suffix needs to be a boolean, not {pid_suffix}")

    @property
    def init_kwargs(self) -> dict:
        return {
            "tracer_entries": self.tracer_entries,
            "verbose": self.verbose,
            "output_file": self.output_file,
            "max_stack_depth": self.max_stack_depth,
            "exclude_files": self.exclude_files,
            "include_files": self.include_files,
            "ignore_c_function": self.ignore_c_function,
            "ignore_frozen": self.ignore_frozen,
            "log_func_retval": self.log_func_retval,
            "log_func_args": self.log_func_args,
            "log_print": self.log_print,
            "log_gc": self.log_gc,
            "log_sparse": self.log_sparse,
            "log_async": self.log_async,
            "log_audit": self.log_audit,
            "log_torch": self.log_torch,
            "pid_suffix": self.pid_suffix,
            "ignore_multiprocess": self.ignore_multiprocess,
            "report_endpoint": self.report_endpoint,
            "min_duration": self.min_duration,
            "dump_raw": self.dump_raw,
            "minimize_memory": self.minimize_memory,
        }

    def __enter__(self) -> "VizTracer":
        self.start()
        return self

    def __exit__(self, type, value, trace) -> None:
        self.stop()
        self.save()
        self.terminate()
        builtins.__dict__.pop("__viz_tracer__", None)

    @property
    def report_directory(self) -> str | None:
        if self.report_endpoint is not None:
            return self.report_endpoint.split(":", 2)[2]
        return None

    def connect_report_server(self) -> None:
        assert self.report_endpoint is not None
        if self.report_socket is not None:
            try:
                self.report_socket.close()
            except Exception:
                pass
        self.report_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        addr, port = self.report_endpoint.split(":")[:2]
        self.report_socket.connect((addr, int(port)))

    def register_global(self) -> None:
        builtins.__dict__["__viz_tracer__"] = self

    def install(self) -> None:
        if (sys.platform == "win32"
                or (sys.platform == "darwin" and "arm" in platform.processor())):
            print("remote install is not supported on this platform!")
            sys.exit(1)

        def signal_start(signum, frame):
            self.start()

        def signal_stop(signum, frame):
            self.stop()
            self.save()

        signal.signal(signal.SIGUSR1, signal_start)
        signal.signal(signal.SIGUSR2, signal_stop)

    def log_instant(self, name: str, args: Any = None, scope: Literal["g", "p", "t"] = "t", cond: bool = True) -> None:
        if cond:
            self.add_instant(name, args=args, scope=scope)

    def log_var(self, name: str, var: Any, cond: bool = True) -> None:
        if cond:
            if isinstance(var, (float, int)):
                self.add_counter(name, {"value": var})
            else:
                import objprint  # type: ignore
                self.add_instant(name, args={"object": objprint.objstr(var, color=False)}, scope="t")

    def log_event(self, event_name: str) -> VizEvent:
        call_frame = sys._getframe(1)
        return VizEvent(self, event_name, call_frame.f_code.co_filename, call_frame.f_lineno)

    def shield_ignore(self, func: Callable, *args, **kwargs):
        prev_ignore_stack = self.setignorestackcounter(0)
        res = func(*args, **kwargs)
        self.setignorestackcounter(prev_ignore_stack)
        return res

    def set_afterfork(self, callback: Callable, *args, **kwargs) -> None:
        self._afterfork_cb = callback
        self._afterfork_args = args
        self._afterfork_kwargs = kwargs

    def start(self) -> None:
        if not self.enable:
            self.parsed = False
            if self.log_torch:
                from torch.profiler import profile, supported_activities  # type: ignore
                self.torch_profile = profile(activities=supported_activities()).__enter__()
            if self.log_print:
                self.overload_print()
            if self.include_files is not None and self.exclude_files is not None:
                raise Exception("include_files and exclude_files can't be both specified!")

            if self.report_server is not None:
                self.report_server.start()

            if self.report_socket is None:
                self.connect_report_server()

            if not self.ignore_multiprocess:
                install_all_hooks(self)

            self._plugin_manager.event("pre-start")
            if not self.log_sparse:
                self.enable = True
                super().start()

    def stop(self, stop_option: str | None = None) -> None:
        if self.enable:
            if self.log_print:
                self.restore_print()
            if not self.log_sparse:
                self.enable = False
                super().stop(stop_option)
            if self.torch_profile is not None:
                self.torch_profile.__exit__(None, None, None)
            self._plugin_manager.event("post-stop")
            if not self.ignore_multiprocess:
                uninstall_all_hooks()

    def parse(self) -> int:
        # parse() is also performance sensitive. We could have a lot of entries
        # in buffer, so try not to add any overhead when parsing
        # We parse the buffer into Chrome Trace Event Format
        self.stop()
        if not self.parsed:
            self.data = {
                "traceEvents": self.load(),
                "viztracer_metadata": {
                    "version": __version__,
                    "overflow": False,
                },
            }
            sync_marker = self.get_sync_marker()
            if sync_marker is not None:
                self.data['viztracer_metadata']['sync_marker'] = sync_marker

            metadata_count = 0
            for d in self.data["traceEvents"]:
                if d["ph"] == "M":
                    metadata_count += 1
                else:
                    break
            self.total_entries = len(self.data["traceEvents"]) - metadata_count
            if self.total_entries == self.tracer_entries:
                self.data["viztracer_metadata"]["overflow"] = True
            self.parsed = True

        return self.total_entries

    def run(self, command: str, output_file: str | None = None) -> None:
        self.start()
        exec(command)
        self.stop()
        self.save(output_file)

    def save_report(
        self,
        output_file: str,
        file_info: bool | None = None,
        verbose: int | None = None
    ) -> None:
        if file_info is None:
            file_info = self.file_info

        if verbose is None:
            verbose = self.verbose

        if isinstance(output_file, str):
            output_file = os.path.abspath(output_file)
            if not os.path.isdir(os.path.dirname(output_file)):
                os.makedirs(os.path.dirname(output_file), exist_ok=True)

        # If there are plugins, we can't do dump raw because it will skip the data
        # manipulation phase
        # If we want to dump torch profile, we can't do dump raw either
        if not self._plugin_manager.has_plugin and not self.log_torch and self.dump_raw:
            self.dump(output_file, sanitize_function_name=self.sanitize_function_name)
        else:
            if not self.parsed:
                self.parse()

            self._plugin_manager.event("pre-save")

            if self.log_torch and self.torch_profile is not None:
                import tempfile
                with tempfile.NamedTemporaryFile(suffix=".json") as tmpfile:
                    self.torch_profile.export_chrome_trace(tmpfile.name)
                    rb = ReportBuilder([(tmpfile.name, {'type': 'torch', 'base_offset': self.get_base_time()}), self.data],
                                       0, minimize_memory=self.minimize_memory, base_time=self.get_base_time())
                    rb.save(output_file=output_file, file_info=file_info)
            else:
                rb = ReportBuilder(self.data, 0, minimize_memory=self.minimize_memory, base_time=self.get_base_time())
                rb.save(output_file=output_file, file_info=file_info)

    def save(
            self,
            output_file: str | None = None,
            file_info: bool | None = None,
            verbose: int | None = None) -> None:
        enabled = False

        if self.enable:
            enabled = True
            self.stop()

        if output_file is None:
            output_file = self.output_file

        if self.report_endpoint is not None:
            assert self.report_directory is not None
            if not os.path.exists(self.report_directory):
                # Report server report directory is gone, skip saving
                return
            tmp_output_file = unique_path(self.report_directory)
        else:
            tmp_output_file = output_file

        if isinstance(output_file, str):
            output_file = os.path.abspath(output_file)
            if not os.path.isdir(os.path.dirname(output_file)):
                os.makedirs(os.path.dirname(output_file), exist_ok=True)

        self.save_report(
            output_file=tmp_output_file,
            file_info=file_info,
            verbose=verbose
        )

        if self.report_socket is None:
            self.connect_report_server()

        assert self.report_socket is not None

        try:
            self.report_socket.sendall(f"{tmp_output_file}\n".encode("utf-8"))
            self.report_socket.close()
            self.report_socket = None
        except Exception:
            pass

        if self.report_server is not None:
            self.report_server.collect()
            self.report_server.save(output_file)

        if enabled:
            self.start()

    def fork_save(self, output_file: str | None = None) -> multiprocessing.Process:
        if multiprocessing.get_start_method() != "fork":
            raise RuntimeError("fork_save is only supported in fork start method")

        # Fix the current pid so it won't give new pid when parsing
        self.setpid()

        p = multiprocessing.Process(target=self.save_report, daemon=False,
                                    kwargs={"output_file": output_file})
        p.start()

        # Revert to the normal pid mode
        self.setpid(0)

        return p

    def terminate(self) -> None:
        self._plugin_manager.terminate()

    def register_exit(self) -> None:
        self.cwd = os.getcwd()

        def term_handler(sig, frame):
            # For multiprocessing.pool, it's possible we receive SIGTERM
            # in util._exit_function(), but before tracer.exit_routine()
            # executes. In this case, we can just let the exit finish
            if not frame_stack_has_func(frame, (self.exit_routine,
                                                multiprocessing.util._exit_function)):
                sys.exit(0)

        signal.signal(signal.SIGTERM, term_handler)

        from multiprocessing.util import Finalize  # type: ignore
        Finalize(self, self.exit_routine, exitpriority=-1)

    def exit_routine(self) -> None:
        self.stop(stop_option="flush_as_finish")
        if not self._exiting:
            self._exiting = True
            os.chdir(self.cwd)
            self.save()
            self.terminate()

    def enable_thread_tracing(self) -> None:
        if sys.version_info < (3, 12):
            sys.setprofile(self.threadtracefunc)

    def add_variable(self, name: str, var: Any, event: str = "instant") -> None:
        if self.enable:
            if event == "instant":
                self.add_instant(f"{name} = {repr(var)}", scope="p")
            elif event == "counter":
                if isinstance(var, (int, float)):
                    self.add_counter(name, {name: var})
                else:
                    raise ValueError(f"{name}({var}) is not a number")
            else:
                raise ValueError(f"{event} is not supported")

    def overload_print(self) -> None:
        self.system_print = builtins.print

        def new_print(*args, **kwargs):
            self.pause()
            file = io.StringIO()
            kwargs["file"] = file
            self.system_print(*args, **kwargs)
            self.add_instant(f"print - {file.getvalue()}")
            self.resume()
        builtins.print = new_print

    def restore_print(self) -> None:
        builtins.print = self.system_print

    def add_func_exec(self, name: str, val: Any, lineno: int) -> None:
        exec_line = f"({lineno}) {name} = {val}"
        curr_args = self.get_func_args()
        if not curr_args:
            self.add_func_args("exec_steps", [exec_line])
        else:
            if "exec_steps" in curr_args:
                curr_args["exec_steps"].append(exec_line)
            else:
                curr_args["exec_steps"] = [exec_line]

    @property
    def log_gc(self) -> bool:
        return self.__log_gc

    @log_gc.setter
    def log_gc(self, log_gc: bool) -> None:
        if isinstance(log_gc, bool):
            self.__log_gc = log_gc
            if log_gc:
                gc.callbacks.append(self.add_garbage_collection)
            elif self.add_garbage_collection in gc.callbacks:
                gc.callbacks.remove(self.add_garbage_collection)
        else:
            raise TypeError(f"log_gc needs to be True or False, not {log_gc}")

    def add_garbage_collection(self, phase: str, info: dict[str, Any]) -> None:
        if self.enable:
            if phase == "start":
                args = {
                    "collecting": 1,
                    "collected": 0,
                    "uncollectable": 0,
                }
                self.add_counter("garbage collection", args)
                self.gc_start_args = args
            if phase == "stop" and self.gc_start_args:
                self.gc_start_args["collected"] = info["collected"]
                self.gc_start_args["uncollectable"] = info["uncollectable"]
                self.gc_start_args = {}
                self.add_counter("garbage collection", {
                    "collecting": 0,
                    "collected": 0,
                    "uncollectable": 0,
                })


def get_tracer() -> VizTracer | None:
    return builtins.__dict__.get("__viz_tracer__", None)
