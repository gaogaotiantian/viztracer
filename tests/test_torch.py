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
                    for _ in range(5):
                        torch.empty(3)
            """

            def check_func(data):
                events = data["traceEvents"]
                py_events = [e for e in events if e["name"] == "torch.empty"]
                aten_events = [e for e in events if e["name"] == "aten::empty"]
                self.assertEqual(len(py_events), 5)
                self.assertEqual(len(aten_events), 5)
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
                for _ in range(5):
                    torch.empty(5)
            """

            def check_func(data):
                events = data["traceEvents"]
                py_events = [e for e in events if e["name"] == "torch.empty"]
                aten_events = [e for e in events if e["name"] == "aten::empty"]
                self.assertEqual(len(py_events), 5)
                self.assertEqual(len(aten_events), 5)
                for py, aten in zip(py_events, aten_events):
                    self.assertLess(py["ts"], aten["ts"])
                    self.assertGreater(py["ts"] + py["dur"], aten["ts"] + aten["dur"])

            self.template(["viztracer", "--log_torch", "cmdline_test.py"], script=script, check_func=check_func)

        else:
            self.template(["viztracer", "--log_torch", "cmdline_test.py"], script="pass", success=False)

    def case_corner(self):
        assert self.pkg_config is not None

        if self.pkg_config.has("torch"):
            script = """
                import torch
                from viztracer import VizTracer
                with VizTracer(log_torch=True, verbose=0) as tracer:
                    torch.empty(3)
                    try:
                        tracer.calibrate_torch_timer()
                    except RuntimeError:
                        pass
                    else:
                        assert False, "Should raise RuntimeError"
                torch_offset = tracer.torch_offset
                tracer.calibrate_torch_timer()
                assert tracer.torch_offset == torch_offset
            """
            self.template(["python", "cmdline_test.py"], script=script)
        else:
            script = """
                from viztracer import VizTracer
                tracer = VizTracer(verbose=0)
                # Bad bad, just for coverage
                tracer.log_torch = True
                tracer.start()
            """

            self.template(["python", "cmdline_test.py"], script=script, expected_output_file=None, success=False,
                          expected_stderr=".*ImportError.*")
