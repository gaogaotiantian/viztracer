import logging
from viztracer import get_tracer, VizLoggingHandler


def fib(n):
    if n < 2:
        logging.warn("Base case, return 1")
        return 1
    logging.info("Recursive, working on {}".format(n))
    return fib(n - 1) + fib(n - 2)


handler = VizLoggingHandler()
handler.setTracer(get_tracer())
logging.basicConfig(handlers=[handler], level=logging.INFO)

fib(7)
