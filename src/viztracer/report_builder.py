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
    def __init__(self, data, verbose=1, align=False, minimize_memory=False):
        self.verbose = verbose
        self.combined_json = None
        self.entry_number_threshold = 4000000
        self.align = align
        self.minimize_memory = minimize_memory
        if type(data) is list:
            self.jsons = [get_json(j) for j in data]
        else:
            self.jsons = [get_json(data)]

    def combine_json(self):
        if self.combined_json:
            return 0
        if not self.jsons:
            raise ValueError("Can't get report of nothing")
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

    def prepare_json(self, file_info=True, display_time_unit="us"):
        # This will prepare self.combined_json to be ready to output
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

    def generate_report(self, output_file, output_format, file_info=True):
        sub = {}
        if output_format == "html":
            self.prepare_json(file_info=file_info, display_time_unit="ns")
            with open(os.path.join(os.path.dirname(__file__), "html/trace_viewer_embedder.html"), encoding="utf-8") as f:
                tmpl = f.read()
            with open(os.path.join(os.path.dirname(__file__), "html/trace_viewer_full.html"), encoding="utf-8") as f:
                sub["trace_viewer_full"] = f.read()
            if json.__name__ == "orjson":
                sub["json_data"] = json.dumps(self.combined_json).decode("utf-8").replace("</script>", "<\\/script>")
            else:
                sub["json_data"] = json.dumps(self.combined_json).replace("</script>", "<\\/script>")
            output_file.write(Template(tmpl).substitute(sub))
        elif output_format == "json":
            self.prepare_json(file_info=file_info, display_time_unit="us")
            if json.__name__ == "orjson":
                output_file.write(json.dumps(self.combined_json).decode("utf-8"))
            else:
                if self.minimize_memory:
                    json.dump(self.combined_json, output_file)
                else:
                    output_file.write(json.dumps(self.combined_json))

    def save(self, output_file="result.html", file_info=True):
        if self.verbose > 0:
            print("==================================================")
            print("== Starting from version 0.13.0, VizTracer will ==")
            print("== use json as the default report file. You can ==")
            print('== generate HTML report with "-o result.html"   ==')
            print("==================================================")

        if isinstance(output_file, io.TextIOBase):
            self.generate_report(output_file, output_format="json", file_info=file_info)
        else:
            file_type = output_file.split(".")[-1]

            if file_type == "html":
                with open(output_file, "w", encoding="utf-8") as f:
                    self.generate_report(f, output_format="html", file_info=file_info)
            elif file_type == "json":
                with open(output_file, "w", encoding="utf-8") as f:
                    self.generate_report(f, output_format="json", file_info=file_info)
            elif file_type == "gz":
                with gzip.open(output_file, "wt") as f:
                    self.generate_report(f, output_format="json", file_info=file_info)
            else:
                raise Exception("Only html, json and gz are supported")

        if self.verbose > 0 and isinstance(output_file, str):
            print("Saving report to {} ...".format(os.path.abspath(output_file)))
            print('Use', end=" ")
            color_print("OKGREEN", '"vizviewer <your_report>"', end=" ")
            print('to open the report')
