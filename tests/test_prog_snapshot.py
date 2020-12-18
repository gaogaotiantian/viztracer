# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

import json
from viztracer.prog_snapshot import ProgSnapshot
from .base_tmpl import BaseTmpl


test1_str = '{"traceEvents":[{"pid":7761,"tid":7761,"ts":23668655769.443,"dur":0.4,"name":"h (test.py:6)","caller_lineno":10,"ph":"X","cat":"FEE"},{"pid":7761,"tid":7761,"ts":23668655769.243,"dur":1.2,"name":"g (test.py:9)","caller_lineno":18,"ph":"X","cat":"FEE"},{"pid":7761,"tid":7761,"ts":23668655770.543,"dur":0.1,"name":"h (test.py:6)","caller_lineno":19,"ph":"X","cat":"FEE"},{"pid":7761,"tid":7761,"ts":23668655769.043,"dur":1.7,"name":"f (test.py:14)","caller_lineno":22,"ph":"X","cat":"FEE"},{"pid":7761,"tid":7761,"ts":23668655771.143,"dur":0.1,"name":"h (test.py:6)","caller_lineno":10,"ph":"X","cat":"FEE"},{"pid":7761,"tid":7761,"ts":23668655771.043,"dur":0.3,"name":"g (test.py:9)","caller_lineno":17,"ph":"X","cat":"FEE"},{"pid":7761,"tid":7761,"ts":23668655771.443,"dur":0.0,"name":"h (test.py:6)","caller_lineno":19,"ph":"X","cat":"FEE"},{"pid":7761,"tid":7761,"ts":23668655770.943,"dur":0.6,"name":"f (test.py:14)","caller_lineno":24,"ph":"X","cat":"FEE"},{"pid":7761,"tid":7761,"ts":23668655768.843,"dur":2.8,"name":"t (test.py:21)","caller_lineno":26,"ph":"X","cat":"FEE"},{"pid":7761,"tid":7761,"ts":23668655766.943,"dur":4.8,"name":"<module> (test.py:2)","caller_lineno":147,"ph":"X","cat":"FEE"},{"pid":7761,"tid":7761,"ts":23668655766.343,"dur":5.8,"name":"builtins.exec","caller_lineno":147,"ph":"X","cat":"FEE"}],"displayTimeUnit":"ns","viztracer_metadata":{"version":"0.9.5"}}'  # noqa: E501


class TestSnapShot(BaseTmpl):
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

    def test_version(self):
        no_version_str = '{"traceEvents":[]}'
        snap = ProgSnapshot(no_version_str)
        self.assertFalse(snap.valid)

        low_version_str = '{"traceEvents":[], "viztracer_metadata":{"version":"0.0.1"}}'
        snap = ProgSnapshot(low_version_str)
        self.assertFalse(snap.valid)

        # Pure coverage
        high_version_str = '{"traceEvents":[{"pid":7761,"tid":7761,"ts":23668655766.343,"dur":5.8,"name":"builtins.exec","caller_lineno":147,"ph":"X","cat":"FEE"}], "viztracer_metadata":{"version":"1000.0.1"}}'  # noqa: E501
        snap = ProgSnapshot(high_version_str)

    def test_object(self):
        data = '{"traceEvents": [{"pid":1,"tid":1,"ts":0.05,"dur":5.8,"name":"builtins.exec","caller_lineno":147,"ph":"X","cat":"FEE"}, {"ph": "N", "pid": 1, "tid": 1, "ts": 0.1, "id": 1000, "name": "a"}, {"ph": "D", "pid": 1, "tid": 1, "ts": 0.3, "id": 1000, "name": "a"}], "viztracer_metadata": {"version": "0.9.5"}}'  # noqa: E501
        snap = ProgSnapshot(data)
        self.assertEqual(len(snap.object_events._objects), 1)

    def test_invalid(self):
        data = '{"traceEvents": [{"ph": "hello"}], "viztracer_metadata": {"version": "0.9.5"}}'
        with self.assertRaises(ValueError):
            _ = ProgSnapshot(data)

        data = '{"traceEvents": [{"ph": "hello", "pid": 1, "tid": 1}], "viztracer_metadata": {"version": "0.9.5"}}'
        with self.assertRaises(ValueError):
            _ = ProgSnapshot(data)

    def test_invalid_filename(self):
        data = '{"traceEvents": [{"pid":7761,"tid":7761,"ts":23668655769.443,"dur":0.4,"name":"_handle_fromlist (<frozen importlib._bootstrap>:1017)","caller_lineno":10,"ph":"X","cat":"FEE"}], "viztracer_metadata": {"version": "0.9.5"}}'  # noqa: E501
        prog = ProgSnapshot(data)
        prog.show()

    def test_multiple_process(self):
        data = '{"traceEvents": [{"pid":7762,"tid":7761,"ts":23668655766.343,"dur":5.8,"name":"builtins.exec","caller_lineno":147,"ph":"X","cat":"FEE"}, {"pid":7761,"tid":7761,"ts":23668655766.343,"dur":5.8,"name":"builtins.exec","caller_lineno":147,"ph":"X","cat":"FEE"}], "viztracer_metadata": {"version": "0.9.5"}}'  # noqa: E501
        snap = ProgSnapshot(data)
        self.assertEqual(len(list(snap.get_trees())), 2)

        # Coverage test
        _ = snap.list_pid()

    def test_change_parent(self):
        data = '{"traceEvents": [{"pid":7762,"tid":7761,"ts":0,"dur":100,"name":"grandpa","caller_lineno":147,"ph":"X","cat":"FEE"}, {"pid":7762,"tid":7761,"ts":50,"dur":10,"name":"grandson","caller_lineno":147,"ph":"X","cat":"FEE"}, {"pid":7762,"tid":7761,"ts":10,"dur":80,"name":"son","caller_lineno":147,"ph":"X","cat":"FEE"}], "viztracer_metadata": {"version": "0.9.5"}}'  # noqa: E501
        snap = ProgSnapshot(data)
        tree = next(snap.get_trees())
        for node in tree.inorder_traverse():
            if node.parent:
                self.assertIn(node, node.parent.children)
