# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

from viztracer import VizTracer
from viztracer.event_base import _EventBase

from .base_tmpl import BaseTmpl


class TestInvalidArgs(BaseTmpl):
    def test_invalid_args(self):
        invalid_args = {
            "verbose": ["hello", 0.1],
            "pid_suffix": ["hello", 1, "True"],
            "max_stack_depth": ["0.3", "hello", 1.5],
            "include_files": ["./src"],
            "exclude_files": ["./src"],
            "ignore_c_function": ["hello", 1, "True"],
            "log_print": ["hello", 1, "True"],
            "log_func_retval": ["hello", 1, "True"],
            "log_gc": ["hello", 1, "True"],
            "log_func_args": ["hello", 1, "True"],
            "min_duration": ["0.1.0", "12", "3us"],
            "ignore_frozen": ["hello", 1, "True"],
            "log_async": ["hello", 1, "True"],
        }
        tracer = VizTracer(verbose=0)
        for args, vals in invalid_args.items():
            for val in vals:
                self.assertRaises(ValueError, tracer.__setattr__, args, val)


class TestInvalidOperation(BaseTmpl):
    def test_generate_without_data(self):
        tracer = VizTracer(verbose=0)
        with self.assertRaises(Exception):
            tracer.generate_json()

    def test_save_invalid_format(self):
        tracer = VizTracer(verbose=0)
        tracer.start()
        _ = len([1, 2])
        tracer.stop()
        with self.assertRaises(Exception):
            tracer.save("test.invalid")

    def test_add_invalid_variable(self):
        tracer = VizTracer(verbose=0)
        tracer.start()
        with self.assertRaises(Exception):
            tracer.add_variable("a", 1, event="invalid")
        with self.assertRaises(Exception):
            tracer.add_variable("a", "str", event="counter")


class TestUseEventBase(BaseTmpl):
    def test_use_event_base(self):
        event = _EventBase(None)
        with self.assertRaises(NotImplementedError):
            event.log()
