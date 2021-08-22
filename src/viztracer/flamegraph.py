# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

import queue
from typing import Any, Dict, List, Optional, Tuple

from .functree import FuncTree, FuncTreeNode


class _FlameNode:
    def __init__(self, parent: Optional["_FlameNode"], name: str):
        self.name: str = name
        self.value: float = 0
        self.count: int = 0
        self.parent: Optional["_FlameNode"] = parent
        self.children: Dict[str, "_FlameNode"] = {}

    def get_child(self, child: FuncTreeNode) -> None:
        if child.fullname not in self.children:
            self.children[child.fullname] = _FlameNode(self, child.fullname)
        self.children[child.fullname].value += child.end - child.start
        self.children[child.fullname].count += 1
        for grandchild in child.children:
            self.children[child.fullname].get_child(grandchild)


class _FlameTree:
    def __init__(self, func_tree: FuncTree):
        self.root: _FlameNode = _FlameNode(None, "__root__")
        self.parse(func_tree)

    def parse(self, func_tree: FuncTree):
        self.root = _FlameNode(None, "__root__")
        for child in func_tree.root.children:
            self.root.get_child(child)


class FlameGraph:
    def __init__(self, trace_data: Optional[Dict[str, Any]] = None):
        self.trees: Dict[str, _FlameTree] = {}
        if trace_data:
            self.parse(trace_data)

    def parse(self, trace_data: Dict[str, Any]) -> None:
        func_trees: Dict[str, FuncTree] = {}
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

    def dump_to_perfetto(self) -> List[Dict[str, Any]]:
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
            q: queue.Queue[Tuple[_FlameNode, int, int]] = queue.Queue()
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
