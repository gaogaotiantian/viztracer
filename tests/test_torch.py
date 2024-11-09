# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt


import json
import sys
import tempfile
import unittest

from viztracer import VizTracer

from .cmdline_tmpl import CmdlineTmpl
from .package_env import package_matrix


@unittest.skipIf(sys.version_info >= (3, 13) and "linux" not in sys.platform, "torch only supports linux on python 3.13")
class TestTorch(CmdlineTmpl):
    @package_matrix(["~torch", "torch"])
    def test_entry(self):
        """
        We only want to toggle torch installation once so we have a single entry
        """

        with self.subTest("basic"):
            self.case_basic()

        with self.subTest("cmdline"):
            self.case_cmdline()

        with self.subTest("corner"):
            self.case_corner()

    def case_basic(self):
        try:
            import torch
        except ImportError:
            torch = None

        if torch:
            with tempfile.TemporaryDirectory() as tmpdir:
                with VizTracer(log_torch=True, verbose=0,
                               output_file=f"{tmpdir}/result.json"):
                    torch.empty(3)

                with open(f"{tmpdir}/result.json") as f:
                    data = json.load(f)
                    events = data["traceEvents"]
                    self.assertTrue(any(e["name"] == "torch.empty" for e in events))
                    self.assertTrue(any(e["name"] == "aten::empty" for e in events))
        else:
            with self.assertRaises(ImportError):
                _ = VizTracer(log_torch=True, verbose=0)

    def case_cmdline(self):
        try:
            import torch
        except ImportError:
            torch = None

        if torch:
            script = """
                import torch
                torch.empty(3)
            """

            def check_func(data):
                events = data["traceEvents"]
                self.assertTrue(any(e["name"] == "torch.empty" for e in events))
                self.assertTrue(any(e["name"] == "aten::empty" for e in events))

            self.template(["viztracer", "--log_torch", "cmdline_test.py"], script=script, check_func=check_func)

        else:
            self.template(["viztracer", "--log_torch", "cmdline_test.py"], script="pass", success=False)

    def case_corner(self):
        try:
            import torch
        except ImportError:
            torch = None

        if torch:
            with tempfile.TemporaryDirectory() as tmpdir:
                with VizTracer(log_torch=True, verbose=0,
                               output_file=f"{tmpdir}/result.json") as tracer:
                    torch.empty(3)
                    with self.assertRaises(RuntimeError):
                        tracer.calibrate_torch_timer()
                torch_offset = tracer.torch_offset
                tracer.calibrate_torch_timer()
                self.assertEqual(tracer.torch_offset, torch_offset)
        else:
            tracer = VizTracer(verbose=0)
            # Bad bad, just for coverage
            tracer.log_torch = True
            with self.assertRaises(ImportError):
                tracer.start()
