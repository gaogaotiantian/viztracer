# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

from viztracer import VizTracer
import unittest


class TestInvalidArgs(unittest.TestCase):
    def test_invalid_args(self):
        invalid_args = {
            "verbose": ["hello", 0.1],
            "pid_suffix": ["hello", 1, "True"],
            "max_stack_depth": ["0.3", "hello", 1.5],
            "include_files": ["./src"],
            "exclude_files": ["./src"],
            "ignore_c_function": ["hello", 1, "True"],
            "log_print": ["hello", 1, "True"],
            "log_return_value": ["hello", 1, "True"]
        }
        tracer = VizTracer()
        for args, vals in invalid_args.items():
            for val in vals:
                with self.assertRaises(ValueError):
                    tracer.__setattr__(args, val)
