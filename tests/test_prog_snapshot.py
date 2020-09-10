# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

import unittest
import json
from viztracer.prog_snapshot import ProgSnapshot


test1_str = '{"traceEvents":[{"pid":7761,"tid":7761,"ts":23668655769.443,"dur":0.4,"name":"test.py(6).h","caller_lineno":10,"ph":"X","cat":"FEE"},{"pid":7761,"tid":7761,"ts":23668655769.243,"dur":1.2,"name":"test.py(9).g","caller_lineno":18,"ph":"X","cat":"FEE"},{"pid":7761,"tid":7761,"ts":23668655770.543,"dur":0.1,"name":"test.py(6).h","caller_lineno":19,"ph":"X","cat":"FEE"},{"pid":7761,"tid":7761,"ts":23668655769.043,"dur":1.7,"name":"test.py(14).f","caller_lineno":22,"ph":"X","cat":"FEE"},{"pid":7761,"tid":7761,"ts":23668655771.143,"dur":0.1,"name":"test.py(6).h","caller_lineno":10,"ph":"X","cat":"FEE"},{"pid":7761,"tid":7761,"ts":23668655771.043,"dur":0.3,"name":"test.py(9).g","caller_lineno":17,"ph":"X","cat":"FEE"},{"pid":7761,"tid":7761,"ts":23668655771.443,"dur":0.0,"name":"test.py(6).h","caller_lineno":19,"ph":"X","cat":"FEE"},{"pid":7761,"tid":7761,"ts":23668655770.943,"dur":0.6,"name":"test.py(14).f","caller_lineno":24,"ph":"X","cat":"FEE"},{"pid":7761,"tid":7761,"ts":23668655768.843,"dur":2.8,"name":"test.py(21).t","caller_lineno":26,"ph":"X","cat":"FEE"},{"pid":7761,"tid":7761,"ts":23668655766.943,"dur":4.8,"name":"test.py(2).<module>","caller_lineno":147,"ph":"X","cat":"FEE"},{"pid":7761,"tid":7761,"ts":23668655766.343,"dur":5.8,"name":"builtins.exec","caller_lineno":147,"ph":"X","cat":"FEE"}],"displayTimeUnit":"ns"}'


class TestSnapShot(unittest.TestCase):
    def test_basic(self):
        snap = ProgSnapshot(test1_str)
        tree_len = len(list(snap.get_trees()))
        self.assertEqual(tree_len, 1)
        tree = next(snap.get_trees())
        count = 0
        for _ in tree.inorder_traverse():
            count += 1
        self.assertEqual(count, 12)

    def test_step(self):
        snap = ProgSnapshot(test1_str)
        self.assertEqual(snap.curr_frame.node.fullname, "builtins.exec")
        snap.step()
        self.assertEqual(snap.curr_frame.node.funcname, "<module>")
        snap.step()
        self.assertEqual(snap.curr_frame.node.funcname, "t")
        snap.step()
        self.assertEqual(snap.curr_frame.node.funcname, "f")
        snap.step()
        self.assertEqual(snap.curr_frame.node.funcname, "g")
        snap.step()
        self.assertEqual(snap.curr_frame.node.funcname, "h")
        snap.step()
        self.assertEqual(snap.curr_frame.node.funcname, "g")
        snap.step()
        self.assertEqual(snap.curr_frame.node.funcname, "f")
        snap.step()
        self.assertEqual(snap.curr_frame.node.funcname, "h")
        snap.step()
        self.assertEqual(snap.curr_frame.node.funcname, "f")
        snap.step()
        self.assertEqual(snap.curr_frame.node.funcname, "t")

    def test_next(self):
        snap = ProgSnapshot(test1_str)
        self.assertEqual(snap.curr_frame.node.fullname, "builtins.exec")
        snap.step()
        self.assertEqual(snap.curr_frame.node.funcname, "<module>")
        snap.step()
        self.assertEqual(snap.curr_frame.node.funcname, "t")
        snap.next()
        self.assertEqual(snap.curr_frame.node.funcname, "t")
        self.assertEqual(snap.curr_frame.curr_children_idx, 1)

    def test_random_entries(self):
        import random
        snap = ProgSnapshot(test1_str)
        test_obj = json.loads(test1_str)
        random.shuffle(test_obj["traceEvents"])
        snap2 = ProgSnapshot(json.dumps(test_obj))
        self.assertTrue(list(snap.get_trees())[0].is_same(list(snap2.get_trees())[0]))
