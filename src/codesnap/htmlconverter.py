# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/codesnap/blob/master/NOTICE.txt

import os
import html
import json
from string import Template


def generate_html_report_from_snap_tree(tree):
    sub = {}

    with open(os.path.join(os.path.dirname(__file__), "html/trace_viewer_embedder.html")) as f:
        tmpl = f.read()
    with open(os.path.join(os.path.dirname(__file__), "html/trace_viewer_full.html")) as f:
        sub["trace_viewer_full"] = f.read()
    sub["json_data"] = json.dumps(tree.get_json())

    return Template(tmpl).substitute(sub)
