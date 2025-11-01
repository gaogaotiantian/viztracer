# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt


import platform
import sys

from .cmdline_tmpl import CmdlineTmpl
from .package_env import package_matrix


def support_torch():
    if "linux" in sys.platform:
        return True
    if sys.platform == "win32":
        return sys.version_info < (3, 13)
    if sys.platform == "darwin":
        return platform.machine().lower() == "arm64" and sys.version_info < (3, 13)


@package_matrix(["~torch", "torch"] if support_torch() else ["~torch"])
class TestTorch(CmdlineTmpl):
    def test_entry(self):
        # We only want to install/uninstall torch once, so do all tests in one function
        with self.subTest("basic"):
            self.case_basic()

        with self.subTest("cmdline"):
            self.case_cmdline()

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
                    if "linux" in sys.platform:
                        # We care about Linux
                        self.assertLess(py["ts"], aten["ts"])
                        self.assertGreater(py["ts"] + py["dur"], aten["ts"] + aten["dur"])
                    elif sys.platform == "win32":
                        # Windows is at least sane, give it 50us diff
                        self.assertLess(py["ts"], aten["ts"] + 50)
                        self.assertGreater(py["ts"] + py["dur"], aten["ts"] + aten["dur"] - 50)
                    else:
                        # Mac is pure crazy and we don't care about it
                        pass

            self.template([sys.executable, "cmdline_test.py"], script=script,
                          check_func=check_func)
        else:
            script = """
                from viztracer import VizTracer
                _ = VizTracer(log_torch=True, verbose=0)
            """
            self.template([sys.executable, "cmdline_test.py"], script=script,
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
                    if "linux" in sys.platform:
                        # We care about Linux
                        self.assertLess(py["ts"], aten["ts"])
                        self.assertGreater(py["ts"] + py["dur"], aten["ts"] + aten["dur"])
                    elif sys.platform == "win32":
                        # Windows is at least sane, give it 100us diff
                        acceptable_margin = 100
                        self.assertLess(py["ts"], aten["ts"] + acceptable_margin)
                        self.assertGreater(py["ts"] + py["dur"], aten["ts"] + aten["dur"] - acceptable_margin)
                    else:
                        # Mac is pure crazy and we don't care about it
                        pass

            self.template(["viztracer", "--log_torch", "cmdline_test.py"], script=script, check_func=check_func)

        else:
            self.template(["viztracer", "--log_torch", "cmdline_test.py"], script="pass", success=False)
