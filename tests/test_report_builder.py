# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt


import io
import json
import os
import tempfile

import viztracer
from viztracer.report_builder import ReportBuilder

from .base_tmpl import BaseTmpl


class TestReportBuilder(BaseTmpl):
    def test_file(self):
        json_path = os.path.join(os.path.dirname(__file__), "data", "multithread.json")
        with open(json_path) as f:
            rb = ReportBuilder(json.loads(f.read()), verbose=0)
        with io.StringIO() as s:
            rb.save(s)
            result1 = s.getvalue()
        with io.StringIO() as s:
            rb.save(s)
            result2 = s.getvalue()
        self.assertEqual(result1, result2)

    def test_minimize_memory(self):
        json_path = os.path.join(os.path.dirname(__file__), "data", "multithread.json")
        with open(json_path) as f:
            rb = ReportBuilder(json.loads(f.read()), verbose=0, minimize_memory=True)
        with io.StringIO() as s:
            rb.save(s)
            result1 = s.getvalue()
        with open(json_path) as f:
            rb = ReportBuilder(json.loads(f.read()), verbose=0, minimize_memory=False)
        with io.StringIO() as s:
            rb.save(s)
            result2 = s.getvalue()
        self.assertEqual(result1, result2)

    def test_invalid(self):
        with self.assertRaises(TypeError):
            _ = ReportBuilder(123123)

        with self.assertRaises(TypeError):
            _ = ReportBuilder([123])
            _ = ReportBuilder([123, 223])

        with self.assertRaises(ValueError):
            _ = ReportBuilder(["/nosuchfile"])
            _ = ReportBuilder(["/nosuchfile1", "nosuchfile2"])

        with self.assertRaises(ValueError):
            rb = ReportBuilder([])
            rb.save()

    def test_too_many_entry(self):
        json_path = os.path.join(os.path.dirname(__file__), "data", "multithread.json")
        with open(json_path) as f:
            rb = ReportBuilder(json.loads(f.read()), verbose=1)
        rb.entry_number_threshold = 20
        # Coverage only
        with io.StringIO() as s:
            rb.save(s)

    def test_invalid_json(self):
        invalid_json_path = os.path.join(os.path.dirname(__file__), "data", "fib.py")
        with self.assertRaises(Exception):
            ReportBuilder([invalid_json_path], verbose=1)

    def test_combine(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path1 = os.path.join(tmpdir, "result1.json")
            file_path2 = os.path.join(tmpdir, "result2.json")
            with viztracer.VizTracer(output_file=file_path1, verbose=0):
                a = []
                for _ in range(10):
                    a.append(1)

            with viztracer.VizTracer(tracer_entries=5, output_file=file_path2, verbose=0):
                a = []
                for _ in range(10):
                    a.append(1)

            rb = ReportBuilder([file_path1, file_path2], verbose=0)
            with io.StringIO() as s:
                rb.save(output_file=s)
                data = json.loads(s.getvalue())
                self.assertTrue(data["viztracer_metadata"]["overflow"])
