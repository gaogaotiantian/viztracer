Limitations
===========

VizTracer uses ``sys.setprofile()`` for its profiler capabilities, so it will conflict with other profiling tools which also use this function. Be aware of it when using VizTracer

The clock resolution and latency on WSL1 is very [bad](https://github.com/microsoft/WSL/issues/77), so if you are using WSL1, you may experience extra overhead. There's no solution for it, except for upgrading to WSL2.