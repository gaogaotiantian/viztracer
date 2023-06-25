# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

import json
import os

from viztracer.flamegraph import FlameGraph

from .base_tmpl import BaseTmpl


class TestFlameGraph(BaseTmpl):
    def test_dump_perfetto(self):
        with open(os.path.join(os.path.dirname(__file__), "data/multithread.json")) as f:
            sample_data = json.loads(f.read())
        fg = FlameGraph(sample_data)
        data = fg.dump_to_perfetto()
        self.assertEqual(len(data), 5)
        for callsite_info in data:
            self.assertIn("name", callsite_info)
            self.assertIn("flamegraph", callsite_info)

        # Test if FlameGraph can handle empty tree
        sample_data["traceEvents"].append(
            {"ph": "M", "pid": 1, "tid": 1, "name": "thread_name", "args": {"name": "MainThread"}})
        fg = FlameGraph(sample_data)
        self.assertEqual(len(fg.trees), 6)
        data = fg.dump_to_perfetto()
        self.assertEqual(len(data), 5)
