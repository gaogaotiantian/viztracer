# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/codesnap/blob/master/NOTICE.txt

from .htmlconverter import generate_html_report_from_snap_tree


class SnapTreeNode:
    def __init__(self, parent, name, t_entry, t_exit):
        self.parent = parent
        self.function_name = name
        self.t_entry = t_entry
        self.t_exit = t_exit
        self.exited = False
        self.children = []

    def json_object(self):
        stack = [self]
        ret = []

        while stack:
            node = stack.pop()
            data = {
                "name": node.function_name,
                "cat": "FEE",
                "ts": node.t_entry,
                "pid": 1,
                "tid": 1,
                "dur": node.t_exit-node.t_entry,
                "ph": "X",
                "value": node.t_exit - node.t_entry,
                "entry": node.t_entry,
                "exit": node.t_exit,
            }
            ret.append(data)
            if node.children:
                stack.extend(node.children[::-1])
        return ret


class SnapTree:
    def __init__(self):
        self.root = SnapTreeNode(None, "__root__", 0, 0)
        self.curr = self.root
        self.end = 0
        # whether to normalize the timestamp so it will start at 0
        self.normalize = True
        self.start_ts = None

    def add_entry(self, name, t):
        # print("entry: {}, {}".format(name, t))
        if self.normalize:
            if not self.start_ts:
                self.start_ts = t
            t -= self.start_ts
        else:
            if self.root.t_entry == 0:
                self.root.t_entry = t

        node = SnapTreeNode(self.curr, name, t, 0)
        self.curr.children.append(node)
        self.curr = node

    def add_exit(self, name, t):
        # print("exit: {}, {}".format(name, t))
        if self.normalize:
            if not self.start_ts:
                self.start_ts = t
            t -= self.start_ts
        self.curr.t_exit = t
        if self.curr == self.root:
            # If we are out of the first stack, just ignore
            # This will actually help the exit of start() function
            return
        if name != self.curr.function_name:
            # if this is a class function, self will be built in the method
            # we check if the only difference is that the exit function has
            # a self object with a class name now
            name_lst = name.split(".")
            if self.curr.function_name == ".".join(name_lst[:-2] + name_lst[-1:]):
                pass
            else:
                raise Exception("Function Entry/Exit did not match. {} vs {}".format(name, self.curr.function_name))
        self.curr.exited = True
        self.curr = self.curr.parent
        if t > self.root.t_exit:
            self.root.t_exit = t

    def generate_html_report(self):
        return generate_html_report_from_snap_tree(self)

    def get_json(self):
        return self.root.json_object()
