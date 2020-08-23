# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

import unittest
import viztracer
from viztracer import VizTracer


class TestIssue1(unittest.TestCase):
    def test_datetime(self):
        tracer = viztracer.VizTracer()
        tracer.start()
        from datetime import timedelta
        timedelta(hours=5)
        tracer.stop()
        tracer.parse()
        tracer.generate_json()

        tracer = viztracer.VizTracer(tracer="python")
        tracer.start()
        from datetime import timedelta
        timedelta(hours=5)
        tracer.stop()
        tracer.parse()
        tracer.generate_json()


class TestStackOptimization(unittest.TestCase):
    # There's an order issue in tracefunc to skip the FEE log
    # If the stack is empty(stack_top is NULL), and we entered
    # into an ignored function, ignore_stack_depth will increment.
    # However, when its corresponding exit comes, ignore_stack_depth
    # won't be decrement because the function is skipped when
    # stack is empty and it's a return function
    def test_instant(self):
        def s():
            return 0
        tracer = VizTracer()
        tracer.start()
        # This is a library function which will be ignored, but
        # this could trick the system into a ignoring status
        tracer.add_instant("name", {"a": 1})
        s()
        s()
        s()
        tracer.stop()
        entries = tracer.parse()
        tracer.save()
        self.assertEqual(entries, 4)


class TestSegFaultRegression(unittest.TestCase):
    # Without parsing, cleanup of C function had caused segfault
    def test_cleanup(self):
        tracer = VizTracer()
        tracer.start()
        _ = len([1, 2, 3])
        _ = sum([2, 3, 4])
        try:
            raise Exception("lol")
        except Exception:
            pass
        tracer.stop()
        tracer.cleanup()
