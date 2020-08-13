import unittest
import random
import time
import cProfile
from viztracer import VizTracer


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


class TestPerformance(unittest.TestCase):
    def do_one_function(self, func):
        # the original speed
        with Timer() as t:
            func()
            origin = t.get_time()

        # With viztracer + python tracer
        tracer = VizTracer("python", verbose=0)
        tracer.start()
        with Timer() as t:
            func()
            instrumented = t.get_time()
        tracer.stop()
        with Timer() as t:
            entries1 = tracer.parse()
            instrumented_parse = t.get_time()
        with Timer() as t:
            tracer.generate_json()
            instrumented_json = t.get_time()
        tracer.clear()

        # With viztracer + c tracer
        tracer = VizTracer("c", verbose=0)
        tracer.start()
        with Timer() as t:
            func()
            instrumented_c = t.get_time()
        tracer.stop()
        with Timer() as t:
            entries2 = tracer.parse()
            instrumented_c_parse = t.get_time()
        with Timer() as t:
            tracer.generate_json()
            instrumented_c_json = t.get_time()
        tracer.clear()

        # With cProfiler
        pr = cProfile.Profile()
        pr.enable()
        with Timer() as t:
            func()
            cprofile = t.get_time()
        pr.disable()

        if func.__name__ != "qsort":
            self.assertEqual(entries1, entries2)

        def time_str(name, origin, instrumented):
            return "{:.9f}({:.2f})[{}] ".format(instrumented, instrumented / origin, name)

        print("{:10}({}, {}):".format(func.__name__, entries1, entries2))
        print(time_str("origin", origin, origin))
        print(time_str("py", origin, instrumented) + time_str("parse", origin, instrumented_parse) + time_str("json", origin, instrumented_json))
        print(time_str("c", origin, instrumented_c) + time_str("parse", origin, instrumented_c_parse) + time_str("json", origin, instrumented_c_json))
        print(time_str("cProfile", origin, cprofile))

    def test_fib(self):
        def fib():
            def _fib(n):
                if n <= 1:
                    return 1
                return _fib(n-1) + _fib(n-2)
            return _fib(17)
        self.do_one_function(fib)

    def test_slow_fib(self):
        def slow_fib():
            def _fib(n):
                if n <= 1:
                    return 1
                time.sleep(0.00001)
                return _fib(n-1) + _fib(n-2)
            return _fib(13)
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
            arr = [random.randrange(100000) for _ in range(1000)]
            quicksort(arr)
        self.do_one_function(qsort)

    def test_hanoi(self):
        def hanoi():
            def TowerOfHanoi(n, source, destination, auxiliary):
                if n == 1:
                    return
                TowerOfHanoi(n-1, source, auxiliary, destination)
                TowerOfHanoi(n-1, auxiliary, destination, source)
            TowerOfHanoi(12, "A", "B", "C")
        self.do_one_function(hanoi)
