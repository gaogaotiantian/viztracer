import unittest

from setup_helpers import get_linux_attach_binary


class TestLinuxAttachBinary(unittest.TestCase):
    def test_x86_64_platform(self):
        self.assertEqual(
            get_linux_attach_binary("manylinux_2_17_x86_64"),
            "attach_process/attach_linux_amd64.so",
        )

    def test_aarch64_platform(self):
        self.assertIsNone(get_linux_attach_binary("manylinux2014_aarch64"))

    def test_i686_platform(self):
        self.assertEqual(
            get_linux_attach_binary("linux_i686"),
            "attach_process/attach_linux_x86.so",
        )

    def test_non_linux_platform(self):
        self.assertIsNone(get_linux_attach_binary("win_amd64"))

    def test_no_platform(self):
        self.assertIsNone(get_linux_attach_binary(None))

    def test_unknown_platform(self):
        self.assertIsNone(get_linux_attach_binary("linux_ppc64le"))
