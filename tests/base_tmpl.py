# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

from unittest import TestCase
import gc
import os
import time


class BaseTmpl(TestCase):
    def setUp(self):
        print("{} start".format(self.id()))

    def tearDown(self):
        print("{} finish".format(self.id()))
        gc.collect()

    def assertEventNumber(self, data, expected_entries):
        entries = [entry for entry in data["traceEvents"] if entry["ph"] != "M"]
        entries_count = len(entries)
        self.assertEqual(entries_count, expected_entries,
                         f"Event number incorrect, {entries_count}(expected {expected_entries}) - {entries}")

    def assertFileExists(self, path, timeout=None):
        if timeout is None:
            if not os.path.exists(path):
                raise AssertionError(f"file {path} does not exist!")
        else:
            start = time.time()
            while True:
                if os.path.exists(path):
                    return
                elif time.time() - start > timeout:
                    raise AssertionError(f"file {path} does not exist!")
                else:
                    time.sleep(0.5)

    def assertTrueTimeout(self, func, timeout):
        start = time.time()
        while True:
            try:
                func()
                break
            except AssertionError as e:
                if time.time() - start > timeout:
                    raise e
