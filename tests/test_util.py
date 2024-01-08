# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

import os
import sys
import time
from multiprocessing import Process

import viztracer.util

from .base_tmpl import BaseTmpl


def target_child():
    time.sleep(1)


class TestUtil(BaseTmpl):
    def test_size_fmt(self):
        size_fmt = viztracer.util.size_fmt
        self.assertEqual(size_fmt(1024), "1.0KiB")
        self.assertEqual(size_fmt(1024**5), "1024.0TiB")

    def test_compare_version(self):
        compare_version = viztracer.util.compare_version
        self.assertEqual(compare_version("0.10.1", "0.10.0"), 1)
        self.assertEqual(compare_version("0.10.0", "0.9.10"), 1)
        self.assertEqual(compare_version("0.10.0", "0.10.0"), 0)
        self.assertEqual(compare_version("0.7.3", "0.8.1"), -1)
        self.assertEqual(compare_version("0.20.3", "0.31.0"), -1)

    def test_time_str_to_us(self):
        time_str_to_us = viztracer.util.time_str_to_us
        self.assertAlmostEqual(time_str_to_us("1.5"), 1.5)
        self.assertAlmostEqual(time_str_to_us("0.2us"), 0.2)
        self.assertAlmostEqual(time_str_to_us(".03ms"), 30)
        self.assertAlmostEqual(time_str_to_us("3s"), 3000000)
        self.assertAlmostEqual(time_str_to_us("600ns"), 0.6)
        self.assertRaises(ValueError, time_str_to_us, "0.0.0")
        self.assertRaises(ValueError, time_str_to_us, "invalid")

    def test_pid_exists(self):
        pid_exists = viztracer.util.pid_exists
        self.assertFalse(pid_exists(-1))
        if sys.platform != "win32":
            self.assertTrue(pid_exists(1))
        self.assertTrue(pid_exists(os.getpid()))
        with self.assertRaises(ValueError):
            pid_exists(0)

        # test child
        p = Process(target=target_child)
        p.start()
        self.assertTrue(pid_exists(p.pid))
        p.join()
        self.assertFalse(pid_exists(p.pid))

        # test a process that doesn't exist
        # Windows pid starts from 4
        if sys.platform == "win32":
            self.assertFalse(pid_exists(2))
