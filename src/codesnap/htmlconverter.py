# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/codesnap/blob/master/NOTICE.txt

import os
import html
import json
from string import Template


colors = ['#e6194B', '#3cb44b', '#ffe119', '#4363d8', '#f58231', '#42d4f4',
          '#f032e6', '#bfef45', '#fabed4', '#469990', '#dcbeff', '#9A6324',
          '#fffac8', '#aaffc3', '#808000', '#ffd8b1']


def string_to_color(s):
    return colors[hash(s) % len(colors)]


def snap_tree_node_html(node, parent_entry, parent_exit):
    parent_duration = parent_exit - parent_entry
    left = (node.t_entry - parent_entry) / parent_duration
    width = (node.t_exit - node.t_entry) / parent_duration
    ret = '<div style="left:{}%;width:{}%;" class="func-container">'.\
        format(left*100, width*100)
    ret += '<div style="background-color:{};" class="func-block">{}</div>'.\
        format(string_to_color(node.function_name), html.escape(node.function_name))
    for child in node.children:
        ret += child.html(node.t_entry, node.t_exit)
    ret += '</div>'

    return ret


def snap_tree_root_node_html(node):
    ret = '<div id="root" style="width:98vw;margin-left:1vw">'
    for child in node.children:
        ret += child.html(node.t_entry, node.t_exit)
    ret += '</div>'

    return ret


def generate_html_report_from_snap_tree(tree):
    sub = {}
    with open(os.path.join(os.path.dirname(__file__), "html/index.html")) as f:
        tmpl = f.read()
    with open(os.path.join(os.path.dirname(__file__), "html/d3-flamegraph.min.js")) as f:
        sub["d3flamegraph_js"] = f.read()
    with open(os.path.join(os.path.dirname(__file__), "html/d3-flamegraph.css")) as f:
        sub["d3flamegraph_css"] = f.read()
    sub["json_data"] = json.dumps(tree.get_json())
    
    return Template(tmpl).substitute(sub)
