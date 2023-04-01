from viztracer import VizTracer
tracer = VizTracer(tracer_entries=1000000)
tracer.start()

def call_self(n):
    if n == 0:
        return
    return call_self(n-1)
for _ in range(10):
    call_self(1000)

tracer.stop()
tracer.save()