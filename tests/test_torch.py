# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt


import json
import sys
import tempfile
import unittest

from .cmdline_tmpl import CmdlineTmpl
from .package_env import package_matrix


@unittest.skipIf(sys.version_info >= (3, 13) and "linux" not in sys.platform, "torch only supports linux on python 3.13")
@package_matrix(["~torch", "torch"])
class TestTorch(CmdlineTmpl):
    def test_basic(self):
        assert self.pkg_config is not None

        if self.pkg_config.has("torch"):
            with tempfile.TemporaryDirectory() as tmpdir:
                script = f"""
                    import torch
                    from viztracer import VizTracer
                    with VizTracer(log_torch=True, verbose=0,
                                   output_file="{tmpdir}/result.json"):
                        torch.empty(3)
                """

                self.template(["python", "cmdline_test.py"], script=script,
                              expected_output_file=None)

                with open(f"{tmpdir}/result.json") as f:
                    data = json.load(f)
                    events = data["traceEvents"]
                    self.assertTrue(any(e["name"] == "torch.empty" for e in events))
                    self.assertTrue(any(e["name"] == "aten::empty" for e in events))
        else:
            script = """
                from viztracer import VizTracer
                _ = VizTracer(log_torch=True, verbose=0)
            """
            self.template(["python", "cmdline_test.py"], script=script,
                          expected_output_file=None, success=False,
                          expected_stderr=".*ModuleNotFoundError.*")

    def test_cmdline(self):
        assert self.pkg_config is not None

        if self.pkg_config.has("torch"):
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

    def test_corner(self):
        assert self.pkg_config is not None

        if self.pkg_config.has("torch"):
            with tempfile.TemporaryDirectory() as tmpdir:
                script = f"""
                    import torch
                    from viztracer import VizTracer
                    with VizTracer(log_torch=True, verbose=0,
                                   output_file=f"{tmpdir}/result.json") as tracer:
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
                self.template(["python", "cmdline_test.py"], script=script, expected_output_file=None)
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
