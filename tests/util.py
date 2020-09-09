import os
import json


def adapt_json_file(filename):
    path = os.path.join(os.path.dirname(__file__), "data", filename)
    py_path_lst = path.split(".")
    py_path_lst[-1] = "py"
    py_path = ".".join(py_path_lst)
    with open(path) as f:
        data = json.loads(f.read())
        for event in data["traceEvents"]:
            if event["ph"] == "X":
                idx = event["name"].index("(")
                new_name = py_path + event["name"][idx:]
                event["name"] = new_name

    with open(path, "w") as f:
        f.write(json.dumps(data))


def get_json_file_path(filename):
    return os.path.join(os.path.dirname(__file__), "data", filename)
