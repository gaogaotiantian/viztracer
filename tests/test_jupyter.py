# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt


import os
from .base_tmpl import BaseTmpl


class TestJupyter(BaseTmpl):
    def setUp(self):
        super().setUp()
        try:
            from IPython.testing.globalipapp import start_ipython
            self.start_ipython = start_ipython
        except ImportError:
            self.skipTest("No Jupyter, skip Jupyter test")

    def test_cellmagic(self):
        ip = self.start_ipython()
        ip.magic("load_ext viztracer")
        ip.run_cell_magic(magic_name="viztracer", line="", cell="print(1)")
        self.assertTrue(os.path.exists("./viztracer_report.json"))
        os.remove("./viztracer_report.json")
