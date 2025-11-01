# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

try:
    import orjson as json  # type: ignore
except ImportError:
    import json  # type: ignore

import gzip
import importlib
import os
import re
import tokenize
from string import Template
from typing import Any, Sequence, TextIO

from . import __version__
from .util import color_print, same_line_print


def get_json(data: dict[str, Any] | str | tuple[str, dict]) -> dict[str, Any]:
    # This function will return a json object if data is already json object
    # or a opened file or a file path
    if isinstance(data, dict):
        # This is an object already
        return data
    elif isinstance(data, str):
        with open(data, encoding="utf-8") as f:
            json_str = f.read()
    elif isinstance(data, tuple):
        path, args = data
        if args['type'] == 'torch':
            with open(path, encoding="utf-8") as f:
                json_str = f.read()
            ret = json.loads(json_str)
            base_offset = args['base_offset']
            # torch 2.4.0+ uses baseTimeNanoseconds to store the offset
            # before that they simply use the absolute timestamp which is
            # equivalent to baseTimeNanoseconds = 0
            torch_offset = ret.get('baseTimeNanoseconds', 0)
            # convert to us
            offset_diff = (torch_offset - base_offset) / 1000

            for event in ret['traceEvents']:
                if 'ts' in event:
                    event['ts'] += offset_diff
                if event['ph'] == 'M':
                    # Pop metadata timestamp so it won't overwrite
                    # process and thread names
                    event.pop('ts', None)

            ret.pop("baseTimeNanoseconds", None)
            ret.pop("displayTimeUnit", None)
            ret.pop("traceName")
            ret.pop("deviceProperties")
            ret.pop("schemaVersion")

            ret['viztracer_metadata'] = {}

            return ret

    return json.loads(json_str)


class ReportBuilder:
    def __init__(
            self,
            data: Sequence[str | dict | tuple[str, dict]] | dict[str, Any],
            verbose: int = 1,
            align: bool = False,
            minimize_memory: bool = False,
            base_time: int | None = None) -> None:
        self.data = data
        self.verbose = verbose
        self.combined_json: dict = {}
        self.entry_number_threshold = 4000000
        self.align = align
        self.minimize_memory = minimize_memory
        self.jsons: list[dict] = []
        self.invalid_json_paths: list[str] = []
        self.json_loaded = False
        self.base_time = base_time
        self.final_messages: list[tuple[str, dict]] = []
        if not isinstance(data, (dict, list, tuple)):
            raise TypeError("Invalid data type for ReportBuilder")
        if isinstance(data, (list, tuple)):
            for path in data:
                if isinstance(path, dict):
                    continue
                if isinstance(path, tuple):
                    path = path[0]
                if not isinstance(path, str):
                    raise TypeError("Path should be a string")
                if not os.path.exists(path):
                    raise ValueError(f"{path} does not exist")
                if not path.endswith(".json"):
                    raise ValueError(f"{path} is not a json file")

    def load_jsons(self) -> None:
        if not self.json_loaded:
            self.json_loaded = True
            if isinstance(self.data, dict):
                self.jsons = [get_json(self.data)]
            elif isinstance(self.data, (list, tuple)):
                self.jsons = []
                self.invalid_json_paths = []
                for idx, j in enumerate(self.data):
                    if self.verbose > 0:
                        same_line_print(f"Loading trace data from processes {idx}/{len(self.data)}")
                    try:
                        self.jsons.append(get_json(j))
                    except json.JSONDecodeError:
                        assert isinstance(j, str)
                        self.invalid_json_paths.append(j)
                if len(self.invalid_json_paths) > 0:
                    self.final_messages.append(("invalid_json", {"paths": self.invalid_json_paths}))

    def combine_json(self) -> None:
        if self.verbose > 0:
            same_line_print("Combining trace data")
        if self.combined_json:
            return
        if not self.jsons:
            if self.invalid_json_paths:
                raise ValueError("No valid json files found")
            else:
                raise ValueError("Can't get report of nothing")
        if self.align:
            for one in self.jsons:
                self.align_events(one["traceEvents"], one['viztracer_metadata'].get('sync_marker', None))
        self.combined_json = self.jsons[0]
        if "viztracer_metadata" not in self.combined_json:
            self.combined_json["viztracer_metadata"] = {}
        for one in self.jsons[1:]:
            if "traceEvents" in one:
                self.combined_json["traceEvents"].extend(one["traceEvents"])
            if one.get("viztracer_metadata", {}).get("overflow", False):
                self.combined_json["viztracer_metadata"]["overflow"] = True
            if one.get("viztracer_metadata", {}).get("baseTimeNanoseconds") is not None:
                self.combined_json["viztracer_metadata"]["baseTimeNanoseconds"] = \
                    one["viztracer_metadata"]["baseTimeNanoseconds"]
            if "file_info" in one:
                if "file_info" not in self.combined_json:
                    self.combined_json["file_info"] = {"files": {}, "functions": {}}
                self.combined_json["file_info"]["files"].update(one["file_info"]["files"])
                self.combined_json["file_info"]["functions"].update(one["file_info"]["functions"])

    def align_events(self, original_events: list[dict[str, Any]], sync_marker: float | None = None) -> list[dict[str, Any]]:
        """
        Apply an offset to all the trace events, making the start timestamp 0
        This is useful when comparing multiple runs of the same script

        If sync_marker is not None then sync_marker  be used as an offset

        This function will change the timestamp in place, and return the original list
        """
        if sync_marker is None:
            offset_ts = min((event["ts"] for event in original_events if "ts" in event))
        else:
            offset_ts = sync_marker

        for event in original_events:
            if "ts" in event:
                event["ts"] -= offset_ts
        return original_events

    def prepare_json(self, file_info: bool = True, display_time_unit: str | None = None) -> None:
        # This will prepare self.combined_json to be ready to output
        self.load_jsons()
        self.combine_json()
        if self.verbose > 0:
            entries = len(self.combined_json["traceEvents"])
            same_line_print(f"Dumping trace data, total entries: {entries}")
            self.final_messages.append(("total_entries", {"total_entries": entries}))
            if self.combined_json["viztracer_metadata"].get("overflow", False):
                self.final_messages.append(("overflow", {}))

        if display_time_unit is not None:
            self.combined_json["displayTimeUnit"] = display_time_unit

        self.combined_json["viztracer_metadata"]["version"] = __version__

        if self.base_time is not None:
            self.combined_json["viztracer_metadata"]["baseTimeNanoseconds"] = self.base_time

        if file_info:
            if "file_info" not in self.combined_json:
                self.combined_json["file_info"] = {"files": {}, "functions": {}}
            pattern = re.compile(r".*\((.*):([0-9]*)\)")
            file_dict = self.combined_json["file_info"]["files"]
            func_dict = self.combined_json["file_info"]["functions"]
            for event in self.combined_json["traceEvents"]:
                if event["ph"] == 'X':
                    if event["name"] not in func_dict:
                        func_dict[event["name"]] = None
                        m = pattern.match(event["name"])
                        if m is not None:
                            file_name = m.group(1)
                            lineno = int(m.group(2))
                            if file_name not in file_dict:
                                content = self.get_source_from_filename(file_name)
                                if content is None:
                                    continue
                                file_dict[file_name] = [content, content.count("\n")]
                            func_dict[event["name"]] = [file_name, lineno]
            unknown_func_dict = set(func for func in func_dict if func_dict[func] is None)
            for func in unknown_func_dict:
                del func_dict[func]

    @classmethod
    def get_source_from_filename(cls, filename: str) -> str | None:
        if filename.startswith("<frozen "):
            m = re.match(r"<frozen (.*)>", filename)
            if not m:
                return None
            module_name = m.group(1)
            try:
                module = importlib.import_module(module_name)
            except ImportError:
                return None
            if hasattr(module, "__file__") and module.__file__ is not None:
                filename = module.__file__
            else:
                return None
        try:
            with tokenize.open(filename) as f:
                return f.read()
        except Exception:
            return None

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
            if json.__name__ == "orjson":
                sub["json_data"] = json.dumps(self.combined_json) \
                                       .decode("utf-8") \
                                       .replace("</script>", "<\\/script>")
            else:
                sub["json_data"] = json.dumps(self.combined_json) \
                                       .replace("</script>", "<\\/script>")  # type: ignore
            output_file.write(Template(tmpl).substitute(sub))
        elif output_format == "json":
            self.prepare_json(file_info=file_info)
            if json.__name__ == "orjson":
                output_file.write(json.dumps(self.combined_json).decode("utf-8"))
            else:
                if self.minimize_memory:
                    json.dump(self.combined_json, output_file)  # type: ignore
                else:
                    output_file.write(json.dumps(self.combined_json))  # type: ignore

    def save(self, output_file: str | TextIO = "result.html", file_info: bool = True) -> None:
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

        if isinstance(output_file, str):
            self.final_messages.append(("view_command", {"output_file": os.path.abspath(output_file)}))

        self.print_messages()

    def print_messages(self):
        if self.verbose > 0:
            same_line_print("")
            for msg_type, msg_args in self.final_messages:
                if msg_type == "overflow":
                    print("")
                    color_print("WARNING", ("Circular buffer is full, you lost some early data, "
                                            "but you still have the most recent data."))
                    color_print("WARNING", ("    If you need more buffer, use \"viztracer --tracer_entries <entry_number>\""))
                    color_print("WARNING", "    Or, you can try the filter options to filter out some data you don't need")
                    color_print("WARNING", "    use --quiet to shut me up")
                    print("")
                elif msg_type == "total_entries":
                    print(f"Total Entries: {msg_args['total_entries']}")
                elif msg_type == "view_command":
                    report_abspath = os.path.abspath(msg_args["output_file"])
                    print("Use the following command to open the report:")
                    if " " in report_abspath:
                        color_print("OKGREEN", f"vizviewer \"{report_abspath}\"")
                    else:
                        color_print("OKGREEN", f"vizviewer {report_abspath}")
                elif msg_type == "invalid_json":
                    print("")
                    color_print("WARNING", "Found and ignored invalid json file, you may lost some process data.")
                    color_print("WARNING", "Invalid json file:")
                    for msg in msg_args["paths"]:
                        color_print("WARNING", f"    {msg}")
                    print("")
