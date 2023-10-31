# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

import builtins
import gc
import os
import sys
from io import StringIO
from typing import Any, Dict, Optional, Sequence, Union

import viztracer.snaptrace as snaptrace  # type: ignore

from . import __version__


class _VizTracer:
    def __init__(
            self,
            tracer_entries: int = 1000000,
            max_stack_depth: int = -1,
            include_files: Optional[Sequence[str]] = None,
            exclude_files: Optional[Sequence[str]] = None,
            ignore_c_function: bool = False,
            ignore_frozen: bool = False,
            log_func_retval: bool = False,
            log_func_args: bool = False,
            log_print: bool = False,
            log_gc: bool = False,
            log_async: bool = False,
            trace_self: bool = False,
            min_duration: float = 0) -> None:
        self.initialized = False
        self.enable = False
        self.parsed = False
        self._tracer = snaptrace.Tracer(tracer_entries)
        self.tracer_entries = tracer_entries
        self.data: Dict[str, Any] = {}
        self.verbose = 0
        self.max_stack_depth = max_stack_depth
        self.curr_stack_depth = 0
        self.include_files = include_files
        self.exclude_files = exclude_files
        self.ignore_c_function = ignore_c_function
        self.ignore_frozen = ignore_frozen
        self.log_func_retval = log_func_retval
        self.log_func_args = log_func_args
        self.log_async = log_async
        self.min_duration = min_duration
        self.log_print = log_print
        self.log_gc = log_gc
        self.trace_self = trace_self
        self.system_print = builtins.print
        self.total_entries = 0
        self.gc_start_args: Dict[str, int] = {}
        self.initialized = True

    @property
    def max_stack_depth(self) -> int:
        return self.__max_stack_depth

    @max_stack_depth.setter
    def max_stack_depth(self, max_stack_depth: Union[str, int]) -> None:
        if isinstance(max_stack_depth, str):
            try:
                self.__max_stack_depth = int(max_stack_depth)
            except ValueError:
                raise ValueError(f"Error when trying to convert max_stack_depth {max_stack_depth} to integer.")
        elif isinstance(max_stack_depth, int):
            self.__max_stack_depth = max_stack_depth
        else:
            raise ValueError(f"Error when trying to convert max_stack_depth {max_stack_depth} to integer.")
        self.config()

    @property
    def include_files(self) -> Optional[Sequence[str]]:
        return self.__include_files

    @include_files.setter
    def include_files(self, include_files: Optional[Sequence[str]]) -> None:
        if include_files is None:
            self.__include_files = None
        elif isinstance(include_files, list):
            if include_files:
                self.__include_files = include_files[:] + [os.path.abspath(f) for f in include_files if not f.startswith("/")]
            else:
                self.__include_files = None
        else:
            raise ValueError("include_files has to be a list")
        self.config()

    @property
    def exclude_files(self) -> Optional[Sequence[str]]:
        return self.__exclude_files

    @exclude_files.setter
    def exclude_files(self, exclude_files: Optional[Sequence[str]]) -> None:
        if exclude_files is None:
            self.__exclude_files = None
        elif isinstance(exclude_files, list):
            if exclude_files:
                self.__exclude_files = exclude_files[:] + [os.path.abspath(f) for f in exclude_files if not f.startswith("/")]
            else:
                self.__exclude_files = None
        else:
            raise ValueError("exclude_files has to be a list")
        self.config()

    @property
    def ignore_c_function(self) -> bool:
        return self.__ignore_c_function

    @ignore_c_function.setter
    def ignore_c_function(self, ignore_c_function: bool) -> None:
        if isinstance(ignore_c_function, bool):
            self.__ignore_c_function = ignore_c_function
        else:
            raise ValueError(f"ignore_c_function needs to be True or False, not {ignore_c_function}")
        self.config()

    @property
    def ignore_frozen(self) -> bool:
        return self.__ignore_frozen

    @ignore_frozen.setter
    def ignore_frozen(self, ignore_frozen: bool) -> None:
        if isinstance(ignore_frozen, bool):
            self.__ignore_frozen = ignore_frozen
        else:
            raise ValueError(f"ignore_frozen needs to be True or False, not {ignore_frozen}")
        self.config()

    @property
    def log_func_retval(self) -> bool:
        return self.__log_func_retval

    @log_func_retval.setter
    def log_func_retval(self, log_func_retval: bool) -> None:
        if isinstance(log_func_retval, bool):
            self.__log_func_retval = log_func_retval
        else:
            raise ValueError(f"log_func_retval needs to be True or False, not {log_func_retval}")
        self.config()

    @property
    def log_async(self) -> bool:
        return self.__log_async

    @log_async.setter
    def log_async(self, log_async: bool) -> None:
        if isinstance(log_async, bool):
            self.__log_async = log_async
        else:
            raise ValueError(f"log_async needs to be True or False, not {log_async}")
        self.config()

    @property
    def log_print(self) -> bool:
        return self.__log_print

    @log_print.setter
    def log_print(self, log_print: bool) -> None:
        if isinstance(log_print, bool):
            self.__log_print = log_print
        else:
            raise ValueError(f"log_print needs to be True or False, not {log_print}")

    @property
    def log_func_args(self) -> bool:
        return self.__log_func_args

    @log_func_args.setter
    def log_func_args(self, log_func_args: bool) -> None:
        if isinstance(log_func_args, bool):
            self.__log_func_args = log_func_args
        else:
            raise ValueError(f"log_func_args needs to be True or False, not {log_func_args}")
        self.config()

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
            raise ValueError(f"log_gc needs to be True or False, not {log_gc}")

    @property
    def verbose(self) -> int:
        return self.__verbose

    @verbose.setter
    def verbose(self, verbose: Union[str, int]) -> None:
        if isinstance(verbose, str):
            try:
                self.__verbose = int(verbose)
            except ValueError:
                raise ValueError(f"Verbose needs to be an integer, not {verbose}")
        elif isinstance(verbose, int):
            self.__verbose = verbose
        else:
            raise ValueError(f"Verbose needs to be an integer, not {verbose}")
        self.config()

    @property
    def min_duration(self) -> float:
        return self.__min_duration

    @min_duration.setter
    def min_duration(self, min_duration: float):
        if isinstance(min_duration, int) or isinstance(min_duration, float):
            self.__min_duration = float(min_duration)
        else:
            raise ValueError(f"duration needs to be a float, not {min_duration}")
        self.config()

    def config(self) -> None:
        if not self.initialized:
            return

        cfg = {
            "verbose": self.verbose,
            "lib_file_path": os.path.dirname(os.path.realpath(__file__)),
            "max_stack_depth": self.max_stack_depth,
            "include_files": self.include_files,
            "exclude_files": self.exclude_files,
            "ignore_c_function": self.ignore_c_function,
            "ignore_frozen": self.ignore_frozen,
            "log_func_retval": self.log_func_retval,
            "log_func_args": self.log_func_args,
            "log_async": self.log_async,
            "trace_self": self.trace_self,
            "min_duration": self.min_duration,
        }

        self._tracer.config(**cfg)

    def start(self) -> None:
        self.enable = True
        self.parsed = False
        if self.log_print:
            self.overload_print()
        if self.include_files is not None and self.exclude_files is not None:
            raise Exception("include_files and exclude_files can't be both specified!")
        self.config()
        self._tracer.start()

    def stop(self) -> None:
        self.enable = False
        if self.log_print:
            self.restore_print()
        self._tracer.stop()

    def pause(self) -> None:
        if self.enable:
            self._tracer.pause()

    def resume(self) -> None:
        if self.enable:
            self._tracer.resume()

    def clear(self) -> None:
        self._tracer.clear()

    def cleanup(self) -> None:
        self._tracer.cleanup()

    def enable_thread_tracing(self) -> None:
        sys.setprofile(self._tracer.threadtracefunc)

    def getts(self) -> float:
        return self._tracer.getts()

    def setignorestackcounter(self, value) -> int:
        # +2 and -2 to compensate for two calls: the current one and the call in the next line
        return self._tracer.setignorestackcounter(value + 2) - 2

    def add_instant(self, name: str, args: Any = None, scope: str = "g") -> None:
        if self.enable:
            if scope not in ["g", "p", "t"]:
                print("Scope has to be one of g, p, t")
                return
            self._tracer.addinstant(name, args, scope)

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

    def add_counter(self, name: str, args: Dict[str, Any]) -> None:
        if self.enable:
            self._tracer.addcounter(name, args)

    def add_object(self, ph: str, obj_id: str, name: str, args: Optional[Dict[str, Any]] = None) -> None:
        if self.enable:
            self._tracer.addobject(ph, obj_id, name, args)

    def add_func_args(self, key: str, value: Any) -> None:
        if self.enable:
            self._tracer.addfunctionarg(key, value)

    def add_raw(self, raw: Dict[str, Any]) -> None:
        self._tracer.addraw(raw)

    def add_garbage_collection(self, phase: str, info: Dict[str, Any]) -> None:
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

    def add_func_exec(self, name: str, val: Any, lineno: int) -> None:
        exec_line = f"({lineno}) {name} = {val}"
        curr_args = self._tracer.getfunctionarg()
        if not curr_args:
            self._tracer.addfunctionarg("exec_steps", [exec_line])
        else:
            if "exec_steps" in curr_args:
                curr_args["exec_steps"].append(exec_line)
            else:
                curr_args["exec_steps"] = [exec_line]

    def _set_curr_stack_depth(self, stack_depth: int) -> None:
        self._tracer.setcurrstack(stack_depth)

    def parse(self) -> int:
        # parse() is also performance sensitive. We could have a lot of entries
        # in buffer, so try not to add any overhead when parsing
        # We parse the buffer into Chrome Trace Event Format
        self.stop()
        if not self.parsed:
            self.data = {
                "traceEvents": self._tracer.load(),
                "viztracer_metadata": {
                    "version": __version__,
                    "overflow": False,
                },
            }
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

    def dump(self, filename: str, sanitize_function_name: bool = False) -> None:
        self._tracer.dump(filename, sanitize_function_name)

    def overload_print(self) -> None:
        self.system_print = builtins.print

        def new_print(*args, **kwargs):
            self.pause()
            io = StringIO()
            kwargs["file"] = io
            self.system_print(*args, **kwargs)
            self.add_instant(f"print - {io.getvalue()}")
            self.resume()
        builtins.print = new_print

    def restore_print(self) -> None:
        builtins.print = self.system_print
