# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

import os
import queue
try:
    import orjson as json
except ImportError:
    import json
from string import Template

from .functree import FuncTree


class _FlameNode:
    def __init__(self, parent, name):
        self.name = name
        self.value = 0
        self.count = 0
        self.parent = parent
        self.children = {}

    def get_child(self, child):
        if child.fullname not in self.children:
            self.children[child.fullname] = _FlameNode(self, child.fullname)
        self.children[child.fullname].value += child.end - child.start
        self.children[child.fullname].count += 1
        for grandchild in child.children:
            self.children[child.fullname].get_child(grandchild)

    def json(self):
        return {
            "name": self.name,
            "value": self.value,
            "children": [child.json() for child in self.children.values()]
        }


class _FlameTree:
    def __init__(self, func_tree):
        self.root = _FlameNode(None, "__root__")
        self.parse(func_tree)

    def parse(self, func_tree):
        self.root = _FlameNode(None, "__root__")
        for child in func_tree.root.children:
            self.root.get_child(child)

    def json(self):
        return self.root.json()


class FlameGraph:
    def __init__(self, trace_data=None):
        self.trees = {}
        if trace_data:
            self.parse(trace_data)

    def parse(self, trace_data):
        func_trees = {}
        for data in trace_data["traceEvents"]:
            key = "p{}_t{}".format(data["pid"], data["tid"])
            if key in func_trees:
                tree = func_trees[key]
            else:
                tree = FuncTree(data["pid"], data["tid"])
                func_trees[key] = tree

            if data["ph"] == "X":
                tree.add_event(data)

        for key, tree in func_trees.items():
            self.trees[key] = _FlameTree(tree)

    def dump_to_json(self):
        ret = {}
        for key in self.trees:
            ret[key] = self.trees[key].json()
        return ret

    def load(self, input_file):
        with open(input_file, encoding="utf-8") as f:
            self.parse(json.loads(f.read()))

    def save(self, output_file="result_flamegraph.html"):
        sub = {}
        with open(os.path.join(os.path.dirname(__file__), "html/flamegraph.html"), encoding="utf-8") as f:
            tmpl = f.read()
        sub["data"] = self.dump_to_json()

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(Template(tmpl).substitute(sub))

    def dump_to_perfetto(self):
        """
        reformat data to what perfetto likes
        private _functionProfileDetails?: FunctionProfileDetails[]
        export interface FunctionProfileDetails {
          name?: string;
          flamegraph?: CallsiteInfo[];
          expandedCallsite?: CallsiteInfo;
          expandedId?: number;
        }
        export interface CallsiteInfo {
          id: number;
          parentId: number;
          depth: number;
          name?: string;
          totalSize: number;
          selfSize: number;
          mapping: string;
          merged: boolean;
          highlighted: boolean;
        }
        """
        ret = []
        for name, tree in self.trees.items():
            q = queue.Queue()
            for child in tree.root.children.values():
                q.put((child, -1, 0))

            if q.empty():
                continue

            flamegraph = []
            idx = 0
            while not q.empty():
                node, parent, depth = q.get()
                flamegraph.append({
                    "id": idx,
                    "parentId": parent,
                    "depth": depth,
                    "name": node.name,
                    "totalSize": node.value,
                    "selfSize": node.value - sum((n.value for n in node.children.values())),
                    "mapping": f"{node.count}",
                    "merged": False,
                    "highlighted": False
                })
                for n in node.children.values():
                    q.put((n, idx, depth + 1))
                idx += 1

            detail = {
                "name": name,
                "flamegraph": flamegraph
            }
            ret.append(detail)
        return ret
