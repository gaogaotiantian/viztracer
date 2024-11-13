# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

import os
import sys
from typing import Any, Dict, Optional, Sequence, Union

import viztracer.snaptrace as snaptrace  # type: ignore


class _VizTracer(snaptrace.Tracer):
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
            min_duration: float = 0,
            process_name: Optional[str] = None) -> None:
        super().__init__(tracer_entries)
        self.initialized = False
        self.enable = False
        self.parsed = False
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
        self.total_entries = 0
        self.gc_start_args: Dict[str, int] = {}
        self.initialized = True
        self.process_name = process_name

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
            # We use the filename from code object to ensure the consistency when
            # comparing to the filename of other code objects on Windows
            "lib_file_path": os.path.dirname(sys._getframe().f_code.co_filename),
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
            "process_name": self.process_name,
        }

        super()._config(**cfg)
