# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

from viztracer.event_base import _EventBase
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
            "log_return_value": ["hello", 1, "True"],
            "log_gc": ["hello", 1, "True"],
            "log_function_args": ["hello", 1, "True"],
            "novdb": ["hello", 1, "True"]
        }
        tracer = VizTracer()
        for args, vals in invalid_args.items():
            for val in vals:
                with self.assertRaises(ValueError):
                    tracer.__setattr__(args, val)


class TestInvalidOperation(unittest.TestCase):
    def test_generate_without_data(self):
        tracer = VizTracer()
        with self.assertRaises(Exception):
            tracer.generate_json()

    def test_save_invalid_format(self):
        tracer = VizTracer()
        tracer.start()
        _ = len([1, 2])
        tracer.stop()
        with self.assertRaises(Exception):
            tracer.save("test.invalid")


class TestUseEventBase(unittest.TestCase):
    def test_use_event_base(self):
        event = _EventBase(None)
        with self.assertRaises(NotImplementedError):
            event.log()
