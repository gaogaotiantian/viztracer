# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/codesnap/blob/master/NOTICE.txt

import sys
import time
import json
from .snaptree import SnapTree
import codesnap.snaptrace as snaptrace


class CodeSnapTracer:
    def __init__(self, tracer="python"):
        self.buffer = []
        self.enable = False
        self.parsed = False
        self.snaptree = SnapTree()
        self.tracer = tracer

    def start(self):
        self.enable = True
        self.parsed = False
        if self.tracer == "python":
            sys.setprofile(self.tracefunc)
        elif self.tracer == "c":
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
        total_entries = 0
        self.stop()
        if not self.parsed:
            if self.tracer == "python":
                for data in self.buffer:
                    # convert seconds to nano seconds
                    if data[0] == "entry":
                        self.snaptree.add_entry(data[1], data[2] * 1000000000)
                    elif data[0] == "exit":
                        self.snaptree.add_exit(data[1], data[2] * 1000000000)
                    else:
                        raise Exception("Unexpected data type")
                    total_entries += 1
                self.buffer = []
            elif self.tracer == "c":
                buffer = snaptrace.load()
                for data in buffer:
                    # [type, ts, file_name, class_name, func_name]
                    # type is an integer, 0 for entry and 3 for exit
                    # ts is count of nano seconds
                    # class_name could be None
                    if data[3]:
                        name = ".".join([data[2], data[3], data[4]])
                    else:
                        name = ".".join([data[2], data[4]])
                    if data[0] == 0:
                        self.snaptree.add_entry(name, data[1])
                    elif data[0] == 3:
                        self.snaptree.add_exit(name, data[1])
                    else:
                        raise Exception("Unexpected data type")
                    total_entries += 1
            self.parsed = True
        if self.enable:
            self.start()

        return total_entries

    def generate_report(self):
        return self.snaptree.generate_html_report()

    def generate_json(self):
        return json.dumps(self.snaptree.get_json())
