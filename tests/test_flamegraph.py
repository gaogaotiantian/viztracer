# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

import unittest
import json
from viztracer import FlameGraph
import os


def depth(tree):
    if not tree["children"]:
        return 1
    return max([depth(n) for n in tree["children"]]) + 1

class TestFlameGraph(unittest.TestCase):
    def test_basic(self):
        with open(os.path.join(os.path.dirname(__file__), "data/multithread.json")) as f:
            sample_data = json.loads(f.read())
        fg = FlameGraph(sample_data)
        trees = fg.parse(sample_data)
        for tree in trees.values():
            self.assertEqual(depth(tree), 5)
        ofile = "result_flamegraph.html"
        fg.save(ofile)
        self.assertTrue(os.path.exists(ofile))
        os.remove(ofile)

    def test_load(self):
        fg = FlameGraph()
        fg.load(os.path.join(os.path.dirname(__file__), "data/multithread.json"))
        for tree in fg._data.values():
            self.assertEqual(depth(tree), 5)
        ofile = "result_flamegraph.html"
        fg.save(ofile)
        self.assertTrue(os.path.exists(ofile))
        os.remove(ofile)
