# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

import json
import os
import re
import subprocess


def generate_json(filename):
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    cwd = os.getcwd()
    os.chdir(data_dir)
    path = os.path.join(os.path.dirname(__file__), "data", filename)
    subprocess.run(["python", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    os.chdir(cwd)


def adapt_json_file(filename):
    path = os.path.join(os.path.dirname(__file__), "data", filename)
    py_filename = ".".join(filename.split(".")[:-1] + ["py"])
    py_path_lst = path.split(".")
    py_path_lst[-1] = "py"
    py_path = ".".join(py_path_lst)
    with open(path) as f:
        data = json.loads(f.read())
        name_regex = re.compile(r"(.*) \((.*):([0-9]*)\)")
        for event in data["traceEvents"]:
            if event["ph"] == "X":
                try:
                    m = name_regex.match(event["name"])
                    if m and py_filename in event["name"]:
                        event["name"] = f"{m.group(1)} ({py_path}:{m.group(3)})"
                except ValueError:
                    pass

    with open(path, "w") as f:
        f.write(json.dumps(data))


def get_tests_data_file_path(filename):
    return os.path.join(os.path.dirname(__file__), "data", filename)


def cmd_with_coverage(cmd):
    if os.getenv("COVERAGE_RUN"):
        if cmd[0] == "python":
            return ["coverage", "run", "--source", "viztracer", "--parallel-mode"] + cmd[1:]
        elif cmd[0] == "viztracer":
            return ["coverage", "run", "--source", "viztracer", "--parallel-mode", "-m"] + cmd
        else:
            raise ValueError(f"can't get cmd with coverage for {cmd}")
    return cmd
