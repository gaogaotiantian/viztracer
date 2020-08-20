# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

import unittest
import viztracer


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
