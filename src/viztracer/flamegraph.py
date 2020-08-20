# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

import os
try:
    import orjson as json
except ImportError:
    import json
from string import Template


class _FlameNode:
    def __init__(self, parent, name):
        self.name = name
        self.value = 0
        self.last_entry = -1
        self.parent = parent
        self.children = {}

    def json(self):
        return {
            "name": self.name,
            "value": self.value,
            "children": [child.json() for child in self.children.values()]
        }


class _FlameTree:
    def __init__(self):
        self.root = _FlameNode(None, "__root__")
        self.curr = self.root

    def add_entry(self, data):
        if self.root.last_entry == -1:
            self.root.last_entry = data["ts"]
        if data["name"] in self.curr.children:
            self.curr = self.curr.children[data["name"]]
        else:
            node = _FlameNode(self.curr, data["name"])
            self.curr.children[data["name"]] = node
            self.curr = node
        self.curr.last_entry = data["ts"]

    def add_exit(self, data):
        if self.curr != self.root:
            self.curr.value += data["ts"] - self.curr.last_entry
            self.curr = self.curr.parent
            if self.curr == self.root:
                self.root.value = data["ts"] - self.root.last_entry

    def json(self):
        return self.root.json()


class FlameGraph:
    def __init__(self, trace_data=None):
        if trace_data:
            self._data = self.parse(trace_data)

    def parse(self, trace_data):
        trees = {}
        ret = {}
        for data in trace_data["traceEvents"]:
            key = "p{}_t{}".format(data["pid"], data["tid"])
            if key in trees:
                tree = trees[key]
            else:
                tree = _FlameTree()
                trees[key] = tree
            if data["ph"] == "B":
                tree.add_entry(data)
            elif data["ph"] == "E":
                tree.add_exit(data)
        for key in trees:
            ret[key] = trees[key].json()
        return ret

    def load(self, input_file):
        with open(input_file) as f:
            self._data = self.parse(json.loads(f.read()))

    def save(self, output_file="result_flamegraph.html"):
        sub = {}
        with open(os.path.join(os.path.dirname(__file__), "html/flamegraph.html")) as f:
            tmpl = f.read()
        sub["data"] = self._data

        with open(output_file, "w") as f:
            f.write(Template(tmpl).substitute(sub))
