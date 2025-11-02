Limitations
===========

VizTracer uses ``sys.setprofile()`` (before Python3.12) and ``sys.monitoring`` (after Python3.12) for its profiler capabilities,
so it will conflict with other profiling tools which also use these mechanisms. Be aware of it when using VizTracer

The clock resolution and latency on WSL1 are very `bad <https://github.com/microsoft/WSL/issues/77>`_, so if you are using WSL1, you may experience extra overhead.
There's no solution for it, except for upgrading to WSL2.

VizTracer, like other python tools that need to execute arbitrary code inside the module,
may conflict with code that check for top module or have other structural requirements.
For example, ``unittest.main()`` won't work if you use VizTracer from command line. 
There are ways to avoid it. You can use inline VizTracer, which will always work.
Or you can specify modules to ``unittest.main()``, which is not a general solution but could work without too much code changes.

If your code uses ``os._exit`` then VizTracer cannot save data before exiting. Consider using ``sys.exit`` instead.
See `this issue <https://github.com/gaogaotiantian/viztracer/issues/340>`_ for details.
