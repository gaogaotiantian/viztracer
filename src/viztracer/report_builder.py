# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

try:
    import orjson  # type: ignore
except ImportError:
    import json
import gzip
import os
import re
from string import Template
import sys
from typing import Any, Dict, List, Optional, Sequence, Union, TextIO

from .util import color_print


def get_json(data: Union[Dict, str]) -> Dict[str, Any]:
    # This function will return a json object if data is already json object
    # or a opened file or a file path
    if isinstance(data, dict):
        # This is an object already
        return data
    elif isinstance(data, str):
        with open(data, encoding="utf-8") as f:
            json_str = f.read()
    else:
        raise TypeError("Unexpected Type{}!", type(data))

    try:
        if "orjson" in sys.modules:
            return orjson.loads(json_str)
        else:
            return json.loads(json_str)
    except Exception as e:
        print("Unable to decode {}".format(data))
        raise e


class ReportBuilder:
    def __init__(
            self,
            data: Union[Sequence[str], Dict],
            verbose: int = 1,
            align: bool = False,
            minimize_memory: bool = False):
        self.verbose = verbose
        self.combined_json: Dict = {}
        self.entry_number_threshold = 4000000
        self.align = align
        self.minimize_memory = minimize_memory
        if isinstance(data, dict):
            self.jsons = [get_json(data)]
        elif isinstance(data, (list, tuple)):
            self.jsons = [get_json(j) for j in data]
        else:
            raise TypeError("Invalid data type for ReportBuilder")

    def combine_json(self) -> None:
        if self.combined_json:
            return
        if not self.jsons:
            raise ValueError("Can't get report of nothing")
        if self.align:
            for one in self.jsons:
                self.align_events(one["traceEvents"])
        self.combined_json = self.jsons[0]
        for one in self.jsons[1:]:
            if "traceEvents" in one:
                self.combined_json["traceEvents"].extend(one["traceEvents"])

    def align_events(self, original_events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
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

    def prepare_json(self, file_info: bool = True, display_time_unit: Optional[str] = None) -> None:
        # This will prepare self.combined_json to be ready to output
        self.combine_json()
        if self.verbose > 0:
            entries = len(self.combined_json["traceEvents"])
            print(f"Dumping trace data, total entries: {entries}")

        if display_time_unit is not None:
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
                            if m is not None:
                                file_name = m.group(1)
                                lineno = int(m.group(2))
                                if file_name not in file_dict:
                                    with open(file_name, "r", encoding="utf-8") as f:
                                        content = f.read()
                                        file_dict[file_name] = [content, content.count("\n")]
                                func_dict[event["name"]] = [file_name, lineno]
                        except Exception:
                            pass

    def generate_report(
            self,
            output_file: TextIO,
            output_format: str,
            file_info: bool = True) -> None:
        sub = {}
        if output_format == "html":
            self.prepare_json(file_info=file_info, display_time_unit="ns")
            with open(os.path.join(os.path.dirname(__file__), "html/trace_viewer_embedder.html"), encoding="utf-8") as f:
                tmpl = f.read()
            with open(os.path.join(os.path.dirname(__file__), "html/trace_viewer_full.html"), encoding="utf-8") as f:
                sub["trace_viewer_full"] = f.read()
            if "orjson" in sys.modules:
                sub["json_data"] = orjson.dumps(self.combined_json) \
                                         .decode("utf-8") \
                                         .replace("</script>", "<\\/script>")
            else:
                sub["json_data"] = json.dumps(self.combined_json) \
                                       .replace("</script>", "<\\/script>")
            output_file.write(Template(tmpl).substitute(sub))
        elif output_format == "json":
            self.prepare_json(file_info=file_info)
            if "orjson" in sys.modules:
                output_file.write(orjson.dumps(self.combined_json).decode("utf-8"))
            else:
                if self.minimize_memory:
                    json.dump(self.combined_json, output_file)  # type: ignore
                else:
                    output_file.write(json.dumps(self.combined_json))

    def save(self, output_file: Union[str, TextIO] = "result.html", file_info: bool = True) -> None:
        if isinstance(output_file, str):
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
        else:
            self.generate_report(output_file, output_format="json", file_info=file_info)

        if self.verbose > 0 and isinstance(output_file, str):
            report_abspath = os.path.abspath(output_file)
            print("Use the following command to open the report:")
            color_print("OKGREEN", "vizviewer {}".format(report_abspath))
