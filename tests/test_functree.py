# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt


import json

from viztracer.functree import FuncTree

from .base_tmpl import BaseTmpl


test_str = '{"traceEvents":[{"pid":7761,"tid":7761,"ts":23668655769.443,"dur":0.4,"name":"h (test.py:6)","caller_lineno":10,"ph":"X","cat":"FEE"},{"pid":7761,"tid":7761,"ts":23668655769.243,"dur":1.2,"name":"g (test.py:9)","caller_lineno":18,"ph":"X","cat":"FEE"},{"pid":7761,"tid":7761,"ts":23668655770.543,"dur":0.1,"name":"h (test.py:6)","caller_lineno":19,"ph":"X","cat":"FEE"},{"pid":7761,"tid":7761,"ts":23668655769.043,"dur":1.7,"name":"f (test.py:14)","caller_lineno":22,"ph":"X","cat":"FEE"},{"pid":7761,"tid":7761,"ts":23668655771.143,"dur":0.1,"name":"h (test.py:6)","caller_lineno":10,"ph":"X","cat":"FEE"},{"pid":7761,"tid":7761,"ts":23668655771.043,"dur":0.3,"name":"g (test.py:9)","caller_lineno":17,"ph":"X","cat":"FEE"},{"pid":7761,"tid":7761,"ts":23668655771.443,"dur":0.0,"name":"h (test.py:6)","caller_lineno":19,"ph":"X","cat":"FEE"},{"pid":7761,"tid":7761,"ts":23668655770.943,"dur":0.6,"name":"f (test.py:14)","caller_lineno":24,"ph":"X","cat":"FEE"},{"pid":7761,"tid":7761,"ts":23668655768.843,"dur":2.8,"name":"t (test.py:21)","caller_lineno":26,"ph":"X","cat":"FEE"},{"pid":7761,"tid":7761,"ts":23668655766.943,"dur":4.8,"name":"<module> (test.py:2)","caller_lineno":147,"ph":"X","cat":"FEE"},{"pid":7761,"tid":7761,"ts":23668655766.343,"dur":5.8,"name":"builtins.exec","caller_lineno":147,"ph":"X","cat":"FEE"}],"displayTimeUnit":"ns","viztracer_metadata":{"version":"0.9.5"}}'  # noqa: E501


class TestFuncTree(BaseTmpl):
    def test_random(self):
        import random
        test_obj1 = json.loads(test_str)
        test_obj2 = json.loads(test_str)
        random.shuffle(test_obj2["traceEvents"])

        tree1 = FuncTree()
        for event in test_obj1["traceEvents"]:
            tree1.add_event(event)

        tree2 = FuncTree()
        for event in test_obj2["traceEvents"]:
            tree2.add_event(event)

        self.assertTrue(tree1.is_same(tree2))
