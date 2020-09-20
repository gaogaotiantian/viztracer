import unittest
import viztracer.util


class TestUtil(unittest.TestCase):
    def test_size_fmt(self):
        size_fmt = viztracer.util.size_fmt
        self.assertEqual(size_fmt(1024), "1.0KiB")
        self.assertEqual(size_fmt(1024**5), "1024.0TiB")