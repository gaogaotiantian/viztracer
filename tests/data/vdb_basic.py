# import wthell
from viztracer import VizCounter, VizTracer, VizObject
# from wthell import wth


def h(a):
    counter.a = a
    ob.b = 3
    return 1 / (a - 3)


def g(a, b):
    a += h(a)
    b += 3
    # raise Exception("lol")


def f(a, b):
    # wthell.wth()
    a = a + 2
    ob.s = str(b)
    g(a + 1, b * 2)
    # wthell.wth()
    h(36)


def t(a):
    f(a + 1, a + 2)
    a += 3
    f(a + 5, 2)


tracer = VizTracer()
counter = VizCounter(tracer, "a")
ob = VizObject(tracer, "b")
tracer.start()
t(3)
tracer.stop()
tracer.save("vdb_basic.json")
