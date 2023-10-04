# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

import contextlib
import cProfile
import gc
import logging
import os
import random
import tempfile
import time

from viztracer import VizTracer

from .base_tmpl import BaseTmpl


class Timer:
    def __init__(self):
        self.timer = 0

    def __enter__(self):
        self.timer = time.perf_counter()
        return self

    def __exit__(self, type, value, trace):
        pass

    def get_time(self):
        return time.perf_counter() - self.timer


class BenchmarkTimer:
    def __init__(self):
        self.timer_baseline = None
        self.timer_experiments = {}
        self._set_up_funcs = []

    @contextlib.contextmanager
    def time(self, title, section=None, baseline=False):
        for func, args, kwargs in self._set_up_funcs:
            func(*args, **kwargs)
        start_time = time.perf_counter()
        try:
            yield
        finally:
            end_time = time.perf_counter()
            data = {
                "dur": end_time - start_time,
                "section": section,
            }
            if baseline:
                self.timer_baseline = data
            else:
                if title not in self.timer_experiments:
                    self.timer_experiments[title] = []
                self.timer_experiments[title].append(data)

    def print_result(self):
        def time_str(baseline, experiment):
            return f"{experiment['dur']:.9f}({experiment['dur'] / baseline['dur']:.2f})[{experiment['section']}]"
        for experiments in self.timer_experiments.values():
            logging.info(" ".join([time_str(self.timer_baseline, experiment) for experiment in experiments]))

    def add_set_up_func(self, func, *args, **kwargs):
        self._set_up_funcs.append((func, args, kwargs))


class TestPerformance(BaseTmpl):
    def do_one_function(self, func):
        bm_timer = BenchmarkTimer()
        bm_timer.add_set_up_func(gc.collect)
        gc.collect()
        gc.disable()
        # the original speed
        with bm_timer.time("baseline", "baseline", baseline=True):
            func()

        # With viztracer + c tracer
        tracer = VizTracer(verbose=0)
        tracer.start()
        with bm_timer.time("c", "c"):
            func()
        tracer.stop()
        with bm_timer.time("c", "parse"):
            tracer.parse()
        with tempfile.TemporaryDirectory() as tmpdir:
            ofile = os.path.join(tmpdir, "result.json")
            with bm_timer.time("c", "save"):
                tracer.save(output_file=ofile)
        tracer.start()
        func()
        tracer.stop()
        with tempfile.TemporaryDirectory() as tmpdir:
            ofile = os.path.join(tmpdir, "result.json")
            with bm_timer.time("c", "dump"):
                tracer.dump(ofile)
        tracer.clear()

        # With cProfiler
        pr = cProfile.Profile()
        pr.enable()
        with bm_timer.time("cProfile", "cProfile"):
            func()
        pr.disable()

        gc.enable()

        bm_timer.print_result()

    def test_fib(self):
        def fib():
            def _fib(n):
                if n <= 1:
                    return 1
                return _fib(n - 1) + _fib(n - 2)
            return _fib(23)
        self.do_one_function(fib)

    def test_slow_fib(self):
        def slow_fib():
            def _fib(n):
                if n <= 1:
                    return 1
                time.sleep(0.00001)
                return _fib(n - 1) + _fib(n - 2)
            return _fib(15)
        self.do_one_function(slow_fib)

    def test_qsort(self):
        def qsort():
            def quicksort(array):
                if len(array) < 2:
                    return array

                low, same, high = [], [], []

                pivot = array[random.randint(0, len(array) - 1)]

                for item in array:
                    if item < pivot:
                        low.append(item)
                    elif item == pivot:
                        same.append(item)
                    elif item > pivot:
                        high.append(item)

                return quicksort(low) + same + quicksort(high)
            arr = [random.randrange(100000) for _ in range(5000)]
            quicksort(arr)
        self.do_one_function(qsort)

    def test_hanoi(self):
        def hanoi():
            def TowerOfHanoi(n, source, destination, auxiliary):
                if n == 1:
                    return
                TowerOfHanoi(n - 1, source, auxiliary, destination)
                TowerOfHanoi(n - 1, auxiliary, destination, source)
            TowerOfHanoi(16, "A", "B", "C")
        self.do_one_function(hanoi)

    def test_list(self):
        def list_operation():
            def ListOperation(n):
                if n == 1:
                    return [1]

                ret = ListOperation(n - 1)
                for i in range(n):
                    ret.append(i)
                return ret
            ListOperation(205)
        self.do_one_function(list_operation)

    def test_float(self):
        from math import cos, sin, sqrt

        class Point():
            __slots__ = ('x', 'y', 'z')

            def __init__(self, i):
                self.x = x = sin(i)
                self.y = cos(i) * 3
                self.z = (x * x) / 2

            def __repr__(self):
                return f"<Point: x={self.x}, y={self.y}, z={self.z}>"

            def normalize(self):
                x = self.x
                y = self.y
                z = self.z
                norm = sqrt(x * x + y * y + z * z)
                self.x /= norm
                self.y /= norm
                self.z /= norm

            def maximize(self, other):
                self.x = self.x if self.x > other.x else other.x
                self.y = self.y if self.y > other.y else other.y
                self.z = self.z if self.z > other.z else other.z
                return self

        def maximize(points):
            next = points[0]
            for p in points[1:]:
                next = next.maximize(p)
            return next

        def benchmark():
            n = 100
            points = [None] * n
            for i in range(n):
                points[i] = Point(i)
            for p in points:
                p.normalize()
            return maximize(points)

        self.do_one_function(benchmark)


class TestFilterPerformance(BaseTmpl):
    def do_one_function(self, func):
        tracer = VizTracer(verbose=0)
        tracer.start()
        with Timer() as t:
            func()
            baseline = t.get_time()
        tracer.stop()
        tracer.cleanup()

        tracer.include_files = ["/"]
        tracer.start()
        with Timer() as t:
            func()
            include_files = t.get_time()
        tracer.stop()
        tracer.cleanup()

        tracer.include_files = []
        tracer.max_stack_depth = 200
        tracer.start()
        with Timer() as t:
            func()
            max_stack_depth = t.get_time()
        tracer.stop()
        tracer.cleanup()

        logging.info("Filter performance:")
        logging.info(f"Baseline:        {baseline:.9f}(1)")
        logging.info(f"Include:         {include_files:.9f}({include_files / baseline:.2f})")
        logging.info(f"Max stack depth: {max_stack_depth:.9f}({max_stack_depth / baseline:.2f})")

    def test_hanoi(self):
        def hanoi():
            def TowerOfHanoi(n, source, destination, auxiliary):
                if n == 1:
                    return
                TowerOfHanoi(n - 1, source, auxiliary, destination)
                TowerOfHanoi(n - 1, auxiliary, destination, source)
            TowerOfHanoi(12, "A", "B", "C")
        self.do_one_function(hanoi)
