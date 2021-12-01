# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

import builtins
import multiprocessing
import objprint  # type: ignore
import os
import signal
import sys
from typing import Any, Callable, Dict, Optional, Sequence, Tuple, Union

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
                 vdb: bool = False,
                 pid_suffix: bool = False,
                 file_info: bool = True,
                 register_global: bool = True,
                 trace_self: bool = False,
                 min_duration: float = 0,
                 minimize_memory: bool = False,
                 dump_raw: bool = False,
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
        self.dump_raw = dump_raw
        self.minimize_memory = minimize_memory
        self._exiting = False
        if register_global:
            self.register_global()

        self.cwd = os.getcwd()

        self.viztmp = None

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
            "vdb": self.vdb,
            "pid_suffix": self.pid_suffix,
            "min_duration": self.min_duration,
            "dump_raw": self.dump_raw,
            "minimize_memory": self.minimize_memory
        }

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, type, value, trace):
        self.stop()
        self.save()
        self.terminate()

    def register_global(self):
        builtins.__dict__["__viz_tracer__"] = self

    def install(self):
        if sys.platform == "win32":
            print("remote install is not supported on Windows!")
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

    def log_var(self, name, var, cond: bool = True) -> None:
        if cond:
            if isinstance(var, (float, int)):
                self.add_counter(name, {"value": var})
            else:
                self.add_instant(name, args={"object": objprint.objstr(var, color=False)}, scope="t")

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
            file_info: Optional[bool] = None,
            verbose: Optional[int] = None):
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

        self._plugin_manager.event("pre-save")

        if self.dump_raw:
            self.dump(output_file)
        else:
            if not self.parsed:
                self.parse()

            rb = ReportBuilder(self.data, verbose, minimize_memory=self.minimize_memory)
            rb.save(output_file=output_file, file_info=file_info)

        if self.viztmp is not None and os.path.exists(self.viztmp):
            os.remove(self.viztmp)

        if enabled:
            self.start()

    def fork_save(self, output_file: Optional[str] = None):
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

    def label_file_to_write(self):
        output_file = self.output_file
        if self.pid_suffix:
            output_file_parts = output_file.split(".")
            output_file_parts[-2] = output_file_parts[-2] + "_" + str(os.getpid())
            output_file = ".".join(output_file_parts) + ".viztmp"

        with open(output_file, "w") as _:
            # create an empty file
            pass
        self.viztmp = output_file

    def terminate(self):
        self._plugin_manager.terminate()

    def register_exit(self):
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

    def exit_routine(self):
        # We need to avoid SIGTERM terminate our process when we dump data
        signal.signal(signal.SIGTERM, lambda sig, frame: 0)
        self.stop()
        if not self._exiting:
            self._exiting = True
            os.chdir(self.cwd)
            self.save()
            self.terminate()
