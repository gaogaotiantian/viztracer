import os
import unittest
from viztracer.report_builder import ReportBuilder


class TestReportBuilder(unittest.TestCase):
    def test_file(self):
        json_path = os.path.join(os.path.dirname(__file__), "data", "multithread.json")
        with open(json_path) as f:
            rb = ReportBuilder(f, verbose=0)
        rb.combine_json()
        result1 = rb.generate_json()
        rb.combine_json()
        result2 = rb.generate_json()
        self.assertEqual(result1, result2)

    def test_invalid(self):
        with self.assertRaises(TypeError):
            _ = ReportBuilder(123123)
