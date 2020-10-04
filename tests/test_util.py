import os
import unittest
import viztracer.util


class TestUtil(unittest.TestCase):
    def test_size_fmt(self):
        size_fmt = viztracer.util.size_fmt
        self.assertEqual(size_fmt(1024), "1.0KiB")
        self.assertEqual(size_fmt(1024**5), "1024.0TiB")

    def test_get_url_from_file(self):
        get_url_from_file = viztracer.util.get_url_from_file
        get_url_from_file(os.path.join(os.path.dirname(__file__), "data", "fib.json"))