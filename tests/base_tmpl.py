# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

import gc
import io
import json
import logging
import os
import sys
import time
from unittest import TestCase


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
)


class BaseTmpl(TestCase):
    trace_test_time = os.getenv("GITHUB_ACTION") and not os.getenv("COVERAGE_RUN")
    pkg_config = None

    @classmethod
    def setUpClass(cls):
        if cls.trace_test_time:
            cls._test_time_events = []

    @classmethod
    def tearDownClass(cls):
        if cls.trace_test_time:
            if os.path.exists("test_time_trace.json"):
                with open("test_time_trace.json", "r") as f:
                    trace = json.load(f)
            else:
                trace = {"traceEvents": []}
            trace["traceEvents"].extend(cls._test_time_events)

            with open("test_time_trace.json", "w") as f:
                json.dump(trace, f)

    def setUp(self):
        logging.info("=" * 60)
        logging.info(f"{self.id()} start")
        self.stdout = io.StringIO()
        self.stdout_orig, sys.stdout = sys.stdout, self.stdout
        if self.trace_test_time:
            self._test_start_time = time.time()

    def tearDown(self):
        if self.trace_test_time:
            test_duration = time.time() - self._test_start_time
            self._test_time_events.append({
                "name": self.id(),
                "cat": "test",
                "ph": "X",
                "ts": self._test_start_time * 1e6,
                "dur": test_duration * 1e6,
            })
        sys.stdout = self.stdout_orig
        logging.info(f"{self.id()} finish")
        gc.collect()

    def dbgPrint(self, *args, **kwargs):
        print(*args, file=self.stdout_orig, **kwargs)

    def assertEventNumber(self, data, expected_entries):
        entries = [entry for entry in data["traceEvents"] if entry["ph"] != "M"]
        entries_count = len(entries)
        self.assertEqual(entries_count, expected_entries,
                         f"Event number incorrect, {entries_count}(expected {expected_entries}) - {entries}")

    def assertFileExists(self, path, timeout=None, msg=None):
        err_msg = f"file {path} does not exist!"
        if msg is not None:
            err_msg = f"file {path} does not exist! {msg}"
        if timeout is None:
            if not os.path.exists(path):
                raise AssertionError(err_msg)
        else:
            start = time.time()
            while True:
                if os.path.exists(path):
                    return
                elif time.time() - start > timeout:
                    raise AssertionError(err_msg)
                else:
                    time.sleep(0.5)

    def assertFileNotExist(self, path):
        if os.path.exists(path):
            raise AssertionError(f"file {path} does exist!")

    def assertTrueTimeout(self, func, timeout):
        start = time.time()
        while True:
            try:
                func()
                break
            except AssertionError as e:
                if time.time() - start > timeout:
                    raise e
