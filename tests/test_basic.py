# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

import builtins
import json
import multiprocessing
import os
import subprocess
import sys
import tempfile
import time
import unittest

from viztracer import VizTracer, get_tracer, ignore_function, trace_and_save

from .base_tmpl import BaseTmpl


def fib(n):
    if n == 1 or n == 0:
        return 1
    return fib(n - 1) + fib(n - 2)


class TestTracerBasic(BaseTmpl):
    def test_construct(self):
        def fib(n):
            if n == 1 or n == 0:
                return 1
            return fib(n - 1) + fib(n - 2)
        t = VizTracer()
        t.verbose = 0
        t.start()
        fib(5)
        t.stop()
        t.parse()
        self.assertEventNumber(t.data, 15)

    def test_builtin_func(self):
        import random

        def fun(n):
            for _ in range(n):
                random.randrange(n)
        t = VizTracer(ignore_c_function=True)
        t.verbose = 0
        t.start()
        fun(10)
        t.stop()
        t.parse()
        self.assertEventNumber(t.data, 21)

    def test_clear(self):
        def fib(n):
            if n == 1 or n == 0:
                return 1
            return fib(n - 1) + fib(n - 2)
        t = VizTracer()
        t.verbose = 0
        t.start()
        fib(5)
        t.stop()
        t.clear()
        t.parse()
        self.assertEventNumber(t.data, 0)


class TestVizTracerBasic(BaseTmpl):
    def test_run(self):
        snap = VizTracer(verbose=0)
        snap.run("import random; random.randrange(10)", output_file="test_run.json")
        self.assertFileExists("test_run.json")
        os.remove("test_run.json")

    def test_with(self):
        with VizTracer(output_file="test_with.json", verbose=0) as _:
            fib(10)
        self.assertFileExists("test_with.json")
        os.remove("test_with.json")

        had_exception = False
        try:
            with VizTracer(output_file="test_with.json", verbose=0):
                _ = 1 / 0
        except ZeroDivisionError:
            had_exception = True
        self.assertFileExists("test_with.json")
        os.remove("test_with.json")
        self.assertTrue(had_exception)

    def test_name_with_class(self):
        class A:
            def f(self):
                pass

        tracer = VizTracer(verbose=0)
        tracer.start()
        A().f()
        tracer.stop()
        tracer.parse()
        if sys.version_info >= (3, 11):
            self.assertIn("TestVizTracerBasic.test_name_with_class.<locals>.A.f",
                          [e["name"].split()[0] for e in tracer.data["traceEvents"]])
        else:
            self.assertIn("f",
                          [e["name"].split()[0] for e in tracer.data["traceEvents"]])

    def test_tracer_entries(self):
        tracer = VizTracer(tracer_entries=10)
        tracer.start()
        fib(10)
        tracer.stop()
        tracer.parse()
        self.assertEventNumber(tracer.data, 10)

    def test_unfinished_function(self):
        def f():
            tracer.stop()
            tracer.parse()

        tracer = VizTracer(tracer_entries=10)
        tracer.start()
        f()
        self.assertEventNumber(tracer.data, 1)
        self.assertEqual(tracer.data["traceEvents"][-1]["ph"], "B")

    def test_save(self):
        tracer = VizTracer(tracer_entries=10)
        tracer.start()
        fib(5)
        tracer.stop()
        tracer.parse()
        with tempfile.TemporaryDirectory() as tmpdir:
            for file_path in [["result.html"], ["result2.json"], ["new_dir", "result2.json"], ["result3.gz"]]:
                path = os.path.join(tmpdir, *file_path)
                tracer.start()
                fib(5)
                tracer.stop()
                tracer.save(path)
                self.assertFileExists(path)

    def test_save_while_enabled(self):
        tracer = VizTracer(tracer_entries=10)
        with tempfile.TemporaryDirectory() as tmpdir:
            tracer.start()
            fib(5)
            tracer.save(os.path.join(tmpdir, "result.json"))
            tracer.clear()
            fib(5)
            tracer.stop()
            tracer.parse()
            self.assertEventNumber(tracer.data, 10)

    def test_time_sanity(self):
        tracer = VizTracer(tracer_entries=10)
        tracer.start()
        start_real = time.perf_counter_ns() / 1000
        start = tracer.getts()
        time.sleep(0.3)
        end = tracer.getts()
        end_real = time.perf_counter_ns() / 1000
        tracer.stop()
        tracer.parse()
        time_events = [e for e in tracer.data["traceEvents"] if e["name"] == "time.sleep"]
        self.assertEqual(len(time_events), 1)
        self.assertAlmostEqual(time_events[0]["dur"], end - start, delta=0.003e6)
        self.assertAlmostEqual(end - start, end_real - start_real, delta=0.003e6)

    def test_sync_marker(self):
        tracer = VizTracer()
        tracer.start()
        tracer.set_sync_marker()
        fib(5)
        tracer.stop()
        tracer.parse()
        self.assertIn("sync_marker", tracer.data["viztracer_metadata"])


class TestInstant(BaseTmpl):
    def test_addinstant(self):
        tracer = VizTracer(verbose=0)
        tracer.start()
        tracer.add_instant('instant - "karma": True')
        tracer.add_instant('instant', args={"karma": True})
        tracer.stop()
        tracer.parse()
        self.assertEventNumber(tracer.data, 2)

    def test_invalid_scope(self):
        tracer = VizTracer(verbose=0)
        tracer.start()
        with self.assertRaises(ValueError):
            tracer.add_instant('instant - "karma": True', scope="invalid")
        tracer.stop()
        tracer.clear()


class TestFunctionArg(BaseTmpl):
    def test_addfunctionarg(self):
        def f(tracer):
            tracer.add_func_args("hello", "world")
        tracer = VizTracer(verbose=0)
        tracer.start()
        f(tracer)
        tracer.stop()
        tracer.parse()
        events = [e for e in tracer.data["traceEvents"] if e["ph"] != "M"]
        self.assertTrue("args" in events[0]
                        and "hello" in events[0]["args"])


class TestDecorator(BaseTmpl):
    def test_pause_resume(self):
        tracer = VizTracer(verbose=0)

        def f():
            pass

        @ignore_function(tracer=tracer)
        def ignore(n):
            if n == 0:
                return 1
            return ignore(n - 1) + 1
        tracer.start()
        ignore(10)
        f()
        tracer.stop()
        tracer.parse()
        self.assertEventNumber(tracer.data, 1)

    def test_ignore_function_without_global_tracer(self):

        @ignore_function
        def f():
            return

        if "__viz_tracer__" in builtins.__dict__:
            builtins.__dict__.pop("__viz_tracer__")

        tracer = VizTracer(register_global=False, verbose=0)

        tracer.start()
        with self.assertRaises(NameError):
            f()

    def test_trace_and_save(self):
        if os.getenv("GITHUB_ACTIONS"):
            timeout = 60
        else:
            timeout = 20
        with tempfile.TemporaryDirectory() as tmp_dir:

            @trace_and_save(output_dir=tmp_dir, verbose=0)
            def my_function(n):
                fib(n)

            for _ in range(3):
                time.sleep(0.0001)
                my_function(10)

            def t():
                self.assertEqual(len([f for f in os.listdir(tmp_dir) if f.endswith(".json")]), 3)

            self.assertTrueTimeout(lambda: self.assertFalse(multiprocessing.active_children()), timeout)
            self.assertTrueTimeout(t, timeout)

        with tempfile.TemporaryDirectory() as tmp_dir:

            @trace_and_save(output_dir=os.path.join(tmp_dir, "new_dir"), verbose=0)
            def cover_mkdir():
                return

            cover_mkdir()

            def t():
                self.assertEqual(len(os.listdir(os.path.join(tmp_dir, "new_dir"))), 1)

            self.assertTrueTimeout(lambda: self.assertFalse(multiprocessing.active_children()), timeout)
            self.assertTrueTimeout(t, timeout)

        if sys.platform in ["linux", "linux2", "darwin"]:
            # ls does not work on windows. Don't bother fixing it because it's just coverage test
            @trace_and_save
            def my_function2(n):
                fib(n)
            my_function2(10)

            def t1():
                a = subprocess.run(["ls result_my_function2*.json"],
                                   shell=True,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
                self.assertEqual(a.returncode, 0)
            self.assertTrueTimeout(t1, timeout)

            def t2():
                a = subprocess.run(["rm result_my_function2*.json"],
                                   shell=True,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
                self.assertEqual(a.returncode, 0)
            self.assertTrueTimeout(t2, timeout)


class TestLogPrint(BaseTmpl):
    def test_log_print(self):
        tracer = VizTracer(log_print=True, verbose=0)
        tracer.start()
        print("hello")
        print("hello")
        print("hello")
        print("hello")
        tracer.stop()
        tracer.parse()
        self.assertEventNumber(tracer.data, 4)


class TestForkSave(BaseTmpl):
    @unittest.skipUnless(multiprocessing.get_start_method() == "fork", "Fork save only works with fork")
    def test_basic(self):
        def fib(n):
            if n == 1 or n == 0:
                return 1
            return fib(n - 1) + fib(n - 2)
        t = VizTracer(verbose=0)
        processes = {}
        for i in range(5, 10):
            t.start()
            fib(i)
            t.stop()
            t.parse()
            processes[i] = t.fork_save(output_file=str(i) + ".json")

        expected = {
            5: 15,
            6: 25,
            7: 41,
            8: 67,
            9: 109,
        }
        pid = None
        for i in range(5, 10):
            path = str(i) + ".json"
            processes[i].join()
            self.assertFileExists(path, timeout=10)
            with open(path) as f:
                data = json.load(f)
            os.remove(path)
            self.assertEventNumber(data, expected[i])
            if pid is None:
                pid = data["traceEvents"][0]["pid"]
            else:
                self.assertEqual(data["traceEvents"][0]["pid"], pid)

    @unittest.skipUnless(multiprocessing.get_start_method() != "fork", "Fork save only works with fork")
    def test_non_fork_platform(self):
        tracer = VizTracer(verbose=0)
        with self.assertRaises(RuntimeError):
            tracer.fork_save("result.json")


class TestGlobalTracer(BaseTmpl):
    def test_get_tracer(self):
        if "__viz_tracer__" in builtins.__dict__:
            builtins.__dict__.pop("__viz_tracer__")
        with self.assertRaises(NameError):
            _ = __viz_tracer__  # noqa: F821
        self.assertIs(get_tracer(), None)
        tracer = VizTracer(verbose=0)
        builtins.__dict__["__viz_tracer__"] = tracer
        self.assertIs(get_tracer(), tracer)
        builtins.__dict__.pop("__viz_tracer__")
