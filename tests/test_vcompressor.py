# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt


import os
import logging
import tempfile
import lzma
from shutil import copyfileobj
from typing import Optional

from .cmdline_tmpl import CmdlineTmpl
from .util import get_json_file_path


class TestVCompressor(CmdlineTmpl):
    def test_basic(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cvf_path = os.path.join(tmpdir, "result.cvf")
            dup_json_path = os.path.join(tmpdir, "result.json")
            self.template(
                ["viztracer", "-o", cvf_path, "--compress", get_json_file_path("multithread.json")],
                expected_output_file=cvf_path, cleanup=False
            )

            self.template(
                ["viztracer", "-o", dup_json_path, "--decompress", cvf_path],
                expected_output_file=dup_json_path
            )


class TestVCompressorPerformance(CmdlineTmpl):

    def _human_readable_filesize(self, filesize: int) -> str:
        units = [("PB", 1 << 50), ("TB", 1 << 40), ("GB", 1 << 30), ("MB", 1 << 20), ("KB", 1 << 10)]
        for unit_name, unit_base in units:
            norm_size = filesize / unit_base
            if norm_size >= 0.8:
                return "{:8.2f}{}".format(norm_size, unit_name)
        return "{:8.2f}B".format(filesize)

    def _print_cr_result(self,
                         filename: str,
                         original_size: int,
                         baseline_size: int,
                         vcompressor_size: int,
                         baseline_name: str = "LZMA",
                         subtest_idx: Optional[int] = None):
        if subtest_idx is None:
            logging.info("On file \"{}\":".format(filename))
        else:
            logging.info("{}. On file \"{}\":".format(subtest_idx, filename))
        logging.info("    [Space] ({} as baseline)".format(baseline_name))
        logging.info("      Uncompressed: {}".format(self._human_readable_filesize(original_size)))
        logging.info("      Baseline:    {}(1.00)".format(self._human_readable_filesize(baseline_size)))
        logging.info("      VCompressor: {}({:.2f})".format(self._human_readable_filesize(vcompressor_size),
                                                            vcompressor_size / baseline_size))

    def get_filesize_vcompressor(self, original_file_path: str) -> int:
        '''Use the demo file to get the file size (in bytes) after VCompressor compression.'''

        with tempfile.TemporaryDirectory() as tmpdir:
            compressed_file_path = os.path.join(tmpdir, "result.cvf")
            self.template(
                ["viztracer", "-o", compressed_file_path, "--compress", original_file_path],
                expected_output_file=compressed_file_path, cleanup=False
            )
            compressed_file_size = os.path.getsize(compressed_file_path)
        return compressed_file_size

    def get_filesize_lzma(self, original_file_path: str, compression_level: int = lzma.PRESET_DEFAULT) -> int:
        '''Use the demo file to get the file size (in bytes) after lzma compression, as a baseline.'''

        with tempfile.TemporaryDirectory() as tmpdir:
            compressed_file_path = os.path.join(tmpdir, "result.xz")
            with open(original_file_path, "rb") as original_file, \
                 lzma.open(compressed_file_path, "wb", preset=compression_level) as compressed_file:
                copyfileobj(original_file, compressed_file)
            compressed_file_size = os.path.getsize(compressed_file_path)
        return compressed_file_size

    def test_benchmark_basic(self):
        # More testcases can be added here
        testcases_filename = ["vdb_basic.json", "multithread.json"]

        for subtest_idx, filename in enumerate(testcases_filename, start=1):
            path = get_json_file_path(filename)
            original_size = os.path.getsize(path)
            baseline_size = self.get_filesize_lzma(path)
            with self.subTest(testcase=filename):
                vcompress_size = self.get_filesize_vcompressor(path)
                self._print_cr_result(filename, original_size, baseline_size, vcompress_size, subtest_idx=subtest_idx)
