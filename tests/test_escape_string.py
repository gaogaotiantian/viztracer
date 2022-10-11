from .cmdline_tmpl import CmdlineTmpl

file_with_escape_string = """
import threading
import time
from viztracer import get_tracer, VizObject, VizCounter

obj = VizObject(get_tracer(), "test \\\\ \\\" \\b \\f \\n \\r \\t")
obj.test = "test \\\\ \\\" \\b \\f \\n \\r \\t"
counter = VizCounter(get_tracer(), "test \\\\ \\\" \\b \\f \\n \\r \\t")
counter.test = 10

def fib(n):
    if n < 2:
        return 1
    time.sleep(0.0000001)
    return fib(n - 1) + fib(n - 2)


class MyThread(threading.Thread):
    def run(self):
        fib(7)


thread1 = MyThread(name = "test \\\\ \\\" \\b \\f \\n \\r \\t")
thread2 = MyThread()
thread3 = MyThread()
thread4 = MyThread()

# !viztracer: log_instant("test \\\\ \\\" \\b \\f \\n \\r \\t", args={"test": "test"})
# !viztracer: log_instant("test \\\\ \\\" \\b \\f \\n \\r \\t", args={"test": "test \\\\ \\\" \\b \\f \\n \\r \\t"})
# !viztracer: log_instant("test \\\\ \\\" \\b \\f \\n \\r \\t", args={"test \\\\ \\\" \\b \\f \\n \\r \\t": "test"})
# !viztracer: log_var("test \\\\ \\\" \\b \\f \\n \\r \\t", 10)
# !viztracer: log_event("test \\\\ \\\" \\b \\f \\n \\r \\t")

thread1.start()
thread2.start()
thread3.start()
thread4.start()

threads = [thread1, thread2, thread3, thread4]

for thread in threads:
    thread.join()
"""


class TestEscapeString(CmdlineTmpl):
    def test_escape_string(self):
        self.template(["viztracer", "-o", "result.json", "--magic_comment", "--dump_raw", "cmdline_test.py"],
                      expected_output_file="result.json",
                      script=file_with_escape_string, expected_stdout=".*Total Entries:.*")
