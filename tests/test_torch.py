# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt


import sys

from .cmdline_tmpl import CmdlineTmpl
from .package_env import package_matrix


@package_matrix(["~torch", "torch"] if sys.version_info < (3, 13) or "linux" in sys.platform else ["~torch"])
class TestTorch(CmdlineTmpl):
    def test_entry(self):
        # We only want to install/uninstall torch once, so do all tests in one function
        with self.subTest("basic"):
            self.case_basic()

        with self.subTest("cmdline"):
            self.case_cmdline()

        with self.subTest("corner"):
            self.case_corner()

    def case_basic(self):
        assert self.pkg_config is not None

        if self.pkg_config.has("torch"):
            script = """
                import torch
                from viztracer import VizTracer
                with VizTracer(log_torch=True, verbose=0):
                    for i in range(100):
                        torch.empty(i)
            """

            def check_func(data):
                events = data["traceEvents"]
                py_events = [e for e in events if e["name"] == "torch.empty"]
                aten_events = [e for e in events if e["name"] == "aten::empty"]
                self.assertEqual(len(py_events), 100)
                self.assertEqual(len(aten_events), 100)
                for py, aten in zip(py_events, aten_events):
                    self.assertLess(py["ts"], aten["ts"])
                    self.assertGreater(py["ts"] + py["dur"], aten["ts"] + aten["dur"])

            self.template(["python", "cmdline_test.py"], script=script,
                          check_func=check_func)
        else:
            script = """
                from viztracer import VizTracer
                _ = VizTracer(log_torch=True, verbose=0)
            """
            self.template(["python", "cmdline_test.py"], script=script,
                          expected_output_file=None, success=False,
                          expected_stderr=".*ModuleNotFoundError.*")

    def case_cmdline(self):
        assert self.pkg_config is not None

        if self.pkg_config.has("torch"):
            script = """
                import torch
                for i in range(100):
                    torch.empty(i)
            """

            def check_func(data):
                events = data["traceEvents"]
                py_events = [e for e in events if e["name"] == "torch.empty"]
                aten_events = [e for e in events if e["name"] == "aten::empty"]
                self.assertEqual(len(py_events), 100)
                self.assertEqual(len(aten_events), 100)
                for py, aten in zip(py_events, aten_events):
                    self.assertLess(py["ts"], aten["ts"])
                    self.assertGreater(py["ts"] + py["dur"], aten["ts"] + aten["dur"])

            self.template(["viztracer", "--log_torch", "cmdline_test.py"], script=script, check_func=check_func)

        else:
            self.template(["viztracer", "--log_torch", "cmdline_test.py"], script="pass", success=False)
