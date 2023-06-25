# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt


import os

from .base_tmpl import BaseTmpl


class TestJupyter(BaseTmpl):
    def setUp(self):
        super().setUp()
        try:
            from IPython.terminal.interactiveshell import \
                TerminalInteractiveShell
            self.ip = TerminalInteractiveShell.instance()
        except ImportError:
            self.skipTest("No Jupyter, skip Jupyter test")

    def test_cellmagic(self):
        self.ip.run_line_magic("load_ext", "viztracer")
        self.ip.run_cell_magic(magic_name="viztracer", line="", cell="print(1)")
        self.assertFileExists("./viztracer_report.json")
        os.remove("./viztracer_report.json")
