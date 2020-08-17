import unittest
import json
from viztracer import FlameGraph
import os


class TestFlameGraph(unittest.TestCase):
    def test_basic(self):
        with open(os.path.join(os.path.dirname(__file__), "data/multithread.json")) as f:
            sample_data = json.loads(f.read())
        fg = FlameGraph(sample_data)
        fg.parse(sample_data)
        ofile = "result_flamegraph.html"
        fg.save(ofile)
        self.assertTrue(os.path.exists(ofile))
        os.remove(ofile)

    def test_load(self):
        fg = FlameGraph()
        fg.load(os.path.join(os.path.dirname(__file__), "data/multithread.json"))
        ofile = "result_flamegraph.html"
        fg.save(ofile)
        self.assertTrue(os.path.exists(ofile))
        os.remove(ofile)
