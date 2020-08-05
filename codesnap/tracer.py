# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/codesnap/blob/master/NOTICE.txt

import sys
import time
import os
from .snaptree import SnapTree

class CodeSnapTracer:
    def __init__(self):
        self.buffer = []
        self.enable = False
        self.parsed = False
        self.snaptree = SnapTree()

    def start(self):
        self.enable = True
        self.parsed = False
        sys.setprofile(self.tracer)
    
    def stop(self):
        self.enable = False
        sys.setprofile(None)

    def tracer(self, frame, event, arg):
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
                name = "{}.{}{}".format(frame.f_globals['__name__'], class_name, frame.f_code.co_name)
                self.buffer.append(("entry", name, time.perf_counter()))
            elif event == "return":
                name = "{}.{}{}".format(frame.f_globals['__name__'], class_name, frame.f_code.co_name)
                self.buffer.append(("exit", name, time.perf_counter()))

    def parse(self):
        self.stop()
        if not self.parsed:
            for data in self.buffer:
                if data[0] == "entry":
                    self.snaptree.add_entry(data[1], data[2])
                elif data[0] == "exit":
                    self.snaptree.add_exit(data[1], data[2])
            self.buffer = []
            self.parsed = True
        if self.enable:
            self.start()

    def generate_report(self):
        return self.snaptree.generate_html_report()