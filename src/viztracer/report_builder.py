# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

from string import Template
import os
import io
try:
    import orjson as json
except ImportError:
    import json
from .util import size_fmt, color_print


def get_json(data):
    # This function will return a json object if data is already json object
    # or a opened file or a file path
    if type(data) is dict:
        # This is an object already
        return data
    elif isinstance(data, io.IOBase):
        return json.loads(data.read())
    elif type(data) is str:
        with open(data) as f:
            return json.loads(f.read())
    else:
        raise TypeError("Unexpected Type{}!", type(data))


class ReportBuilder:
    def __init__(self, data, verbose=1):
        self.verbose = verbose
        self.combined_json = None
        self.entry_number_threshold = 4000000
        if type(data) is list:
            self.jsons = [get_json(j) for j in data]
        else:
            self.jsons = [get_json(data)]

    def combine_json(self):
        if self.combined_json:
            return 0
        if not self.jsons:
            raise Exception("Can't get report of nothing")
        self.combined_json = self.jsons[0]
        if len(self.jsons) > 1:
            for one in self.jsons[1:]:
                if "traceEvents" in one:
                    self.combined_json["traceEvents"].extend(one["traceEvents"])

    def generate_json(self, allow_binary=False):
        self.combine_json()
        if self.verbose > 0:
            entries = len(self.combined_json["traceEvents"])
            print("Dumping trace data to json, total entries: {}, estimated json file size: {}"
                    .format(entries, size_fmt(120*entries)))
            if entries >= self.entry_number_threshold:
                print("")
                color_print("WARNING", "Large trace requires a lot of RAM and is slow to load.")
                color_print("WARNING", "    If you need faster loading time or smaller trace file, try a smaller tracer_entries or use filters")
                color_print("WARNING", "    use --quiet to shut me up")
                print("")

        if json.__name__ == "orjson":
            if allow_binary:
                return json.dumps(self.combined_json)
            else:
                return json.dumps(self.combined_json).decode("utf-8")
        else:
            return json.dumps(self.combined_json)

    def generate_report(self):
        sub = {}
        with open(os.path.join(os.path.dirname(__file__), "html/trace_viewer_embedder.html"), encoding="utf-8") as f:
            tmpl = f.read()
        with open(os.path.join(os.path.dirname(__file__), "html/trace_viewer_full.html"), encoding="utf-8") as f:
            sub["trace_viewer_full"] = f.read()
        sub["json_data"] = self.generate_json()

        if self.verbose > 0:
            print("Generating HTML report")

        return Template(tmpl).substitute(sub)

    def save(self, output_file="result.html"):
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(self.generate_report())
