try:
    import orjson as json
except ImportError:
    import json
from .functree import FuncTree
import bisect


class Frame:
    def __init__(self, parent, node):
        self.parent = parent
        self.node = node
        self.curr_children_idx = 0
        self.next = None
        self.code_string = None
        if parent:
            parent.next = self

    @property
    def curr_children_idx(self):
        return self.__curr_children_idx

    @curr_children_idx.setter
    def curr_children_idx(self, idx):
        self.code_string = None
        self.__curr_children_idx = idx

    def show(self, p):
        if self.code_string:
            p(self.code_string)
            return

        node = self.node
        firstlineno = node.lineno
        if node.filename:
            with open(node.filename) as f:
                lst = f.readlines()

            indent = -1
            start = firstlineno - 1
            line = lst[start]
            stripped_line = line.lstrip()
            indent = len(line) - len(stripped_line)

            if node.funcname != "<module>":
                end = firstlineno
                while end < len(lst):
                    line = lst[end]
                    stripped_line = line.lstrip()
                    if not stripped_line.startswith("#") and len(line) - len(stripped_line) <= indent:
                        break
                    end += 1

                # clear the ending spaces
                while lst[end-1].strip() == "":
                    end -= 1
            else:
                end = len(lst)

            if self.curr_children_idx >= len(self.node.children):
                currline = end - 1
            else:
                currline = self.node.children[self.curr_children_idx].caller_lineno - 1

            for idx in range(start, end):
                if len(lst[idx].strip()) > 0:
                    if idx == currline:
                        lst[idx] = "> " + lst[idx]
                    else:
                        lst[idx] = "  " + lst[idx]

            self.code_string = "".join(lst[start:end])
        else:
            self.code_string = "> " + self.node.fullname
        p(self.code_string)


class ProgSnapshot:
    def __init__(self, json_string=None):
        self.func_trees = {}
        self.curr_node = None
        self.curr_frame = None
        self.first_tree = None
        if json_string:
            self.load(json_string)

    def load(self, json_string):
        self.func_trees = {}
        raw_data = json.loads(json_string)
        trace_events = raw_data["traceEvents"]
        for event in trace_events:
            self.load_event(event)
        self.first_tree = min([tree for tree in self.get_trees()], key=lambda x: x.first_ts())
        first_ts = self.first_tree.first_ts()
        self.curr_frame = Frame(None, self.first_tree.first_node())
        for tree in self.get_trees():
            tree.normalize(first_ts)

    def load_event(self, event):
        # event is a chrome trace format event object
        try:
            ph = event["ph"]
            pid = event["pid"]
            tid = event["tid"]
        except Exception:
            print("Error when loading event data: {}", event)
            return

        if ph == "X":
            if pid not in self.func_trees:
                self.func_trees[pid] = {}
            if tid not in self.func_trees[pid]:
                self.func_trees[pid][tid] = FuncTree()

            self.func_trees[pid][tid].add_event(event)
        else:
            # Currently we only support complete events
            return

    def get_trees(self):
        for pid in self.func_trees:
            for tid in self.func_trees[pid]:
                yield self.func_trees[pid][tid]
        return

    def show(self, p):
        self.curr_frame.show(p)

    def up(self):
        # Inspect previous frame
        if not self.curr_frame.parent:
            return False, "No outer frame anymore"
        self.curr_frame = self.curr_frame.parent
        return True, None

    def down(self):
        if not self.curr_frame.next:
            return False, "Already at current frame"
        self.curr_frame = self.curr_frame.next
        return True, None

    def _goto_inner_frame(self):
        while self.curr_frame.next:
            self.curr_frame = self.curr_frame.next

    def step(self):
        self._goto_inner_frame()
        curr_frame = self.curr_frame
        if curr_frame.curr_children_idx < len(curr_frame.node.children):
            child = curr_frame.node.children[curr_frame.curr_children_idx]
            if child.is_python:
                new_frame = Frame(curr_frame, child)
                self.curr_frame = new_frame
            else:
                curr_frame.curr_children_idx += 1
        else:
            # go out of the function
            if curr_frame.parent:
                curr_frame = curr_frame.parent
                curr_frame.next = None
                curr_frame.curr_children_idx += 1
                self.curr_frame = curr_frame
            else:
                return False, "at the end of the trace"
        return True, None

    def step_back(self):
        self._goto_inner_frame()
        curr_frame = self.curr_frame
        if curr_frame.curr_children_idx > 0:
            curr_frame.curr_children_idx -= 1
            child = curr_frame.node.children[curr_frame.curr_children_idx]
            if child.is_python:
                new_frame = Frame(curr_frame, child)
                new_frame.curr_children_idx = len(new_frame.node.children)
                self.curr_frame = new_frame
        else:
            # go out of the function
            if curr_frame.parent:
                curr_frame = curr_frame.parent
                curr_frame.next = None
                self.curr_frame = curr_frame
            else:
                return False, "at the beginning of the trace"
        return True, None

    def next(self):
        self._goto_inner_frame()
        curr_frame = self.curr_frame
        if curr_frame.curr_children_idx < len(curr_frame.node.children) - 1:
            curr_frame.curr_children_idx += 1
        else:
            # go out of the function
            if curr_frame.parent:
                curr_frame = curr_frame.parent
                curr_frame.next = None
                curr_frame.curr_children_idx += 1
                self.curr_frame = curr_frame
            else:
                return False, "at the end of the trace"
        return True, None

    def next_back(self):
        self._goto_inner_frame()
        curr_frame = self.curr_frame
        if curr_frame.curr_children_idx > 0:
            curr_frame.curr_children_idx -= 1
        else:
            # go out of the function
            if curr_frame.parent:
                curr_frame = curr_frame.parent
                curr_frame.next = None
                self.curr_frame = curr_frame
            else:
                return False, "at the beginning of the trace"
        return True, None

    def func_return(self):
        self._goto_inner_frame()
        curr_frame = self.curr_frame
        if not curr_frame.parent:
            return False, "No callers available"
        curr_frame = curr_frame.parent
        curr_frame.curr_children_idx += 1
        curr_frame.next = None
        self.curr_frame = curr_frame

        return True, None

    def where(self, p):
        tmp_frame = self.curr_frame
        while tmp_frame.parent:
            tmp_frame = tmp_frame.parent
        while True:
            if tmp_frame == self.curr_frame:
                p("> " + tmp_frame.node.fullname)
            else:
                p("  " + tmp_frame.node.fullname)
            if tmp_frame.next:
                tmp_frame = tmp_frame.next
            else:
                break

        return True, None

    def goto_timestamp(self, ts):
        frame = Frame(None, self.first_tree.first_node())
        while True:
            if frame.node.children:
                starts = [child.start for child in frame.node.children]
                idx = bisect.bisect(starts, ts)
                if idx == 0:
                    frame.curr_children_idx = 0
                    break
                else:
                    idx -= 1
                if frame.node.children[idx].end < ts:
                    # here's what we need!
                    frame.curr_children_idx = idx + 1
                    break
                else:
                    new_frame = Frame(frame, frame.node.children[idx])
                    frame = new_frame
            else:
                break
        self.curr_frame = frame

        return True, None
