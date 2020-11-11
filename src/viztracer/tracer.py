# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

import os
import builtins
import gc
from io import StringIO
from .util import color_print
from .report_builder import ReportBuilder
from . import __version__
import viztracer.snaptrace as snaptrace


class _VizTracer:
    def __init__(self,
                 tracer_entries=1000000,
                 max_stack_depth=-1,
                 include_files=None,
                 exclude_files=None,
                 ignore_c_function=False,
                 ignore_non_file=False,
                 log_return_value=False,
                 log_function_args=False,
                 log_print=False,
                 log_gc=False,
                 novdb=False):
        self.buffer = []
        self.enable = False
        self.parsed = False
        self._tracer = snaptrace.Tracer(tracer_entries)
        self.tracer_entries = tracer_entries
        self.verbose = 0
        self.data = []
        self.max_stack_depth = max_stack_depth
        self.curr_stack_depth = 0
        self.include_files = include_files
        self.exclude_files = exclude_files
        self.ignore_c_function = ignore_c_function
        self.ignore_non_file = ignore_non_file
        self.log_return_value = log_return_value
        self.log_print = log_print
        self.log_gc = log_gc
        self.novdb = novdb
        self.log_function_args = log_function_args
        self.system_print = builtins.print
        self.total_entries = 0
        self.counters = {}
        self.gc_start_args = {}

    @property
    def max_stack_depth(self):
        return self.__max_stack_depth

    @max_stack_depth.setter
    def max_stack_depth(self, max_stack_depth):
        if type(max_stack_depth) is str:
            try:
                self.__max_stack_depth = int(max_stack_depth)
            except ValueError:
                raise ValueError("Error when trying to convert max_stack_depth {} to integer.".format(max_stack_depth))
        elif type(max_stack_depth) is int:
            self.__max_stack_depth = max_stack_depth
        else:
            raise ValueError("Error when trying to convert max_stack_depth {} to integer.".format(max_stack_depth))

    @property
    def include_files(self):
        return self.__include_files

    @include_files.setter
    def include_files(self, include_files):
        if include_files is None:
            self.__include_files = None
        elif type(include_files) == list:
            if include_files:
                self.__include_files = include_files[:] + [os.path.abspath(f) for f in include_files if not f.startswith("/")]
            else:
                self.__include_files = None
        else:
            raise ValueError("include_files has to be a list")

    @property
    def exclude_files(self):
        return self.__exclude_files

    @exclude_files.setter
    def exclude_files(self, exclude_files):
        if exclude_files is None:
            self.__exclude_files = None
        elif type(exclude_files) == list:
            if exclude_files:
                self.__exclude_files = exclude_files[:] + [os.path.abspath(f) for f in exclude_files if not f.startswith("/")]
            else:
                self.__exclude_files = None
        else:
            raise ValueError("exclude_files has to be a list")

    @property
    def ignore_c_function(self):
        return self.__ignore_c_function

    @ignore_c_function.setter
    def ignore_c_function(self, ignore_c_function):
        if type(ignore_c_function) is bool:
            self.__ignore_c_function = ignore_c_function
        else:
            raise ValueError("ignore_c_function needs to be True or False, not {}".format(ignore_c_function))

    @property
    def log_return_value(self):
        return self.__log_return_value

    @log_return_value.setter
    def log_return_value(self, log_return_value):
        if type(log_return_value) is bool:
            self.__log_return_value = log_return_value
        else:
            raise ValueError("log_return_value needs to be True or False, not {}".format(log_return_value))

    @property
    def log_print(self):
        return self.__log_print

    @log_print.setter
    def log_print(self, log_print):
        if type(log_print) is bool:
            self.__log_print = log_print
        else:
            raise ValueError("log_print needs to be True or False, not {}".format(log_print))

    @property
    def log_function_args(self):
        return self.__log_function_args

    @log_function_args.setter
    def log_function_args(self, log_function_args):
        if type(log_function_args) is bool:
            self.__log_function_args = log_function_args
        else:
            raise ValueError("log_function_args needs to be True or False, not {}".format(log_function_args))

    @property
    def log_gc(self):
        return self.__log_gc

    @log_gc.setter
    def log_gc(self, log_gc):
        if type(log_gc) is bool:
            self.__log_gc = log_gc
            if log_gc:
                gc.callbacks.append(self.add_garbage_collection)
            elif self.add_garbage_collection in gc.callbacks:
                gc.callbacks.remove(self.add_garbage_collection)
        else:
            raise ValueError("log_gc needs to be True or False, not {}".format(log_gc))

    @property
    def novdb(self):
        return self.__novdb

    @novdb.setter
    def novdb(self, novdb):
        if type(novdb) is bool:
            self.__novdb = novdb
        else:
            raise ValueError("novdb needs to be True or False, not {}".format(novdb))

    def start(self):
        self.enable = True
        self.parsed = False
        if self.log_print:
            self.overload_print()
        if self.include_files is not None and self.exclude_files is not None:
            raise Exception("include_files and exclude_files can't be both specified!")
        self._tracer.config(
            verbose=self.verbose,
            lib_file_path=os.path.dirname(os.path.realpath(__file__)),
            max_stack_depth=self.max_stack_depth,
            include_files=self.include_files,
            exclude_files=self.exclude_files,
            ignore_c_function=self.ignore_c_function,
            ignore_non_file=self.ignore_non_file,
            log_return_value=self.log_return_value,
            novdb=self.novdb,
            log_function_args=self.log_function_args
        )
        self._tracer.start()

    def stop(self):
        self.enable = False
        if self.log_print:
            self.restore_print()
        self._tracer.stop()

    def pause(self):
        if self.enable:
            self._tracer.pause()

    def resume(self):
        if self.enable:
            self._tracer.resume()

    def clear(self):
        self._tracer.clear()

    def cleanup(self):
        self._tracer.cleanup()

    def add_instant(self, name, args, scope="g"):
        if self.enable:
            if scope not in ["g", "p", "t"]:
                print("Scope has to be one of g, p, t")
                return
            self._tracer.addinstant(name, args, scope)

    def add_variable(self, name, var, event="instant"):
        if self.enable:
            if event == "instant":
                self.add_instant(name, {"value": repr(var)}, scope="p")
            elif event == "counter":
                if type(var) is int or type(var) is float:
                    self.add_counter(name, {name: var})
                else:
                    raise ValueError("{}({}) is not a number".format(name, var))
            else:
                raise ValueError("{} is not supported".format(event))

    def add_counter(self, name, args):
        if self.enable:
            self._tracer.addcounter(name, args)

    def add_object(self, ph, obj_id, name, args=None):
        if self.enable:
            self._tracer.addobject(ph, obj_id, name, args)

    def add_functionarg(self, key, value):
        if self.enable:
            self._tracer.addfunctionarg(key, value)

    def add_garbage_collection(self, phase, info):
        if self.enable:
            if phase == "start":
                args = {
                    "collecting": 1,
                    "collected": 0,
                    "uncollectable": 0
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
                    "uncollectable": 0
                })

    def add_func_exec(self, name, val, lineno):
        exec_line = "({}) {} = {}".format(lineno, name, val)
        curr_args = self._tracer.getfunctionarg()
        if not curr_args:
            self._tracer.addfunctionarg("exec_steps", [exec_line])
        else:
            if "exec_steps" in curr_args:
                curr_args["exec_steps"].append(exec_line)
            else:
                curr_args["exec_steps"] = [exec_line]

    def parse(self):
        # parse() is also performance sensitive. We could have a lot of entries
        # in buffer, so try not to add any overhead when parsing
        # We parse the buffer into Chrome Trace Event Format
        self.stop()
        if not self.parsed:
            self.data = {
                "traceEvents": self._tracer.load(),
                "displayTimeUnit": "ns",
                "viztracer_metadata": {
                    "version": __version__
                }
            }
            self.total_entries = len(self.data["traceEvents"])
            if self.total_entries == self.tracer_entries and self.verbose > 0:
                print("")
                color_print("WARNING", "Circular buffer is full, you lost some early data, but you still have the most recent data.")
                color_print("WARNING", "    If you need more buffer, use \"viztracer --tracer_entries <entry_number>(current: {})\"".format(self.tracer_entries))
                color_print("WARNING", "    Or, you can try the filter options to filter out some data you don't need")
                color_print("WARNING", "    use --quiet to shut me up")
                print("")
            self.parsed = True

        return self.total_entries

    def overload_print(self):
        self.system_print = builtins.print

        def new_print(*args, **kwargs):
            self.pause()
            io = StringIO()
            kwargs["file"] = io
            self.system_print(*args, **kwargs)
            self.add_instant("print", {"string": io.getvalue()})
            self.resume()
        builtins.print = new_print

    def restore_print(self):
        builtins.print = self.system_print

    def generate_report(self):
        builder = ReportBuilder(self.data, verbose=self.verbose)
        return builder.generate_report(file_info=True)

    def generate_json(self, allow_binary=False, file_info=False):
        builder = ReportBuilder(self.data, verbose=self.verbose)
        return builder.generate_json(allow_binary, file_info=file_info)
