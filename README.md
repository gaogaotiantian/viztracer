# VizTracer

[![build](https://github.com/gaogaotiantian/viztracer/workflows/build/badge.svg)](https://github.com/gaogaotiantian/viztracer/actions?query=workflow%3Abuild)  [![pypi](https://img.shields.io/pypi/v/viztracer.svg)](https://pypi.org/project/viztracer/)  [![support-version](https://img.shields.io/pypi/pyversions/viztracer)](https://img.shields.io/pypi/pyversions/viztracer)  [![license](https://img.shields.io/github/license/gaogaotiantian/viztracer)](https://github.com/gaogaotiantian/viztracer/blob/master/LICENSE)  [![commit](https://img.shields.io/github/last-commit/gaogaotiantian/viztracer)](https://github.com/gaogaotiantian/viztracer/commits/master)

VizTracer is a low-overhead deterministic debugging/profiling tool that can trace and visualize your python code to help you intuitively understand your code better and figure out the time consuming part of your code.

You can take a look at the [demo](http://www.minkoder.com/viztracer/result.html) result of multiple example programs(sort algorithms, mcts, modulo algorithms, multithread tracing, etc.)

[![example_img](https://github.com/gaogaotiantian/viztracer/blob/master/img/example.png)](https://github.com/gaogaotiantian/viztracer/blob/master/img/example.png)

[trace viewer](https://chromium.googlesource.com/catapult) is used to display the stand alone html data.

VizTracer also supports json output that complies with Chrome trace event format, which can be loaded using [perfetto](https://ui.perfetto.dev/)

VizTracer generates HTML report for flamegraph using [d3-flamegraph](https://github.com/spiermar/d3-flame-graph)

## Highlights

* Lower overhead than cProfile, more accurate on actual time consumed
* Detailed function entry/exit information on timeline, not just summary of time used
* Super easy to use, no source code change for basic usage, no package dependency
* Optional function filter to ignore functions you are not interested 
* Customize events to log and track data through time
* Stand alone HTML report with powerful front-end, or chrome-compatible json 
* Works on Linux/MacOS/Windows

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

You can also generate ```json``` file or ```gz``` file and load it with [chrome://tracing/](chrome://tracing/) or [perfetto](https://ui.perfetto.dev/). ```gz``` file is especially helpful when your trace file is large

```
python3 -m viztracer -o result.json my_script.py arg1 arg2
python3 -m viztracer -o result.json.gz my_script.py arg1 arg2
```

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

However, you can generate json file as well, which complies to the chrome trace event format. You can load the json file on [perfetto](https://ui.perfetto.dev/), which will replace the deprecated trace viewer in the future. Or you can use [chrome://tracing](chrome://tracing/) to load the file.

At the moment, perfetto does not support locally stand alone HTML file generation and it has some bugs, so I'm not able to switch completely to it. The good news is that once you load the perfetto page, you can use it even when you are offline. 

**When you are dealing with big traces, a stand alone HTML file might be very large and hard to load. You should try to dump a compressed ```filename.json.gz``` file and load it via [chrome://tracing/](chrome://tracing/) or [perfetto](https://ui.perfetto.dev/)**

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

Overhead is a big consideration when people choose profilers. VizTracer has a better overhead performance than native cProfiler. In the worst case(Pure FEE) VizTracer is about the same as cProfile and in more practical cases VizTracer performs much better. 

This is because VizTracer collects less information than cProfile, and optimized the hook function with a lot of efforts.

An example run for test_performance with Python 3.8 / Ubuntu 18.04.4 on Github VM

```
fib:
0.000678067(1.00)[origin] 
0.019880272(29.32)[py] 0.011103901(16.38)[parse] 0.021165599(31.21)[json] 
0.001344933(1.98)[c] 0.008181911(12.07)[parse] 0.015789866(23.29)[json] 
0.001472846(2.17)[cProfile]  

hanoi     (6148, 4100):
0.000550255(1.00)[origin] 
0.016343521(29.70)[py] 0.007299123(13.26)[parse] 0.016779364(30.49)[json] 
0.001062505(1.93)[c] 0.006416136(11.66)[parse] 0.011463236(20.83)[json] 
0.001144914(2.08)[cProfile] 

qsort     (8289, 5377):
0.002817679(1.00)[origin] 
0.052747431(18.72)[py] 0.011339725(4.02)[parse] 0.023644345(8.39)[json] 
0.004767673(1.69)[c] 0.008735166(3.10)[parse] 0.017173703(6.09)[json] 
0.007248019(2.57)[cProfile] 

slow_fib  (1135, 758):
0.028759652(1.00)[origin] 
0.033994071(1.18)[py] 0.001630461(0.06)[parse] 0.003386635(0.12)[json] 
0.029481623(1.03)[c] 0.001152415(0.04)[parse] 0.002191417(0.08)[json] 
0.028289305(0.98)[cProfile] 
```

## Documentation 

For full documentation, please see [https://viztracer.readthedocs.io/en/stable](https://viztracer.readthedocs.io/en/stable)

## Bugs/Requests

Please send bug reports and feature requests through [github issue tracker](https://github.com/gaogaotiantian/viztracer/issues). VizTracer is currently under development now and it's open to any constructive suggestions.

## License

Copyright Tian Gao, 2020.

Distributed under the terms of the  [Apache 2.0 license](https://github.com/gaogaotiantian/viztracer/blob/master/LICENSE).