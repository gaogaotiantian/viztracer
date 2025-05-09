# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt


import io
import json
import os
import shutil
import sys
import tempfile
import textwrap
from unittest.mock import patch

import viztracer
from viztracer.report_builder import ReportBuilder

from .base_tmpl import BaseTmpl
from .cmdline_tmpl import CmdlineTmpl
from .package_env import package_matrix


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

    def test_get_source_from_filename(self):
        self.assertIsNotNone(ReportBuilder.get_source_from_filename("<frozen importlib._bootstrap>"))
        self.assertIsNotNone(ReportBuilder.get_source_from_filename(__file__))
        self.assertIsNone(ReportBuilder.get_source_from_filename("<frozen nonexistmodule>"))
        self.assertIsNone(ReportBuilder.get_source_from_filename("<frozen incomplete"))

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

    @patch('sys.stdout', new_callable=io.StringIO)
    def test_invalid_json_file(self, mock_stdout):
        with tempfile.TemporaryDirectory() as tmpdir:
            invalid_json_path = os.path.join(os.path.dirname(__file__), "data", "fib.py")
            valid_json_path = os.path.join(os.path.dirname(__file__), "data", "multithread.json")
            invalid_json_file = shutil.copy(invalid_json_path, os.path.join(tmpdir, "invalid.json"))
            valid_json_file = shutil.copy(valid_json_path, os.path.join(tmpdir, "valid.json"))
            rb = ReportBuilder([invalid_json_file, valid_json_file], verbose=1)
            with io.StringIO() as s:
                rb.save(s)
            self.assertIn("Invalid json file", mock_stdout.getvalue())

    @patch('sys.stdout', new_callable=io.StringIO)
    def test_all_invalid_json(self, mock_stdout):
        with tempfile.TemporaryDirectory() as tmpdir:
            invalid_json_path = os.path.join(os.path.dirname(__file__), "data", "fib.py")
            invalid_json_file = shutil.copy(invalid_json_path, os.path.join(tmpdir, "invalid.json"))
            rb = ReportBuilder([invalid_json_file], verbose=1)
            with self.assertRaises(Exception) as context:
                with io.StringIO() as s:
                    rb.save(s)
            self.assertEqual(str(context.exception), "No valid json files found")

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

            # Try to combine with an empty file
            empty_file = os.path.join(tmpdir, "empty.json")
            with open(empty_file, "w") as f:
                f.write(json.dumps({"traceEvents": []}))

            rb = ReportBuilder([empty_file, file_path1], verbose=0)
            with io.StringIO() as s:
                rb.save(output_file=s)
                data = json.loads(s.getvalue())
                self.assertEqual(len([e for e in data["traceEvents"] if e["name"] == "list.append"]), 10)


class TestReportBuilderCmdline(CmdlineTmpl):
    @package_matrix(["~orjson", "orjson"] if "free-threading" not in sys.version else None)
    def test_package_matrix(self):
        """
        The module will be imported only once so flipping the package matrix will only
        work when we start a new script
        """

        with tempfile.TemporaryDirectory() as tmpdir:
            invalid_json_path = os.path.join(os.path.dirname(__file__), "data", "fib.py")
            invalid_json_file = shutil.copy(invalid_json_path, os.path.join(tmpdir, "invalid.json"))

            script = textwrap.dedent(f"""
                import io
                from viztracer.report_builder import ReportBuilder
                rb = ReportBuilder([{repr(invalid_json_file)}], verbose=1)
                try:
                    with io.StringIO() as s:
                        rb.save(s)
                except Exception as e:
                    assert str(e) == "No valid json files found"
                else:
                    assert False
            """)

            self.template([sys.executable, "cmdline_test.py"], script=script, expected_output_file=None)
