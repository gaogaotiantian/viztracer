# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt


import io
import os
from viztracer.report_builder import ReportBuilder
from .base_tmpl import BaseTmpl


class TestReportBuilder(BaseTmpl):
    def test_file(self):
        json_path = os.path.join(os.path.dirname(__file__), "data", "multithread.json")
        with open(json_path) as f:
            rb = ReportBuilder(f, verbose=0)
        with io.StringIO() as s:
            rb.save(s)
            result1 = s.getvalue()
        with io.StringIO() as s:
            rb.save(s)
            result2 = s.getvalue()
        self.assertEqual(result1, result2)

    def test_invalid(self):
        with self.assertRaises(TypeError):
            _ = ReportBuilder(123123)

        with self.assertRaises(ValueError):
            rb = ReportBuilder([])
            rb.save()

    def test_too_many_entry(self):
        json_path = os.path.join(os.path.dirname(__file__), "data", "multithread.json")
        with open(json_path) as f:
            rb = ReportBuilder(f, verbose=1)
        rb.entry_number_threshold = 20
        # Coverage only
        with io.StringIO() as s:
            rb.save(s)

    def test_invalid_json(self):
        invalid_json_path = os.path.join(os.path.dirname(__file__), "data", "fib.py")
        with open(invalid_json_path) as f:
            with self.assertRaises(Exception):
                ReportBuilder(f, verbose=1)
