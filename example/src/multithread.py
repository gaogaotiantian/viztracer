import os
import threading
import time

from viztracer import VizTracer


def fib(n):
    if n < 2:
        return 1
    time.sleep(0.0000001)
    return fib(n - 1) + fib(n - 2)


class MyThread(threading.Thread):
    def run(self):
        fib(7)


with VizTracer(output_file=os.path.join(os.path.dirname(__file__), "../", "json/multithread.json"),
               file_info=True) as _:
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
