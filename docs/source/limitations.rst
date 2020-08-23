Limitations
===========

VizTracer uses ``sys.setprofile()`` for its profiler capabilities, so it will conflict with other profiling tools which also use this function. Be aware of it when using VizTracer