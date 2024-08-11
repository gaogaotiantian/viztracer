# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/codesnap/blob/master/NOTICE.txt

import os
from .htmlconverter import snap_tree_node_html, snap_tree_root_node_html, generate_html_report_from_snap_tree

class SnapTreeNode:
    def __init__(self, parent, name, t_entry, t_exit):
        self.parent = parent
        self.function_name = name
        self.t_entry = t_entry
        self.t_exit = t_exit
        self.children = []

    def html(self, parent_entry = None, parent_exit = None):
        if parent_entry == None and parent_exit == None:
            # This is root
            return snap_tree_root_node_html(self)
        else:
            return snap_tree_node_html(self, parent_entry, parent_exit)

class SnapTree:
    def __init__(self):
        self.root = SnapTreeNode(None, "__root__", 0, 0)
        self.curr = self.root
        self.end = 0

    def add_entry(self, name, t):
        node = SnapTreeNode(self.curr, name, t, 0)
        self.curr.children.append(node)
        self.curr = node
        if self.root.t_entry == 0:
            self.root.t_entry = t

    def add_exit(self, name, t):
        self.curr.t_exit = t
        if name != self.curr.function_name:
            raise Exception("Function Entry/Exit did not match.{} vs {}", name, self.curr.function_name)
        self.curr = self.curr.parent
        if t > self.root.t_exit:
            self.root.t_exit = t

    def generate_html_report(self):
        return generate_html_report_from_snap_tree(self)
