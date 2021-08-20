# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

import os
import multiprocessing
import builtins
import signal
import sys
from typing import Any, Callable, Dict, Optional, Sequence, Tuple, Union
from .tracer import _VizTracer
from .flamegraph import FlameGraph
from .report_builder import ReportBuilder
from .vizplugin import VizPluginBase, VizPluginManager
from .vizevent import VizEvent


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
                 vdb: bool = False,
                 pid_suffix: bool = False,
                 file_info: bool = True,
                 register_global: bool = True,
                 trace_self: bool = False,
                 min_duration: float = 0,
                 output_file: str = "result.json",
                 plugins: Sequence[Union[VizPluginBase, str]] = []):
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
            vdb=vdb,
            log_func_args=log_func_args,
            log_async=log_async,
            trace_self=trace_self,
            min_duration=min_duration
        )
        self._tracer: Any
        self.verbose = verbose
        self.pid_suffix = pid_suffix
        self.file_info = file_info
        self.output_file = output_file
        self.system_print = None
        self.log_sparse = log_sparse
        if register_global:
            self.register_global()

        self._afterfork_cb: Optional[Callable] = None
        self._afterfork_args: Tuple = tuple()
        self._afterfork_kwargs: Dict = {}

        # load in plugins
        self._plugin_manager = VizPluginManager(self, plugins)

    @property
    def pid_suffix(self) -> bool:
        return self.__pid_suffix

    @pid_suffix.setter
    def pid_suffix(self, pid_suffix: bool):
        if type(pid_suffix) is bool:
            self.__pid_suffix = pid_suffix
        else:
            raise ValueError("pid_suffix needs to be a boolean, not {}".format(pid_suffix))

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, type, value, trace):
        self.stop()
        if type is None:
            self.save()
        self.terminate()

    def register_global(self):
        builtins.__dict__["__viz_tracer__"] = self

    def install(self):
        if sys.platform == "win32":
            print("remote install is not supported on Windows!")
            exit(1)

        def signal_start(signum, frame):
            self.start()

        def signal_stop(signum, frame):
            self.stop()
            self.save()

        signal.signal(signal.SIGUSR1, signal_start)
        signal.signal(signal.SIGUSR2, signal_stop)

    def log_event(self, event_name: str) -> VizEvent:
        call_frame = sys._getframe(1)
        return VizEvent(self, event_name, call_frame.f_code.co_filename, call_frame.f_lineno)

    def set_afterfork(self, callback: Callable, *args, **kwargs):
        self._afterfork_cb = callback
        self._afterfork_args = args
        self._afterfork_kwargs = kwargs

    def start(self):
        if not self.enable:
            self._plugin_manager.event("pre-start")
            _VizTracer.start(self)

    def stop(self):
        if self.enable:
            _VizTracer.stop(self)
            self._plugin_manager.event("post-stop")

    def run(self, command: str, output_file: Optional[str] = None):
        self.start()
        exec(command)
        self.stop()
        self.save(output_file)

    def save(
            self,
            output_file: Optional[str] = None,
            save_flamegraph: bool = False,
            file_info: Optional[bool] = None,
            minimize_memory: bool = False,
            verbose: Optional[int] = None):
        if file_info is None:
            file_info = self.file_info
        enabled = False
        if self.enable:
            enabled = True
            self.stop()
        if not self.parsed:
            self.parse()
        if output_file is None:
            output_file = self.output_file
        if verbose is None:
            verbose = self.verbose
        if self.pid_suffix:
            output_file_parts = output_file.split(".")
            output_file_parts[-2] = output_file_parts[-2] + "_" + str(os.getpid())
            output_file = ".".join(output_file_parts)

        self._plugin_manager.event("pre-save")

        if isinstance(output_file, str):
            output_file = os.path.abspath(output_file)
            if not os.path.isdir(os.path.dirname(output_file)):
                os.makedirs(os.path.dirname(output_file), exist_ok=True)

        rb = ReportBuilder(self.data, verbose, minimize_memory=minimize_memory)
        rb.save(output_file=output_file, file_info=file_info)

        if save_flamegraph:
            self.save_flamegraph(".".join(output_file.split(".")[:-1]) + "_flamegraph.html")

        if enabled:
            self.start()

    def fork_save(self, output_file: Optional[str] = None, save_flamegraph: bool = False):
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
                                    kwargs={"output_file": output_file, "save_flamegraph": save_flamegraph})
        p.start()

        if multiprocessing.get_start_method() != "fork":
            self._tracer = tracer
        else:
            # Revert to the normal pid mode
            self._tracer.setpid(0)

        return p

    def save_flamegraph(self, output_file: Optional[str] = None):
        flamegraph = FlameGraph(self.data)
        if output_file is None:
            name_list = self.output_file.split(".")
            output_file = ".".join(name_list[:-1]) + "_flamegraph.html"
        flamegraph.save(output_file)

    def terminate(self):
        self._plugin_manager.terminate()
