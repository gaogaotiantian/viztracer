# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt


import json
import logging
import lzma
import os
import tempfile
import unittest
import zlib
from collections import namedtuple
from functools import wraps
from shutil import copyfileobj
from typing import Callable, List, Optional, Tuple, overload

from .cmdline_tmpl import CmdlineTmpl
from .test_performance import Timer
from .util import get_tests_data_file_path


class TestVCompressor(CmdlineTmpl):
    def test_basic(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cvf_path = os.path.join(tmpdir, "result.cvf")
            dup_json_path = os.path.join(tmpdir, "result.json")
            self.template(
                ["viztracer", "-o", cvf_path, "--compress", get_tests_data_file_path("multithread.json")],
                expected_output_file=cvf_path,
                cleanup=False)

            self.template(
                ["viztracer", "-o", dup_json_path, "--decompress", cvf_path],
                expected_output_file=dup_json_path)

    def test_compress_invalid(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cvf_path = os.path.join(tmpdir, "result.cvf")
            not_exist_path = os.path.join(tmpdir, "do_not_exist.json")
            result = self.template(
                ["viztracer", "-o", cvf_path, "--compress", not_exist_path],
                expected_output_file=None,
                success=False)
            self.assertIn("Unable to find file", result.stdout.decode("utf8"))

            result = self.template(
                ["viztracer", "-o", cvf_path, "--compress", get_tests_data_file_path("fib.py")],
                expected_output_file=None,
                success=False)
            self.assertIn("Only support compressing json report", result.stdout.decode("utf8"))

    def test_compress_default_outputfile(self):
        default_compress_output = "result.cvf"
        self.template(
            ["viztracer", "--compress", get_tests_data_file_path("multithread.json")],
            expected_output_file=default_compress_output,
            cleanup=False)

        self.assertTrue(os.path.exists(default_compress_output))

        self.template(
            ["viztracer", "-o", "result.json", "--decompress", default_compress_output],
            expected_output_file="result.json")

        self.cleanup(output_file=default_compress_output)

    def test_decompress_invalid(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            not_exist_path = os.path.join(tmpdir, "result.cvf")
            dup_json_path = os.path.join(tmpdir, "result.json")
            result = self.template(
                ["viztracer", "-o", dup_json_path, "--decompress", not_exist_path],
                expected_output_file=dup_json_path,
                success=False)
            self.assertIn("Unable to find file", result.stdout.decode("utf8"))

    def test_decompress_default_outputfile(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cvf_path = os.path.join(tmpdir, "result.cvf")
            default_decompress_output = "result.json"
            self.template(
                ["viztracer", "-o", cvf_path, "--compress", get_tests_data_file_path("multithread.json")],
                expected_output_file=cvf_path,
                cleanup=False)

            self.template(
                ["viztracer", "--decompress", cvf_path],
                expected_output_file=default_decompress_output,
                cleanup=False)

            self.assertTrue(os.path.exists(default_decompress_output))
            self.cleanup(output_file=default_decompress_output)


test_large_fib = """
from viztracer import VizTracer
tracer = VizTracer(tracer_entries=2000000)
tracer.start()

def fib(n):
    if n < 2:
        return 1
    return fib(n-1) + fib(n-2)
fib(27)

tracer.stop()
tracer.save(output_file='%s')
"""


class TestVCompressorPerformance(CmdlineTmpl):

    BenchmarkResult = namedtuple("BenchmarkResult", ["file_size", "elapsed_time"])  # unit: byte, second

    @overload
    def _benchmark(benchmark_process: Callable[..., None]):
        ...

    @overload
    def _benchmark(repeat: int):
        ...

    def _benchmark(*args, **kargs):
        def _decorator(benchmark_process: Callable) -> Callable:
            @wraps(benchmark_process)
            def _wrapper(self, uncompressed_file_path: str) -> "TestVCompressorPerformance.BenchmarkResult":
                compression_time_total = 0.
                with tempfile.TemporaryDirectory() as tmpdir:
                    compressed_file_path = os.path.join(tmpdir, "result.compressed")
                    # pre-warm
                    benchmark_process(self, uncompressed_file_path, compressed_file_path)
                    os.remove(compressed_file_path)
                    # real benchmark
                    for _ in range(loop_time):
                        with Timer() as t:
                            benchmark_process(self, uncompressed_file_path, compressed_file_path)
                            compression_time_total += t.get_time()
                        compressed_file_size = os.path.getsize(compressed_file_path)
                        os.remove(compressed_file_path)
                return TestVCompressorPerformance.BenchmarkResult(compressed_file_size, compression_time_total / loop_time)
            return _wrapper

        if len(args) == 0 and len(kargs) == 0:
            raise TypeError("_benchmark must decorate a function.")

        # used as @_benchmark
        if len(args) == 1 and len(kargs) == 0 and callable(args[0]):
            loop_time = 3
            return _decorator(args[0])

        # used as @_benchmark(...)
        loop_time = kargs["repeat"] if "repeat" in kargs else args[0]
        return _decorator

    @staticmethod
    def _human_readable_filesize(filesize: int) -> str:  # filesize in bytes
        units = [("PB", 1 << 50), ("TB", 1 << 40), ("GB", 1 << 30), ("MB", 1 << 20), ("KB", 1 << 10)]
        for unit_name, unit_base in units:
            norm_size = filesize / unit_base
            if norm_size >= 0.8:
                return f"{norm_size:8.2f}{unit_name}"
        return f"{filesize:8.2f}B"

    @classmethod
    def _print_result(
        cls,
        filename: str,
        original_size: int,
        vcompress_result: BenchmarkResult,
        other_results: List[Tuple[str, BenchmarkResult]],  # [(compressor_name, BenchmarkResult)]
        subtest_idx: Optional[int] = None,
    ):
        if subtest_idx is None:
            logging.info(f"On file \"{filename}\":")
        else:
            logging.info(f"{subtest_idx}. On file \"{filename}\":")

        # Space-wise Info
        logging.info("    [Space]")
        logging.info("      Uncompressed:   {}".format(
            cls._human_readable_filesize(original_size)),
        )
        logging.info("      VCompressor:    {}(1.000) [CR:{:6.2f}%]".format(  # CR stands for compress ratio
            cls._human_readable_filesize(vcompress_result.file_size),
            vcompress_result.file_size / original_size * 100,
        ))
        for name, result in other_results:
            logging.info("      {}{}({:.3f}) [CR:{:6.2f}%]".format(
                name + ":" + " " * max(15 - len(name), 0),
                cls._human_readable_filesize(result.file_size),
                result.file_size / vcompress_result.file_size,
                result.file_size / original_size * 100,
            ))

        # Time-wise Info
        logging.info("    [Time]")
        logging.info("      VCompressor:    {:9.3f}s(1.000)".format(
            vcompress_result.elapsed_time,
        ))
        for name, result in other_results:
            logging.info("      {}{:9.3f}s({:.3f})".format(
                name + ":" + " " * max(15 - len(name), 0),
                result.elapsed_time,
                result.elapsed_time / vcompress_result.elapsed_time,
            ))

    @_benchmark
    def _benchmark_vcompressor(self, uncompressed_file_path: str, compressed_file_path: str) -> None:
        self.template(
            ["viztracer", "-o", compressed_file_path, "--compress", uncompressed_file_path],
            expected_output_file=compressed_file_path, script=None, cleanup=False,
        )

    @_benchmark
    def _benchmark_lzma(self, uncompressed_file_path: str, compressed_file_path: str) -> None:
        with open(uncompressed_file_path, "rb") as original_file:
            with lzma.open(compressed_file_path, "wb", preset=lzma.PRESET_DEFAULT) as compressed_file:
                copyfileobj(original_file, compressed_file)

    @_benchmark
    def _benchmark_zlib(self, uncompressed_file_path: str, compressed_file_path: str) -> None:
        with open(uncompressed_file_path, "rb") as original_file:
            compressed_data = zlib.compress(original_file.read())
        with open(compressed_file_path, "wb") as compressed_file:
            compressed_file.write(compressed_data)

    @_benchmark
    def _benchmark_vcompressor_lzma(self, uncompressed_file_path: str, compressed_file_path: str) -> None:
        tmp_compress_file = uncompressed_file_path + ".tmp"
        self.template(
            ["viztracer", "-o", tmp_compress_file, "--compress", uncompressed_file_path],
            expected_output_file=tmp_compress_file,
            script=None,
            cleanup=False)

        with open(tmp_compress_file, "rb") as tmp_file:
            with lzma.open(compressed_file_path, "wb", preset=lzma.PRESET_DEFAULT) as compressed_file:
                copyfileobj(tmp_file, compressed_file)

    @_benchmark
    def _benchmark_vcompressor_zlib(self, uncompressed_file_path: str, compressed_file_path: str) -> None:
        tmp_compress_file = uncompressed_file_path + ".tmp"
        self.template(
            ["viztracer", "-o", tmp_compress_file, "--compress", uncompressed_file_path],
            expected_output_file=tmp_compress_file,
            script=None,
            cleanup=False)
        with open(tmp_compress_file, "rb") as tmp_file:
            compressed_data = zlib.compress(tmp_file.read())
        with open(compressed_file_path, "wb") as compressed_file:
            compressed_file.write(compressed_data)

    def test_benchmark_basic(self):
        # More testcases can be added here
        testcases_filename = ["vdb_basic.json", "multithread.json"]

        for subtest_idx, filename in enumerate(testcases_filename, start=1):
            path = get_tests_data_file_path(filename)
            original_size = os.path.getsize(path)
            # More compressors can be added here
            other_results = [
                ("LZMA", self._benchmark_lzma(path)),
            ]
            with self.subTest(testcase=filename):
                vcompress_result = self._benchmark_vcompressor(path)
                self._print_result(filename, original_size,
                                   vcompress_result, other_results, subtest_idx=subtest_idx)

    @unittest.skipUnless(os.getenv("GITHUB_ACTIONS"), "skipped because not in github actions")
    def test_benchmark_large_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            origin_json_path = os.path.join(tmpdir, "large_fib.json")
            run_script = test_large_fib % (origin_json_path.replace("\\", "/"))
            self.template(
                ["python", "cmdline_test.py"], script=run_script, cleanup=False,
                expected_output_file=origin_json_path,
            )
            original_size = os.path.getsize(origin_json_path)
            other_results = [
                ("LZMA", self._benchmark_lzma(origin_json_path)),
                ("ZLIB", self._benchmark_zlib(origin_json_path)),
                ("VC+LZMA", self._benchmark_vcompressor_lzma(origin_json_path)),
                ("VC+ZLIB", self._benchmark_vcompressor_zlib(origin_json_path)),
            ]
            with self.subTest(testcase="large_fib.json"):
                vcompress_result = self._benchmark_vcompressor(origin_json_path)
                self._print_result("large_fib.json", original_size,
                                   vcompress_result, other_results)


class VCompressorCompare(unittest.TestCase):
    def assertEventsEqual(self, first: list, second: list, ts_margin: float):
        """
        This method is used to assert if two lists of events are equal,
        first and second are the two lists that we compare,
        ts_margin is the max timestamps diff that we tolerate.
        The timestamps may changed before/after the compression for more effective compression
        """
        self.assertEqual(len(first), len(second),
                         f"list length not equal, first is {len(first)} \n second is {len(second)}")
        first.sort(key=lambda i: i["ts"])
        second.sort(key=lambda i: i["ts"])
        for i in range(len(first)):
            self.assertEventEqual(first[i], second[i], ts_margin)

    def assertEventEqual(self, first: dict, second: dict, ts_margin: float):
        """
        This method is used to assert if two events are equal,
        first and second are the two events that we compare,
        ts_margin is the max timestamps diff that we tolerate.
        The timestamps may changed before/after the compression for more effective compression
        """
        self.assertEqual(len(first), len(second),
                         f"event length not equal, first is: \n {str(first)} \n second is: \n {str(second)}")
        for key, value in first.items():
            if key in ["ts", "dur"]:
                self.assertGreaterEqual(ts_margin, abs(value - second[key]),
                                        f"{key} diff is greater than margin")
            else:
                self.assertEqual(value, second[key], f"{key} is not equal")

    def assertThreadOrProcessEqual(self, first: list, second: list):
        """
        This method is used to assert if two lists of thread names are equal
        """
        self.assertEqual(len(first), len(second),
                         f"list length not equal, first is {len(first)} \n second is {len(second)}")
        first.sort(key=lambda i: (i["pid"], i["tid"]))
        second.sort(key=lambda i: (i["pid"], i["tid"]))
        for _ in range(len(first)):
            self.assertEqual(first, second,
                             f"{first} and {second} not equal")


test_counter_events = """
import threading
import time
import sys
from viztracer import VizTracer, VizCounter

tracer = VizTracer()
tracer.start()

class MyThreadSparse(threading.Thread):
    def run(self):
        counter = VizCounter(tracer, 'thread counter ' + str(self.ident))
        counter.a = sys.maxsize - 1
        time.sleep(0.01)
        counter.a = sys.maxsize * 2
        time.sleep(0.01)
        counter.a = -sys.maxsize + 2
        time.sleep(0.01)
        counter.a = -sys.maxsize * 2

main_counter = VizCounter(tracer, 'main counter')
thread1 = MyThreadSparse()
thread2 = MyThreadSparse()
main_counter.arg1 = 100.01
main_counter.arg2 = -100.01
main_counter.arg3 = 0.0
delattr(main_counter, \"arg3\")

thread1.start()
thread2.start()

threads = [thread1, thread2]

for thread in threads:
    thread.join()

main_counter.arg1 = 200.01
main_counter.arg2 = -200.01

tracer.stop()
tracer.save(output_file='%s')
"""


test_duplicated_timestamp = """
from viztracer import VizTracer
tracer = VizTracer(tracer_entries=1000000)
tracer.start()

def call_self(n):
    if n == 0:
        return
    return call_self(n-1)
for _ in range(10):
    call_self(1000)

tracer.stop()
tracer.save(output_file='%s')
"""


test_non_frequent_events = """
import threading
from viztracer import VizTracer, VizObject

tracer = VizTracer()
tracer.start()

class MyThreadSparse(threading.Thread):
    def run(self):
        viz_object = VizObject(tracer, 'thread object ' + str(self.ident))
        viz_object.a = 'test string 1'
        viz_object.a = 'test string 2'
        viz_object.a = {'test': 'string3'}
        viz_object.a = ['test string 4']
        tracer.log_instant("thread id " + str(self.ident))
        tracer.log_instant("thread id " + str(self.ident), "test instant string", "t")
        tracer.log_instant("thread id " + str(self.ident), {"b":"test"}, "g")
        tracer.log_instant("thread id " + str(self.ident), {"b":"test", "c":123}, "p")

main_viz_object = VizObject(tracer, 'main viz_object')
thread1 = MyThreadSparse()
thread2 = MyThreadSparse()
main_viz_object.arg1 = 100.01
main_viz_object.arg2 = -100.01
main_viz_object.arg3 = [100, -100]
delattr(main_viz_object, 'arg3')
tracer.log_instant("process")
tracer.log_instant("process", "test instant string", "t")
tracer.log_instant("process", {"b":"test"}, "g")
tracer.log_instant("process", {"b":"test", "c":123}, "p")

thread1.start()
thread2.start()
threads = [thread1, thread2]

for thread in threads:
    thread.join()

main_viz_object.arg1 = {100: "string1"}
main_viz_object.arg2 = {100: "string1", -100: "string2"}

tracer.stop()
tracer.save(output_file='%s')
"""


test_fee_args = """
from viztracer import VizTracer
tracer = VizTracer(log_func_args=True, log_func_retval=True)
tracer.start()

def fib(n):
    if n < 2:
        return 1
    return fib(n-1) + fib(n-2)
fib(10)
tracer.log_func_args = False
tracer.log_func_retval = False
fib(10)

tracer.stop()
tracer.save(output_file='%s')
"""


class TestVCompressorCorrectness(CmdlineTmpl, VCompressorCompare):

    def _generate_test_data(self, test_file):
        with tempfile.TemporaryDirectory() as tmpdir:
            cvf_path = os.path.join(tmpdir, "result.cvf")
            dup_json_path = os.path.join(tmpdir, "result.json")
            origin_json_path = get_tests_data_file_path(test_file)
            self.template(
                ["viztracer", "-o", cvf_path, "--compress", origin_json_path],
                expected_output_file=cvf_path,
                cleanup=False)
            self.template(
                ["viztracer", "-o", dup_json_path, "--decompress", cvf_path],
                expected_output_file=dup_json_path,
                cleanup=False)

            with open(origin_json_path, "r") as f:
                origin_json_data = json.load(f)
            with open(dup_json_path, "r") as f:
                dup_json_data = json.load(f)
        return origin_json_data, dup_json_data

    def _generate_test_data_by_script(self, run_script):
        with tempfile.TemporaryDirectory() as tmpdir:
            origin_json_path = os.path.join(tmpdir, "result.json")
            cvf_path = os.path.join(tmpdir, "result.cvf")
            dup_json_path = os.path.join(tmpdir, "recovery.json")
            run_script = run_script % (origin_json_path.replace("\\", "/"))
            self.template(
                ["python", "cmdline_test.py"],
                script=run_script,
                cleanup=False,
                expected_output_file=origin_json_path)
            self.template(
                ["viztracer", "-o", cvf_path, "--compress", origin_json_path],
                expected_output_file=cvf_path,
                cleanup=False)
            self.template(
                ["viztracer", "-o", dup_json_path, "--decompress", cvf_path],
                expected_output_file=dup_json_path,
                cleanup=False)
            with open(origin_json_path, "r") as f:
                origin_json_data = json.load(f)
            with open(dup_json_path, "r") as f:
                dup_json_data = json.load(f)
        return origin_json_data, dup_json_data

    def test_file_info(self):
        origin_json_data, dup_json_data = self._generate_test_data("multithread.json")
        self.assertEqual(origin_json_data["file_info"], dup_json_data["file_info"])

    def test_process_name(self):
        origin_json_data, dup_json_data = self._generate_test_data("multithread.json")
        origin_names = [i for i in origin_json_data["traceEvents"] if i["ph"] == "M" and i["name"] == "process_name"]
        dup_names = [i for i in dup_json_data["traceEvents"] if i["ph"] == "M" and i["name"] == "process_name"]
        self.assertThreadOrProcessEqual(origin_names, dup_names)

    def test_thread_name(self):
        origin_json_data, dup_json_data = self._generate_test_data("multithread.json")
        origin_names = [i for i in origin_json_data["traceEvents"] if i["ph"] == "M" and i["name"] == "thread_name"]
        dup_names = [i for i in dup_json_data["traceEvents"] if i["ph"] == "M" and i["name"] == "thread_name"]
        self.assertThreadOrProcessEqual(origin_names, dup_names)

    def test_fee(self):
        origin_json_data, dup_json_data = self._generate_test_data("multithread.json")
        origin_fee_events = {}

        # compare the data seperatly in different thread and process to avoid timestamp conflict
        for event in origin_json_data["traceEvents"]:
            if event["ph"] == "X":
                event_key = (event["pid"], event["tid"])
                if event_key not in origin_fee_events:
                    origin_fee_events[event_key] = []
                origin_fee_events[event_key].append(event)

        dup_fee_events = {}
        for event in dup_json_data["traceEvents"]:
            if event["ph"] == "X":
                event_key = (event["pid"], event["tid"])
                if event_key not in dup_fee_events:
                    self.assertIn(event_key, origin_fee_events, f"thread data {str(event_key)} not in origin data")
                    dup_fee_events[event_key] = []
                dup_fee_events[event_key].append(event)

        for key, value in origin_fee_events.items():
            self.assertIn(key, dup_fee_events, f"thread data {str(key)} not in decompressed data")
            self.assertEventsEqual(value, dup_fee_events[key], 0.011)

    def test_fee_with_args(self):
        origin_json_data, dup_json_data = self._generate_test_data_by_script(test_fee_args)
        origin_fee_events = [i for i in origin_json_data["traceEvents"] if i["ph"] == "X"]
        dup_fee_events = [i for i in dup_json_data["traceEvents"] if i["ph"] == "X"]
        self.assertEventsEqual(origin_fee_events, dup_fee_events, 0.011)

    def test_counter_events(self):
        origin_json_data, dup_json_data = self._generate_test_data_by_script(test_counter_events)
        origin_counter_events = [i for i in origin_json_data["traceEvents"] if i["ph"] == "C"]
        dup_counter_events = [i for i in dup_json_data["traceEvents"] if i["ph"] == "C"]
        self.assertEventsEqual(origin_counter_events, dup_counter_events, 0.011)

    def test_duplicated_timestamp(self):
        # We need to make sure there's no duplicated timestamp in decompressed data.
        # The test_duplicated_timestamp can generate timestamps with less difference.
        # So it is used to test if there would be duplicated in decompressed data.
        origin_json_data, dup_json_data = self._generate_test_data_by_script(test_duplicated_timestamp)
        origin_fee_events = [i for i in origin_json_data["traceEvents"] if i["ph"] == "X"]
        dup_fee_events = [i for i in dup_json_data["traceEvents"] if i["ph"] == "X"]
        dup_timestamp_list = [event["ts"] for event in dup_fee_events if event["ph"] == "X"]
        dup_timestamp_set = set(dup_timestamp_list)
        self.assertEqual(len(dup_timestamp_list), len(dup_timestamp_set), "There's duplicated timestamp")
        self.assertEventsEqual(origin_fee_events, dup_fee_events, 0.011)

    def test_non_frequent_events(self):
        # We still have instant event and VizObject that are not frequently used
        # This test is a basic coverage
        origin_json_data, dup_json_data = self._generate_test_data_by_script(test_non_frequent_events)
        ph_filter = ["X", "M", "C"]  # these are compressed by other methods
        origin_events = [i for i in origin_json_data["traceEvents"] if i["ph"] not in ph_filter]
        dup_events = [i for i in dup_json_data["traceEvents"] if i["ph"] not in ph_filter]
        self.assertEventsEqual(origin_events, dup_events, 0.011)
