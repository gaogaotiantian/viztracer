# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

import os
import unittest
import viztracer.util
from .base_tmpl import BaseTmpl


class TestUtil(BaseTmpl):
    def test_size_fmt(self):
        size_fmt = viztracer.util.size_fmt
        self.assertEqual(size_fmt(1024), "1.0KiB")
        self.assertEqual(size_fmt(1024**5), "1024.0TiB")

    def test_get_url_from_file(self):
        get_url_from_file = viztracer.util.get_url_from_file
        get_url_from_file(os.path.join(os.path.dirname(__file__), "data", "fib.json"))