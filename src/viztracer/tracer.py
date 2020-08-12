# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/codesnap/blob/master/NOTICE.txt

import sys
import os
import time
try:
    import orjson as json
except ImportError:
    import json
from string import Template
from .util import ProgressBar
import viztracer.snaptrace as snaptrace


class _VizTracer:
    def __init__(self, tracer="python", max_stack_depth=-1, include_files=None, exclude_files=None):
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
    
    @property
    def include_files(self):
        return self.__include_files

    @include_files.setter
    def include_files(self, include_files):
        if include_files == None:
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
        if exclude_files == None:
            self.__exclude_files = None
        elif type(exclude_files) == list:
            if exclude_files:
                self.__exclude_files = [os.path.abspath(f) for f in exclude_files]
            else:
                self.__exclude_files = None
        else:
            raise Exception("exclude_files has to be a list")

    def start(self):
        self.enable = True
        self.parsed = False
        if self.tracer == "python":
            self.curr_stack_depth = 0
            sys.setprofile(self.tracefunc)
        elif self.tracer == "c":
            if self.include_files is not None and self.exclude_files is not None:
                raise Exception("include_files and exclude_files can't be both specified!")
            snaptrace.config(
                max_stack_depth=self.max_stack_depth,
                include_files=self.include_files,
                exclude_files=self.exclude_files
            )
            snaptrace.start()

    def stop(self):
        self.enable = False
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

    def parse(self):
        # parse() is also performance sensitive. We could have a lot of entries 
        # in buffer, so try not to add any overhead when parsing
        # We parse the buffer into Chrome Trace Event Format
        total_entries = 0
        pid = os.getpid()
        self.stop()
        if not self.parsed:
            if self.tracer == "python":
                buffer_size = len(self.buffer)
                pbar = ProgressBar("Parsing data")
                buffer_count = 1
                for data in self.buffer:
                    if self.verbose > 0:
                        pbar.update(float(buffer_count) / buffer_size)

                    if data[0] == "entry":
                        ph = "B"
                    elif data[0] == "exit":
                        ph = "E"
                    else:
                        raise Exception("Unexpected data type")
                    # convert seconds to micro seconds
                    event = {
                        "name": data[1],
                        "cat": "FEE",
                        "ph": ph,
                        "pid": pid,
                        "tid": 1,
                        "ts": data[2] * 1000000
                    }
                    self.data.append(event)
                    total_entries += 1
                    buffer_count += 1
                self.buffer = []
            elif self.tracer == "c":
                buffer = snaptrace.load()
                buffer_size = len(buffer)
                pbar = ProgressBar("Parsing data")
                buffer_count = 1
                for data in buffer:
                    if self.verbose > 0:
                        pbar.update(float(buffer_count) / buffer_size)
                    # [type, ts, file_name, class_name, func_name]
                    # type is an integer, 0 for entry and 3 for exit
                    # ts is count of nano seconds
                    # class_name could be None
                    if data[3]:
                        name = ".".join([data[2], data[3], data[4]])
                    else:
                        name = ".".join([data[2], data[4]])

                    if data[0] == 0:
                        ph = "B"
                    elif data[0] == 3:
                        ph = "E"
                    else:
                        raise Exception("Unexpected data type")
                    
                    event = {
                        "name": name,
                        "cat": "FEE",
                        "ph": ph,
                        "pid": pid,
                        "tid": 1,
                        "ts": data[1] / 1000
                    }
                    self.data.append(event)
                    total_entries += 1
                    buffer_count += 1
            self.parsed = True
        if self.enable:
            self.start()

        return total_entries

    def generate_report(self):
        sub = {}
        with open(os.path.join(os.path.dirname(__file__), "html/trace_viewer_embedder.html")) as f:
            tmpl = f.read()
        with open(os.path.join(os.path.dirname(__file__), "html/trace_viewer_full.html")) as f:
            sub["trace_viewer_full"] = f.read()
        sub["json_data"] = self.generate_json()

        return Template(tmpl).substitute(sub)

    def generate_json(self):
        if self.verbose > 0:
            print("Dumping trace data to json")
        if json.__name__ == "orjson":
            return json.dumps(self.data).decode("utf8")
        else:
            return json.dumps(self.data)
