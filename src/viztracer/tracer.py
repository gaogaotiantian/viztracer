# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

import sys
import os
import time
import builtins
from io import StringIO
try:
    import orjson as json
except ImportError:
    import json
from string import Template
from .util import ProgressBar, size_fmt
import viztracer.snaptrace as snaptrace


class _VizTracer:
    def __init__(self,
                 tracer="c",
                 max_stack_depth=-1,
                 include_files=None,
                 exclude_files=None,
                 ignore_c_function=False,
                 log_print=False):
        self.buffer = []
        self.enable = False
        self.parsed = False
        self.tracer = tracer
        self.verbose = 0
        self.data = []
        self.max_stack_depth = max_stack_depth
        self.curr_stack_depth = 0
        self.include_files = include_files
        self.exclude_files = exclude_files
        self.ignore_c_function = ignore_c_function
        self.log_print = log_print
        self.system_print = builtins.print
        self.total_entries = 0

    @property
    def tracer(self):
        return self.__tracer

    @tracer.setter
    def tracer(self, tracer):
        if tracer.lower() in ["c", "python"]:
            self.__tracer = tracer.lower()
        else:
            raise Exception("tracer can only be c or python, not {}".format(tracer))

    @property
    def max_stack_depth(self):
        return self.__max_stack_depth

    @max_stack_depth.setter
    def max_stack_depth(self, max_stack_depth):
        try:
            self.__max_stack_depth = int(max_stack_depth)
        except Exception as e:
            print("Error when trying to convert max_stack_depth {} to integer.".format(max_stack_depth))
            raise e

    @property
    def include_files(self):
        return self.__include_files

    @include_files.setter
    def include_files(self, include_files):
        if include_files is None:
            self.__include_files = None
        elif type(include_files) == list:
            if include_files:
                self.__include_files = [os.path.abspath(f) for f in include_files]
            else:
                self.__include_files = None
        else:
            raise Exception("include_files has to be a list")

    @property
    def exclude_files(self):
        return self.__exclude_files

    @exclude_files.setter
    def exclude_files(self, exclude_files):
        if exclude_files is None:
            self.__exclude_files = None
        elif type(exclude_files) == list:
            if exclude_files:
                self.__exclude_files = [os.path.abspath(f) for f in exclude_files]
            else:
                self.__exclude_files = None
        else:
            raise Exception("exclude_files has to be a list")

    @property
    def ignore_c_function(self):
        return self.__ignore_c_function

    @ignore_c_function.setter
    def ignore_c_function(self, ignore_c_function):
        if type(ignore_c_function) is bool:
            self.__ignore_c_function = ignore_c_function
        else:
            raise Exception("ignore_c_function needs to be True or False, not {}".format(ignore_c_function))

    @property
    def log_print(self):
        return self.__log_print

    @log_print.setter
    def log_print(self, log_print):
        if type(log_print) is bool:
            self.__log_print = log_print
        else:
            raise Exception("log_print needs to be True or False, not {}".format(log_print))

    def start(self):
        self.enable = True
        self.parsed = False
        if self.log_print:
            self.overload_print()
        if self.tracer == "python":
            self.curr_stack_depth = 0
            sys.setprofile(self.tracefunc)
        elif self.tracer == "c":
            if self.include_files is not None and self.exclude_files is not None:
                raise Exception("include_files and exclude_files can't be both specified!")
            snaptrace.config(
                verbose=self.verbose,
                lib_file_path=os.path.dirname(os.path.realpath(__file__)),
                max_stack_depth=self.max_stack_depth,
                include_files=self.include_files,
                exclude_files=self.exclude_files,
                ignore_c_function=self.ignore_c_function
            )
            snaptrace.start()

    def stop(self):
        self.enable = False
        if self.log_print:
            self.restore_print()
        if self.tracer == "python":
            sys.setprofile(None)
        elif self.tracer == "c":
            snaptrace.stop()

    def clear(self):
        if self.tracer == "python":
            self.buffer = []
        elif self.tracer == "c":
            snaptrace.clear()

    def cleanup(self):
        if self.tracer == "c":
            snaptrace.cleanup()

    def tracefunc(self, frame, event, arg):
        if event == "call" or event == "return":
            if self.max_stack_depth >= 0:
                if event == "call":
                    self.curr_stack_depth += 1
                    if self.curr_stack_depth > self.max_stack_depth:
                        return
                elif event == "return":
                    self.curr_stack_depth = max(0, self.curr_stack_depth - 1)
                    if self.curr_stack_depth + 1 > self.max_stack_depth:
                        return

            if self.include_files:
                for f in self.include_files:
                    if frame.f_code.co_filename.startswith(f):
                        break
                else:
                    return

            if self.exclude_files:
                for f in self.exclude_files:
                    if frame.f_code.co_filename.startswith(f):
                        return

            f_locals = frame.f_locals
            if "self" in f_locals:
                if issubclass(f_locals["self"].__class__, self.__class__):
                    # If we are inside this class, ignore
                    return
                class_name = type(f_locals["self"]).__name__ + "."
            else:
                class_name = ""

            if event == "call":
                name = "{}.{}{}".format(frame.f_code.co_filename, class_name, frame.f_code.co_name)
                self.buffer.append(("entry", name, time.perf_counter()))
            elif event == "return":
                name = "{}.{}{}".format(frame.f_code.co_filename, class_name, frame.f_code.co_name)
                self.buffer.append(("exit", name, time.perf_counter()))

    def add_instant(self, name, args, scope="g"):
        if self.tracer == "c":
            if scope not in ["g", "p", "t"]:
                print("Scope has to be one of g, p, t")
                return
            snaptrace.addinstant(name, args, scope)

    def parse(self):
        # parse() is also performance sensitive. We could have a lot of entries
        # in buffer, so try not to add any overhead when parsing
        # We parse the buffer into Chrome Trace Event Format
        self.total_entries = 0
        pid = os.getpid()
        self.stop()
        if not self.parsed:
            if self.tracer == "python":
                buffer_size = len(self.buffer)
                pbar = ProgressBar("Parsing data")
                buffer_count = 1
                events = []
                for data in self.buffer:
                    if self.verbose > 0:
                        pbar.update(float(buffer_count) / buffer_size)

                    if data[0] == "entry":
                        ph = "B"
                    elif data[0] == "exit":
                        ph = "E"
                    else:
                        raise Exception("Unexpected data type")

                    if data[0] == "exit" and events[-1]["ph"] == "B" and data[1] == events[-1]["name"]:
                        events[-1]["ph"] = "X"
                        events[-1]["dur"] = data[2] * 1000000 - events[-1]["ts"]
                        continue
                    # convert seconds to micro seconds
                    event = {
                        "name": data[1],
                        "cat": "FEE",
                        "ph": ph,
                        "pid": pid,
                        "tid": 1,
                        "ts": data[2] * 1000000
                    }
                    events.append(event)
                    self.total_entries += 1
                    buffer_count += 1
                self.data = {
                    "traceEvents": events,
                }
                self.buffer = []
            elif self.tracer == "c":
                self.data = {
                    "traceEvents": snaptrace.load(),
                    "displayTimeUnit": "ns"
                }
                self.total_entries = len(self.data["traceEvents"])
            self.parsed = True
        if self.enable:
            self.start()

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
        sub = {}
        with open(os.path.join(os.path.dirname(__file__), "html/trace_viewer_embedder.html")) as f:
            tmpl = f.read()
        with open(os.path.join(os.path.dirname(__file__), "html/trace_viewer_full.html")) as f:
            sub["trace_viewer_full"] = f.read()
        sub["json_data"] = self.generate_json()
        if self.verbose > 0:
            print("Generating HTML report")

        return Template(tmpl).substitute(sub)

    def generate_json(self):
        if self.verbose > 0:
            print("Dumping trace data to json, total entries: {}, estimated json file size: {}".format(self.total_entries, size_fmt(120*self.total_entries)))
        if json.__name__ == "orjson":
            return json.dumps(self.data).decode("utf8")
        else:
            return json.dumps(self.data)
