# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

import copy
import bisect
import re


class FuncTreeNode:
    name_regex = r"(.*)\(([0-9]+)\)\.(.*)"

    def __init__(self, event=None):
        self.filename = None
        self.lineno = None
        self.caller_lineno = -1
        self.is_python = False
        self.funcname = None
        if event is None:
            self.event = {"name": "__ROOT__"}
            self.fullname = "__ROOT__"
            self.parent = None
            self.children = []
            self.start = -1
            self.end = 2 ** 64
        else:
            self.event = copy.copy(event)
            self.parent = None
            self.children = []
            self.start = self.event["ts"]
            self.end = self.event["ts"] + self.event["dur"]
            self.fullname = self.event["name"]
            m = re.match(self.name_regex, self.fullname)
            if m:
                self.is_python = True
                self.filename = m.group(1)
                self.lineno = int(m.group(2))
                self.funcname = m.group(3)
            if "caller_lineno" in self.event:
                self.caller_lineno = self.event["caller_lineno"]

    def is_ancestor(self, other):
        return self.start < other.start and self.end > other.end

    def is_same(self, other):
        return self.fullname == other.fullname and \
                len(self.children) == len(other.children) and \
                all([t[0].is_same(t[1]) for t in zip(self.children, other.children)])

    def adopt(self, other):
        new_children = []
        if self.is_ancestor(other):
            start_array = [n.start for n in self.children]
            end_array = [n.end for n in self.children]
            start_idx = bisect.bisect(start_array, other.start)
            end_idx = bisect.bisect(end_array, other.end)
            if (start_idx == end_idx + 1):
                self.children[end_idx].adopt(other)
            elif (start_idx == end_idx):
                other.parent = self
                self.children.insert(start_idx, other)
            elif (start_idx < end_idx):
                def change_parent(node):
                    node.parent = other
                new_children = self.children[start_idx:end_idx]
                map(change_parent, new_children)
                other.children = new_children
                other.parent = self
                self.children = self.children[:start_idx] + [other] + self.children[end_idx:]
            else:
                raise Exception("This should not be possible")
        else:
            self.parent.adopt(other)


class FuncTree:
    def __init__(self, pid=0, tid=0):
        self.root = FuncTreeNode()
        self.curr = self.root
        self.pid = pid
        self.tid = tid

    def is_same(self, other):
        return self.root.is_same(other.root)

    def add_event(self, event):
        node = FuncTreeNode(event)

        self.curr.adopt(node)
        self.curr = node

    def first_ts(self):
        return self.root.children[0].event["ts"]

    def first_node(self):
        return self.root.children[0]

    def node_by_timestamp(self, ts):
        starts = [node.start for node in self.root.children]
        idx = bisect.bisect(starts, ts)
        if idx == 0:
            return self.root.children[0]
        else:
            return self.root.children[idx-1]

    def normalize(self, first_ts):
        for node in self.inorder_traverse():
            node.start -= first_ts
            node.end -= first_ts

    def inorder_traverse(self):
        lst = [self.root]
        while lst:
            ret = lst.pop()
            lst.extend(ret.children[::-1])
            yield ret
        return
