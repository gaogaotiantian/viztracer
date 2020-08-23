# VizTracer

[![build](https://github.com/gaogaotiantian/viztracer/workflows/build/badge.svg)](https://github.com/gaogaotiantian/viztracer/actions?query=workflow%3Abuild)  [![pypi](https://img.shields.io/pypi/v/viztracer.svg)](https://pypi.org/project/viztracer/)  [![support-version](https://img.shields.io/pypi/pyversions/viztracer)](https://img.shields.io/pypi/pyversions/viztracer)  [![license](https://img.shields.io/github/license/gaogaotiantian/viztracer)](https://github.com/gaogaotiantian/viztracer/blob/master/LICENSE)  [![commit](https://img.shields.io/github/last-commit/gaogaotiantian/viztracer)](https://github.com/gaogaotiantian/viztracer/commits/master)

VizTracer is a deterministic debugging/profiling tool that can trace and visualize your python code to help you intuitively understand your code better and figure out the time consuming part of your code.

VizTracer can display every function executed and the corresponding entry/exit time from the beginning of the program to the end, which is helpful for programmers to catch sporatic performance issues. VizTracer is also capable of generating traditional flamegraph which is a good summary of the execution of the program

You can take a look at the [demo](http://www.minkoder.com/viztracer/result.html) result of multiple example programs(sort algorithms, mcts, modulo algorithms, multithread tracing, etc.)

[![example_img](https://github.com/gaogaotiantian/viztracer/blob/master/img/example.png)](https://github.com/gaogaotiantian/viztracer/blob/master/img/example.png)

[trace viewer](https://chromium.googlesource.com/catapult) is used to display the stand alone html data.

VizTracer also supports json output that complies with Chrome trace event format, which can be loaded using [perfetto](https://ui.perfetto.dev/)

VizTracer generates HTML report for flamegraph using [d3-flamegraph](https://github.com/spiermar/d3-flame-graph)

## Install

The prefered way to install VizTracer is via pip

```
pip install viztracer
```

You can also download the source code and build it yourself.

## Usage

There are a couple ways to use VizTracer

### Command Line

The easiest way to use VizTracer is through command line. Assume you have a python script to profile and the normal way to run it is:

```
python3 my_script.py arg1 arg2
```

You can simply use VizTracer as 

```
python3 -m viztracer my_script.py arg1 arg2
```

which will generate a ```result.html``` file in the directory you run this command. Open it in browser and there's your result.

By default, VizTracer only generates trace file, either in HTML format or json. You can have VizTracer to generate a flamegraph as well by 

```
python3 -m viztracer --save_flamegraph my_script.py
```

### Inline

Sometimes the command line may not work as you expected, or you do not want to profile the whole script. You can manually start/stop the profiling in your script as well.

```python
from viztracer import VizTracer

tracer = VizTracer()
tracer.start()
# Something happens here
tracer.stop()
tracer.save() # also takes output_file as an optional argument
```

Or, you can do it with ```with``` statement

```python
with VizTracer(output_file="optional.html") as tracer:
    # Something happens here
```

### Display Result

By default, VizTracer will generate a stand alone HTML file which you can simply open with Chrome(maybe Firefox?). The front-end uses trace-viewer to show all the data. 

However, you can generate json file as well, which complies to the chrome trace event format. You can load the json file on [perfetto](https://ui.perfetto.dev/), which will replace the deprecated trace viewer in the future. 

At the moment, perfetto does not support locally stand alone HTML file generation, so I'm not able to switch completely to it. The good news is that once you load the perfetto page, you can use it even when you are offline. 


### Trace Filter

Sometimes your code is really complicated or you need to run you program for a long time, which means the parsing time would be too long and the HTML/JSON file would be too large. There are ways in VizTracer to filter out the data you don't need. 

The filter works at tracing time, not parsing time. That means, using filters will introduce some extra overhead while your tracing, but will save significant memory, parsing time and disk space. 

VizTracer support:

* max stack depth
* include files
* exclude files
* ignore c function

### Add Custom Event

```VizTracer``` supports inserting custom events while the program is running. This works like a print debug, but you can know when this print happens while looking at trace data. 

VizTracer has:

* Instant Event
* Counter Event
* Object Event

### Multi Thread Support

```VizTracer``` supports python native ```threading``` module without the need to do any modification to your code. Just start ```VizTracer``` before you create threads and it will just work.

[![example_img](https://github.com/gaogaotiantian/viztracer/blob/master/img/multithread_example.png)](https://github.com/gaogaotiantian/viztracer/blob/master/img/example.png)


### Multi Process Support

VizTracer can support multi process with some extra steps. The current structure of VizTracer keeps one single buffer for one process, which means the user will have to produce multiple results from multiple processes and combine them together. 

### JSON alternative 

VizTracer needs to dump the internal data to json format. It is recommended for the users to install ```orjson```, which is much faster than the builtin ```json``` library. VizTracer will try to import ```orjson``` and fall back to the builtin ```json``` library if ```orjson``` does not exist.

## Performance

Overhead is a big consideration when people choose profilers. VizTracer now has a similar overhead as native cProfiler. It works slightly worse in the worst case(Pure FEE) and better in easier case because even though it collects some extra information than cProfiler, the structure is lighter. 

Admittedly, VizTracer is only focusing on FEE now, so cProfiler also gets other information that VizTracer does not acquire.

An example run for test_performance with Python 3.8 / Ubuntu 18.04.4 on Github VM

```
fib       (10336, 10336): 0.000852800 vs 0.013735200(16.11)[py] vs 0.001585900(1.86)[c] vs 0.001628400(1.91)[cProfile]
hanoi     (8192, 8192): 0.000621400 vs 0.012924899(20.80)[py] vs 0.001801800(2.90)[c] vs 0.001292900(2.08)[cProfile]
qsort     (10586, 10676): 0.003457500 vs 0.042572898(12.31)[py] vs 0.005594100(1.62)[c] vs 0.007573200(2.19)[cProfile]
slow_fib  (1508, 1508): 0.033606299 vs 0.038840998(1.16)[py] vs 0.033270399(0.99)[c] vs 0.032577599(0.97)[cProfile]
```

## Documentation 

For full documentation, please see [https://viztracer.readthedocs.io/en/latest](https://viztracer.readthedocs.io/en/latest)

## Bugs/Requests

Please send bug reports and feature requests through [github issue tracker](https://github.com/gaogaotiantian/viztracer/issues). VizTracer is currently under development now and it's open to any constructive suggestions.

## License

Copyright Tian Gao, 2020.

Distributed under the terms of the  [Apache 2.0 license](https://github.com/gaogaotiantian/viztracer/blob/master/LICENSE).