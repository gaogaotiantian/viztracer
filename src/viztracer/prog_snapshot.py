# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

try:
    import orjson as json
except ImportError:
    import json
import bisect
from .functree import FuncTree
from .util import color_print
from . import __version__


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

            start = firstlineno - 1
            line = lst[start]
            stripped_line = line.lstrip()
            code_indent = len(line) - len(stripped_line)

            if node.funcname != "<module>":
                end = firstlineno
                indented = False
                while end < len(lst):
                    line = lst[end]
                    stripped_line = line.lstrip()
                    indent = len(line) - len(stripped_line)
                    if indent > code_indent:
                        indented = True
                    elif indented:
                        if len(stripped_line) > 0 and \
                                not stripped_line.startswith("#"):
                            break
                    end += 1

                # clear the ending spaces
                while lst[end-1].strip() == "":
                    end -= 1
            else:
                end = len(lst)

            if self.curr_children_idx >= len(self.node.children):
                currline = end
            else:
                currline = self.node.children[self.curr_children_idx].caller_lineno - 1

            for idx in range(start, end):
                if len(lst[idx].strip()) > 0:
                    if idx == currline:
                        lst[idx] = "> " + lst[idx]
                    else:
                        lst[idx] = "  " + lst[idx]

            if currline == end:
                self.code_string = "".join(lst[start:end] + ["> \n"])
            else:
                self.code_string = "".join(lst[start:end] + ["  \n"])
        else:
            self.code_string = "> " + self.node.fullname
        p(self.code_string)


class CounterEvents:
    def __init__(self):
        self._events = []

    def add_event(self, event):
        # The events have to be added in order
        if self._events:
            args = self._events[-1]["args"].copy()
        else:
            args = {}
        args.update(event["args"])
        self._events.append({
            "ts": event["ts"],
            "args": args
        })

    def normalize(self, first_ts):
        for event in self._events:
            event["ts"] -= first_ts

    def get_args(self, ts):
        ts_lst = [event["ts"] for event in self._events]
        idx = bisect.bisect(ts_lst, ts)
        if idx == 0:
            return {}
        else:
            return self._events[idx-1]["args"]


class ObjectEvents:
    def __init__(self):
        self._objects = {}

    def add_event(self, event):
        if event["id"] not in self._objects:
            entry = {
                "id": event["id"],
                "name": event["name"],
                "snapshots": [
                ]
            }
            self._objects[event["id"]] = entry

        entry = self._objects[event["id"]]

        if event["ph"] in ["N", "D"]:
            entry["snapshots"].append({
                "ts": event["ts"],
                "args": None
            })
        elif event["ph"] == "O":
            entry["snapshots"].append({
                "ts": event["ts"],
                "args": event["args"]["snapshot"]
            })
        else: # pragma: no cover
            raise ValueError("Unexpected type for object event")

    def normalize(self, first_ts):
        for entry in self._objects.values():
            for snapshot in entry["snapshots"]:
                snapshot["ts"] -= first_ts

    def get_args(self, ts):
        ret = {}
        for entry in self._objects.values():
            ts_lst = [snapshot["ts"] for snapshot in entry["snapshots"]]
            idx = bisect.bisect(ts_lst, ts)
            if idx != 0:
                snapshot = entry["snapshots"][idx-1]
                if snapshot["args"] is not None:
                    ret[entry["name"]] = snapshot["args"]
        return ret


class ProgSnapshot:
    compatible_version = "0.6.2"
    def __init__(self, json_string=None, p=print):
        self.func_trees = {}
        self.curr_node = None
        self.curr_frame = None
        self.first_tree = None
        self.curr_tree = None
        self.counter_events = CounterEvents()
        self.object_events = ObjectEvents()
        if json_string:
            if not self.load(json_string):
                self.valid = False
                return
        self.p = p
        self.valid = True

    def load(self, json_string):
        self.func_trees = {}
        raw_data = json.loads(json_string)
        if "viztracer_metadata" not in raw_data:
            color_print("FAIL", "Error, json file version too old.")
            return False
        else:
            if not self.check_version(raw_data["viztracer_metadata"]["version"]):
                return False
        trace_events = raw_data["traceEvents"]
        for event in trace_events:
            self.load_event(event)
        self.first_tree = min([tree for tree in self.get_trees()], key=lambda x: x.first_ts())
        first_ts = self.first_tree.first_ts()
        self.curr_tree = self.first_tree
        self.curr_frame = Frame(None, self.first_tree.first_node())
        for tree in self.get_trees():
            tree.normalize(first_ts)
        self.counter_events.normalize(first_ts)
        self.object_events.normalize(first_ts)
        return True

    def load_event(self, event):
        # event is a chrome trace format event object
        try:
            ph = event["ph"]
            pid = event["pid"]
            tid = event["tid"]
        except Exception:
            raise ValueError("Error when loading event data: {}", event)

        if ph == "X":
            if pid not in self.func_trees:
                self.func_trees[pid] = {}
            if tid not in self.func_trees[pid]:
                self.func_trees[pid][tid] = FuncTree(pid, tid)

            self.func_trees[pid][tid].add_event(event)
        elif ph == "C":
            self.counter_events.add_event(event)
        elif ph in ["N", "D", "O"]:
            self.object_events.add_event(event)
        else:
            print("Unsupported event type: {}".format(ph))
            return

    def check_version(self, version):
        if tuple(version.split(".")) < tuple(self.compatible_version.split(".")):
            color_print("FAIL", "Error, json file version too old.")
            return False
        elif tuple(version.split(".")) > tuple(__version__.split(".")):
            color_print("WARNING", "Warning, json file version is newer than vdb! Not sure if it's compatible")
        return True

    def get_trees(self):
        for pid in self.func_trees:
            for tid in self.func_trees[pid]:
                yield self.func_trees[pid][tid]
        return

    def show(self):
        self.curr_frame.show(self.p)

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
            new_frame = Frame(curr_frame, child)
            self.curr_frame = new_frame
        else:
            # go out of the function
            success, _ = self.func_return()
            if not success:
                return False, "at the end of the trace"
        return True, None

    def step_back(self):
        self._goto_inner_frame()
        curr_frame = self.curr_frame
        if curr_frame.curr_children_idx > 0:
            curr_frame.curr_children_idx -= 1
            child = curr_frame.node.children[curr_frame.curr_children_idx]
            new_frame = Frame(curr_frame, child)
            new_frame.curr_children_idx = len(new_frame.node.children)
            self.curr_frame = new_frame
        else:
            # go out of the function
            success, _ = self.func_return_back()
            if not success:
                return False, "at the beginning of the trace"
        return True, None

    def next(self):
        self._goto_inner_frame()
        curr_frame = self.curr_frame
        if curr_frame.curr_children_idx < len(curr_frame.node.children):
            curr_frame.curr_children_idx += 1
        else:
            # go out of the function
            success, _ = self.func_return()
            if not success:
                return False, "at the end of the trace"
        return True, None

    def next_back(self):
        self._goto_inner_frame()
        curr_frame = self.curr_frame
        if curr_frame.curr_children_idx > 0:
            curr_frame.curr_children_idx -= 1
        else:
            # go out of the function
            success, _ = self.func_return_back()
            if not success:
                return False, "at the beginning of the trace"
        return True, None

    def func_return(self):
        self._goto_inner_frame()
        curr_frame = self.curr_frame
        if not curr_frame.parent:
            # Check if there's a sibling
            node = curr_frame.node
            idx = node.parent.children.index(node)
            if idx < len(node.parent.children) - 1:
                self.curr_frame = Frame(None, node.parent.children[idx+1])
                return True, None
            return False, "No callers available"
        curr_frame = curr_frame.parent
        curr_frame.curr_children_idx += 1
        curr_frame.next = None
        self.curr_frame = curr_frame

        return True, None

    def func_return_back(self):
        self._goto_inner_frame()
        curr_frame = self.curr_frame
        if not curr_frame.parent:
            # Check if there's a sibling
            node = curr_frame.node
            idx = node.parent.children.index(node)
            if idx > 0:
                self.curr_frame = Frame(None, node.parent.children[idx-1])
                return True, None
            return False, "No callers available"
        curr_frame = curr_frame.parent
        curr_frame.next = None
        self.curr_frame = curr_frame

        return True, None

    def where(self):
        tmp_frame = self.curr_frame
        while tmp_frame.parent:
            tmp_frame = tmp_frame.parent
        while True:
            if tmp_frame == self.curr_frame:
                self.p("> " + tmp_frame.node.fullname)
            else:
                self.p("  " + tmp_frame.node.fullname)
            if tmp_frame.next:
                tmp_frame = tmp_frame.next
            else:
                break

        return True, None

    def goto_timestamp(self, ts):
        frame = Frame(None, self.curr_tree.node_by_timestamp(ts))
        while True:
            if frame.node.children:
                starts = [child.start for child in frame.node.children]
                idx = bisect.bisect_left(starts, ts)
                if idx == 0:
                    frame.curr_children_idx = 0
                    break
                else:
                    idx -= 1
                if frame.node.children[idx].end <= ts:
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

    def get_timestamp(self):
        tmp_frame = self.curr_frame
        while tmp_frame.next:
            tmp_frame = tmp_frame.next
        if not tmp_frame.node.children:
            return tmp_frame.node.start
        if tmp_frame.curr_children_idx >= len(tmp_frame.node.children):
            return tmp_frame.node.children[-1].end
        else:
            return tmp_frame.node.children[tmp_frame.curr_children_idx].start

    def print_timestamp(self):
        self.p(str(self.get_timestamp()))

        return True, None

    def print_counter(self):
        self.p(str(self.counter_events.get_args(self.get_timestamp())))

        return True, None

    def print_object(self):
        object_dict = self.object_events.get_args(self.get_timestamp())
        for k, v in object_dict.items():
            self.p(str(k) + ":")
            self.p(str(v))

        return True, None

    def list_tid(self):
        curr_tree = self.curr_tree
        forest = self.func_trees[curr_tree.pid]
        for tid in forest:
            if tid == curr_tree.tid:
                self.p("> {}".format(tid))
            else:
                self.p("  {}".format(tid))

        return True, None

    def list_pid(self):
        curr_tree = self.curr_tree
        for pid in self.func_trees:
            if pid == curr_tree.pid:
                self.p("> {}".format(pid))
            else:
                self.p("  {}".format(pid))

        return True, None

    def goto_tid(self, tid):
        assert(type(tid) is int)
        forest = self.func_trees[self.curr_tree.pid]
        if tid not in forest:
            return False, "No such tid"
        else:
            ts = self.get_timestamp()
            self.curr_tree = forest[tid]
            self.goto_timestamp(ts)

        return True, None

    def goto_pid(self, pid):
        assert(type(pid) is int)
        if pid not in self.func_trees:
            return False, "No such pid"
        else:
            ts = self.get_timestamp()
            forest = self.func_trees[pid]
            for tid in forest:
                self.curr_tree = forest[tid]
                break
            self.goto_timestamp(ts)

        return True, None

    def print_args(self):
        self.p(str(self.curr_frame.node.event.get("args", "")))

        return True, None
