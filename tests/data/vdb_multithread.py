import threading
import time

from viztracer import VizTracer, ignore_function


@ignore_function
def ig(n):
    if n < 2:
        return 1
    return ig(n - 1) + ig(n - 2)


def fib(n):
    if n < 2:
        return 1
    time.sleep(0.0000001)
    return fib(n - 1) + fib(n - 2)


class MyThread(threading.Thread):
    def run(self):
        fib(7)


tracer = VizTracer(verbose=1)
tracer.start()

thread1 = MyThread()
thread2 = MyThread()
thread3 = MyThread()
thread4 = MyThread()

thread1.start()
thread2.start()
thread3.start()
thread4.start()

threads = [thread1, thread2, thread3, thread4]

for thread in threads:
    thread.join()

tracer.stop()
tracer.save(output_file="vdb_multithread.json")
