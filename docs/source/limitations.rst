Limitations
===========

VizTracer uses ``sys.setprofile()`` for its profiler capabilities, so it will conflict with other profiling tools which also use this function. Be aware of it when using VizTracer

The clock resolution and latency on WSL1 are very `bad <https://github.com/microsoft/WSL/issues/77>`_, so if you are using WSL1, you may experience extra overhead. There's no solution for it, except for upgrading to WSL2.

VizTracer, like other python tools that need to execute arbitrary code inside the module, may conflict with code that check for top module or have other structural requirements. For example, ``unittest.main()`` won't work if you use VizTracer from command line. 
There are ways to avoid it. You can use inline VizTracer, which will always work. Or you can specify modules to ``unittest.main()``, which is not a general solution but could work without too much code changes.