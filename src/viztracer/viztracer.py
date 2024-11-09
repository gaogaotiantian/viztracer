# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

import builtins
import multiprocessing
import os
import platform
import signal
import sys
from typing import Any, Callable, Dict, Optional, Sequence, Tuple, Union

import objprint  # type: ignore

from .report_builder import ReportBuilder
from .tracer import _VizTracer
from .vizevent import VizEvent
from .vizplugin import VizPluginBase, VizPluginManager


# This is the interface of the package. Almost all user should use this
# class for the functions
class VizTracer(_VizTracer):
    def __init__(self,
                 tracer_entries: int = 1000000,
                 verbose: int = 1,
                 max_stack_depth: int = -1,
                 include_files: Optional[Sequence[str]] = None,
                 exclude_files: Optional[Sequence[str]] = None,
                 ignore_c_function: bool = False,
                 ignore_frozen: bool = False,
                 log_func_retval: bool = False,
                 log_func_args: bool = False,
                 log_print: bool = False,
                 log_gc: bool = False,
                 log_sparse: bool = False,
                 log_async: bool = False,
                 log_torch: bool = False,
                 log_audit: Optional[Sequence[str]] = None,
                 pid_suffix: bool = False,
                 file_info: bool = True,
                 register_global: bool = True,
                 trace_self: bool = False,
                 min_duration: float = 0,
                 minimize_memory: bool = False,
                 dump_raw: bool = False,
                 sanitize_function_name: bool = False,
                 process_name: Optional[str] = None,
                 output_file: str = "result.json",
                 plugins: Sequence[Union[VizPluginBase, str]] = []) -> None:
        super().__init__(
            tracer_entries=tracer_entries,
            max_stack_depth=max_stack_depth,
            include_files=include_files,
            exclude_files=exclude_files,
            ignore_c_function=ignore_c_function,
            ignore_frozen=ignore_frozen,
            log_func_retval=log_func_retval,
            log_print=log_print,
            log_gc=log_gc,
            log_func_args=log_func_args,
            log_async=log_async,
            trace_self=trace_self,
            min_duration=min_duration,
            process_name=process_name,
        )
        self._tracer: Any
        self.verbose = verbose
        self.pid_suffix = pid_suffix
        self.file_info = file_info
        self.output_file = output_file
        self.system_print = None
        self.log_sparse = log_sparse
        self.log_audit = log_audit
        self.log_torch = log_torch
        self.torch_profile = None
        self.torch_offset = 0.0
        self.dump_raw = dump_raw
        self.sanitize_function_name = sanitize_function_name
        self.minimize_memory = minimize_memory
        self._exiting = False
        if register_global:
            self.register_global()

        self.cwd = os.getcwd()

        self.viztmp: Optional[str] = None

        self._afterfork_cb: Optional[Callable] = None
        self._afterfork_args: Tuple = tuple()
        self._afterfork_kwargs: Dict = {}

        # load in plugins
        self._plugin_manager = VizPluginManager(self, plugins)

        if self.log_torch:
            self.calibrate_torch_timer()

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
    def init_kwargs(self) -> Dict:
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
            "min_duration": self.min_duration,
            "dump_raw": self.dump_raw,
            "minimize_memory": self.minimize_memory,
        }

    def __enter__(self) -> "VizTracer":
        if not self.log_sparse:
            self.start()
        return self

    def __exit__(self, type, value, trace) -> None:
        if not self.log_sparse:
            self.stop()
        self.save()
        self.terminate()

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

    def log_instant(self, name: str, args: Any = None, scope: str = "t", cond: bool = True) -> None:
        if cond:
            self.add_instant(name, args=args, scope=scope)

    def log_var(self, name: str, var: Any, cond: bool = True) -> None:
        if cond:
            if isinstance(var, (float, int)):
                self.add_counter(name, {"value": var})
            else:
                self.add_instant(name, args={"object": objprint.objstr(var, color=False)}, scope="t")

    def log_event(self, event_name: str) -> VizEvent:
        call_frame = sys._getframe(1)
        return VizEvent(self, event_name, call_frame.f_code.co_filename, call_frame.f_lineno)

    def shield_ignore(self, func, *args, **kwargs):
        prev_ignore_stack = self.setignorestackcounter(0)
        res = func(*args, **kwargs)
        self.setignorestackcounter(prev_ignore_stack)
        return res

    def set_afterfork(self, callback: Callable, *args, **kwargs) -> None:
        self._afterfork_cb = callback
        self._afterfork_args = args
        self._afterfork_kwargs = kwargs

    def calibrate_torch_timer(self, force=False):
        if self.enable:
            raise RuntimeError("You can't calibrate torch timer while tracer is running")
        if self.torch_offset and not force:
            return
        import json
        import tempfile
        import torch  # type: ignore
        from torch.profiler import profile, supported_activities  # type: ignore
        verbose = self.verbose
        # Silent the tracer during calibration
        self.verbose = 0
        with profile(activities=supported_activities()) as prof:
            _VizTracer.start(self)
            for _ in range(20):
                torch.empty(100)
            _VizTracer.stop(self)
        with tempfile.NamedTemporaryFile(suffix=".json") as tmpfile:
            prof.export_chrome_trace(tmpfile.name)
            self.parse()
            torch_starts = []
            torch_ends = []
            viz_starts = []
            viz_ends = []
            min_offset = None
            max_offset = None
            with open(tmpfile.name, "r") as f:
                torch_data = json.load(f)
                for event in torch_data["traceEvents"]:
                    if event["ph"] == "X" and event["name"] == "aten::empty":
                        torch_starts.append(event["ts"])
                        torch_ends.append(event["ts"] + event["dur"])
            for event in self.data["traceEvents"]:
                if event["ph"] == "X" and event["name"] == "torch.empty":
                    viz_starts.append(event["ts"])
                    viz_ends.append(event["ts"] + event["dur"])
            if len(torch_starts) == 0 or len(viz_starts) == 0 or len(torch_starts) != len(viz_starts):
                raise RuntimeError("Torch timer calibration failed")  # pragma: no cover

            for i in range(len(torch_starts)):
                if min_offset is None or torch_starts[i] + min_offset < viz_starts[i]:
                    min_offset = viz_starts[i] - torch_starts[i]
                if max_offset is None or torch_ends[i] + max_offset > viz_ends[i]:
                    max_offset = viz_ends[i] - torch_ends[i]
            assert min_offset is not None and max_offset is not None
            self.torch_offset = (min_offset + max_offset) / 2
            self.clear()
        self.verbose = verbose

    def start(self) -> None:
        if not self.enable:
            self._plugin_manager.event("pre-start")
            if self.log_torch:
                try:
                    from torch.profiler import profile, supported_activities
                except ImportError:
                    raise ImportError("torch is not installed, please install it to use log_torch")
                self.torch_profile = profile(activities=supported_activities()).__enter__()
            _VizTracer.start(self)

    def stop(self, stop_option: Optional[str] = None) -> None:
        if self.enable:
            _VizTracer.stop(self, stop_option)
            if self.torch_profile is not None:
                self.torch_profile.__exit__(None, None, None)
            self._plugin_manager.event("post-stop")

    def run(self, command: str, output_file: Optional[str] = None) -> None:
        self.start()
        exec(command)
        self.stop()
        self.save(output_file)

    def save(
            self,
            output_file: Optional[str] = None,
            file_info: Optional[bool] = None,
            verbose: Optional[int] = None) -> None:
        if file_info is None:
            file_info = self.file_info
        enabled = False
        if output_file is None:
            output_file = self.output_file
        if verbose is None:
            verbose = self.verbose
        if self.pid_suffix:
            output_file_parts = output_file.split(".")
            output_file_parts[-2] = output_file_parts[-2] + "_" + str(os.getpid())
            output_file = ".".join(output_file_parts)

        if isinstance(output_file, str):
            output_file = os.path.abspath(output_file)
            if not os.path.isdir(os.path.dirname(output_file)):
                os.makedirs(os.path.dirname(output_file), exist_ok=True)

        if self.enable:
            enabled = True
            self.stop()

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
                    rb = ReportBuilder([(tmpfile.name, {'type': 'torch', 'offset': self.torch_offset}), self.data],
                                       verbose, minimize_memory=self.minimize_memory)
                    rb.save(output_file=output_file, file_info=file_info)
            else:
                rb = ReportBuilder(self.data, verbose, minimize_memory=self.minimize_memory)
                rb.save(output_file=output_file, file_info=file_info)

        if enabled:
            self.start()

    def fork_save(self, output_file: Optional[str] = None) -> multiprocessing.Process:
        if multiprocessing.get_start_method() != "fork":
            # You have to parse first if you are not forking, address space is not copied
            # Since it's not forking, we can't pickle tracer, just set it to None when
            # we spawn
            if not self.parsed:
                self.parse()
            tracer = self._tracer
            self._tracer = None
        else:
            # Fix the current pid so it won't give new pid when parsing
            self._tracer.setpid()

        p = multiprocessing.Process(target=self.save, daemon=False,
                                    kwargs={"output_file": output_file})
        p.start()

        if multiprocessing.get_start_method() != "fork":
            self._tracer = tracer
        else:
            # Revert to the normal pid mode
            self._tracer.setpid(0)

        return p

    def label_file_to_write(self) -> None:
        output_file = self.output_file
        if self.pid_suffix:
            output_file_parts = output_file.split(".")
            output_file_parts[-2] = output_file_parts[-2] + "_" + str(os.getpid())
            output_file = ".".join(output_file_parts) + ".viztmp"

        with open(output_file, "w") as _:
            # create an empty file
            pass
        self.viztmp = output_file

    def terminate(self) -> None:
        self._plugin_manager.terminate()

    def register_exit(self) -> None:
        self.cwd = os.getcwd()

        def term_handler(sig, frame):
            # For multiprocessing.pool, it's possible we receive SIGTERM
            # in util._exit_function(), but before tracer.exit_routine()
            # executes. In this case, sys.exit() or util._exit_function()
            # won't trigger trace collection. We have to explicitly run
            # exit_routine()
            # Notice that exit_rountine() won't be executed multiple times
            # as it was protected my self._exiting
            self.exit_routine()
            sys.exit(0)

        self.label_file_to_write()

        signal.signal(signal.SIGTERM, term_handler)

        from multiprocessing.util import Finalize  # type: ignore
        Finalize(self, self.exit_routine, exitpriority=-1)

    def exit_routine(self) -> None:
        # We need to avoid SIGTERM terminate our process when we dump data
        signal.signal(signal.SIGTERM, lambda sig, frame: 0)
        self.stop(stop_option="flush_as_finish")
        if not self._exiting:
            self._exiting = True
            os.chdir(self.cwd)
            try:
                self.save()
            finally:
                if self.viztmp is not None and os.path.exists(self.viztmp):
                    os.remove(self.viztmp)
            self.terminate()


def get_tracer() -> Optional[VizTracer]:
    return builtins.__dict__.get("__viz_tracer__", None)
