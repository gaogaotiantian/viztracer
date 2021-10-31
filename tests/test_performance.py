# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

import cProfile
import gc
import io
import os
import random
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


class TestPerformance(BaseTmpl):
    def do_one_function(self, func):
        gc.collect()
        gc.disable()
        # the original speed
        with Timer() as t:
            func()
            origin = t.get_time()

        gc.collect()
        # With viztracer + c tracer + vdb
        tracer = VizTracer(verbose=0, vdb=True)
        tracer.start()
        with Timer() as t:
            func()
            instrumented_c_vdb = t.get_time()
        tracer.stop()
        with Timer() as t:
            tracer.parse()
            instrumented_c_vdb_parse = t.get_time()
        with Timer() as t:
            tracer.save(output_file="tmp.json")
            instrumented_c_vdb_json = t.get_time()
        os.remove("tmp.json")
        tracer.clear()

        gc.collect()
        # With viztracer + c tracer
        tracer = VizTracer(verbose=0)
        tracer.start()
        with Timer() as t:
            func()
            instrumented_c = t.get_time()
        tracer.stop()
        with Timer() as t:
            tracer.parse()
            instrumented_c_parse = t.get_time()
        with Timer() as t:
            with io.StringIO() as s:
                tracer.save(s)
            instrumented_c_json = t.get_time()
        tracer.clear()

        gc.collect()
        # With cProfiler
        pr = cProfile.Profile()
        pr.enable()
        with Timer() as t:
            func()
            cprofile = t.get_time()
        pr.disable()

        gc.enable()

        def time_str(name, origin, instrumented):
            return "{:.9f}({:.2f})[{}] ".format(instrumented, instrumented / origin, name)

        print(time_str("origin", origin, origin))
        print(time_str("c+vdb", origin, instrumented_c_vdb)
              + time_str("parse", origin, instrumented_c_vdb_parse)
              + time_str("json", origin, instrumented_c_vdb_json))
        print(time_str("c", origin, instrumented_c)
              + time_str("parse", origin, instrumented_c_parse)
              + time_str("json", origin, instrumented_c_json))
        print(time_str("cProfile", origin, cprofile))

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

        print("Filter performance:")
        print("Baseline:        {:.9f}(1)".format(baseline))
        print("Include:         {:.9f}({:.2f})".format(include_files, include_files / baseline))
        print("Max stack depth: {:.9f}({:.2f})".format(max_stack_depth, max_stack_depth / baseline))

    def test_hanoi(self):
        def hanoi():
            def TowerOfHanoi(n, source, destination, auxiliary):
                if n == 1:
                    return
                TowerOfHanoi(n - 1, source, auxiliary, destination)
                TowerOfHanoi(n - 1, auxiliary, destination, source)
            TowerOfHanoi(12, "A", "B", "C")
        self.do_one_function(hanoi)
