# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

import os
import builtins
from io import StringIO
from .util import color_print
from .report_builder import ReportBuilder
import viztracer.snaptrace as snaptrace


class _VizTracer:
    def __init__(self,
                 tracer_entries=1000000,
                 max_stack_depth=-1,
                 include_files=None,
                 exclude_files=None,
                 ignore_c_function=False,
                 log_return_value=False,
                 log_print=False):
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
        self.log_return_value = log_return_value
        self.log_print = log_print
        self.system_print = builtins.print
        self.total_entries = 0
        self.counters = {}

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
            log_return_value=self.log_return_value
        )
        self._tracer.start()

    def stop(self):
        self.enable = False
        if self.log_print:
            self.restore_print()
        self._tracer.stop()

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

    def add_counter(self, name, args):
        if self.enable:
            self._tracer.addcounter(name, args)

    def add_object(self, ph, obj_id, name, args=None):
        if self.enable:
            self._tracer.addobject(ph, obj_id, name, args)

    def add_functionarg(self, key, value):
        if self.enable:
            self._tracer.addfunctionarg(key, value)

    def parse(self):
        # parse() is also performance sensitive. We could have a lot of entries
        # in buffer, so try not to add any overhead when parsing
        # We parse the buffer into Chrome Trace Event Format
        self.stop()
        if not self.parsed:
            self.data = {
                "traceEvents": self._tracer.load(),
                "displayTimeUnit": "ns"
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
            snaptrace.pause()
            io = StringIO()
            kwargs["file"] = io
            self.system_print(*args, **kwargs)
            self.add_instant("print", {"string": io.getvalue()})
            snaptrace.resume()
        builtins.print = new_print

    def restore_print(self):
        builtins.print = self.system_print

    def generate_report(self):
        builder = ReportBuilder(self.data, verbose=self.verbose)
        return builder.generate_report()

    def generate_json(self, allow_binary=False):
        builder = ReportBuilder(self.data, verbose=self.verbose)
        return builder.generate_json(allow_binary)
