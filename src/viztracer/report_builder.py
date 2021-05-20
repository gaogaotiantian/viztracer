# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

from string import Template
import os
import io
import re
import gzip
try:
    import orjson as json
except ImportError:
    import json
from .util import color_print


def get_json(data):
    # This function will return a json object if data is already json object
    # or a opened file or a file path
    if type(data) is dict:
        # This is an object already
        return data
    elif isinstance(data, io.IOBase):
        json_str = data.read()
    elif type(data) is str:
        with open(data, encoding="utf-8") as f:
            json_str = f.read()
    else:
        raise TypeError("Unexpected Type{}!", type(data))

    try:
        return json.loads(json_str)
    except Exception as e:
        print("Unable to decode {}".format(data))
        raise e


class ReportBuilder:
    def __init__(self, data, verbose=1, align=False):
        self.verbose = verbose
        self.combined_json = None
        self.entry_number_threshold = 4000000
        self.align = align
        if type(data) is list:
            self.jsons = [get_json(j) for j in data]
        else:
            self.jsons = [get_json(data)]

    def combine_json(self):
        if self.combined_json:
            return 0
        if not self.jsons:
            raise Exception("Can't get report of nothing")
        if self.align:
            for one in self.jsons:
                self.align_events(one["traceEvents"])
        self.combined_json = self.jsons[0]
        for one in self.jsons[1:]:
            if "traceEvents" in one:
                self.combined_json["traceEvents"].extend(one["traceEvents"])

    def align_events(self, original_events):
        """
        Apply an offset to all the trace events, making the start timestamp 0
        This is useful when comparing multiple runs of the same script

        This function will change the timestamp in place, and return the original list
        """
        offset_ts = min((event["ts"] for event in original_events if "ts" in event))
        for event in original_events:
            if "ts" in event:
                event["ts"] -= offset_ts
        return original_events

    def generate_json(self, allow_binary=False, file_info=True, display_time_unit="us"):
        self.combine_json()
        if self.verbose > 0:
            entries = len(self.combined_json["traceEvents"])
            print(f"Dumping trace data, total entries: {entries}")

        self.combined_json["displayTimeUnit"] = display_time_unit

        if file_info:
            self.combined_json["file_info"] = {"files": {}, "functions": {}}
            pattern = re.compile(r".*\((.*):([0-9]*)\)")
            file_dict = self.combined_json["file_info"]["files"]
            func_dict = self.combined_json["file_info"]["functions"]
            for event in self.combined_json["traceEvents"]:
                if event["ph"] == 'X':
                    if event["name"] not in func_dict:
                        try:
                            m = pattern.match(event["name"])
                            file_name = m.group(1)
                            lineno = int(m.group(2))
                            if file_name not in file_dict:
                                with open(file_name, "r", encoding="utf-8") as f:
                                    content = f.read()
                                    file_dict[file_name] = [content, content.count("\n")]
                            func_dict[event["name"]] = [file_name, lineno]
                        except Exception:
                            pass

        if json.__name__ == "orjson":
            if allow_binary:
                return json.dumps(self.combined_json)
            else:
                return json.dumps(self.combined_json).decode("utf-8")
        else:
            return json.dumps(self.combined_json)

    def generate_report(self, file_info=True):
        sub = {}
        with open(os.path.join(os.path.dirname(__file__), "html/trace_viewer_embedder.html"), encoding="utf-8") as f:
            tmpl = f.read()
        with open(os.path.join(os.path.dirname(__file__), "html/trace_viewer_full.html"), encoding="utf-8") as f:
            sub["trace_viewer_full"] = f.read()
        sub["json_data"] = self.generate_json(file_info=file_info, display_time_unit="ns")
        sub["json_data"] = sub["json_data"].replace("</script>", "<\\/script>")

        return Template(tmpl).substitute(sub)

    def save(self, output_file="result.html", file_info=True):
        file_type = output_file.split(".")[-1]

        if self.verbose > 0:
            print("==================================================")
            print("== Starting from version 0.13.0, VizTracer will ==")
            print("== use json as the default report file. You can ==")
            print('== generate HTML report with "-o result.html"   ==')
            print("==================================================")

        if file_type == "html":
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(self.generate_report(file_info=True))
        elif file_type == "json":
            data = self.generate_json(allow_binary=True, file_info=file_info)
            if type(data) is bytes:
                with open(output_file, "wb") as f:
                    f.write(data)
            else:
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(data)
        elif file_type == "gz":
            data = self.generate_json(allow_binary=True, file_info=file_info)
            if type(data) is not bytes:
                data = data.encode("utf-8")
            with gzip.open(output_file, "wb") as f:
                f.write(data)
        else:
            raise Exception("Only html, json and gz are supported")

        if self.verbose > 0:
            print("Saving report to {} ...".format(os.path.abspath(output_file)))
            print('Use', end=" ")
            color_print("OKGREEN", '"vizviewer <your_report>"', end=" ")
            print('to open the report')
