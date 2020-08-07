import unittest
import random
import time
import cProfile
from codesnap import CodeSnap

class TestPerformance(unittest.TestCase):
    def do_one_function(self, func):
        # the original speed
        origin_start = time.perf_counter()
        func()
        origin_end = time.perf_counter()

        # With codesnap
        snap = CodeSnap()
        snap.start()
        instrumented_start = time.perf_counter()
        func()
        instrumented_end = time.perf_counter()
        snap.stop()
        entries1 = snap.parse()
        snap.clear()

        # With codesnap + c tracer
        snap = CodeSnap("c")
        snap.start()
        c_instrumented_start = time.perf_counter()
        func()
        c_instrumented_end = time.perf_counter()
        snap.stop()
        entries2 = snap.parse()
        snap.clear()

        # With cProfiler
        pr = cProfile.Profile()
        pr.enable()
        cprofile_start = time.perf_counter()
        func()
        cprofile_end = time.perf_counter()
        pr.disable()

        if func.__name__ != "qsort":
            self.assertEqual(entries1, entries2)

        origin = origin_end - origin_start
        instrumented = instrumented_end - instrumented_start
        c_instrumented = c_instrumented_end - c_instrumented_start
        cprofile = cprofile_end - cprofile_start
        print("{:10}({}, {}): {:.9f} vs {:.9f}({:.2f})[py] vs {:.9f}({:.2f})[c] vs {:.9f}({:.2f})[cProfile]".format(func.__name__, 
            entries1, entries2, origin, instrumented, instrumented / origin, c_instrumented, c_instrumented / origin,
            cprofile, cprofile / origin))
    
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
            def TowerOfHanoi(n , source, destination, auxiliary): 
                if n==1: 
                    return
                TowerOfHanoi(n-1, source, auxiliary, destination) 
                TowerOfHanoi(n-1, auxiliary, destination, source) 
            TowerOfHanoi(12, "A", "B", "C")
        self.do_one_function(hanoi)
        