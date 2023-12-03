# VizTracer

[![build](https://github.com/gaogaotiantian/viztracer/workflows/build/badge.svg)](https://github.com/gaogaotiantian/viztracer/actions?query=workflow%3Abuild)  [![flake8](https://github.com/gaogaotiantian/viztracer/workflows/lint/badge.svg)](https://github.com/gaogaotiantian/viztracer/actions?query=workflow%3ALint)  [![readthedocs](https://img.shields.io/readthedocs/viztracer)](https://viztracer.readthedocs.io/en/stable/)  [![coverage](https://img.shields.io/codecov/c/github/gaogaotiantian/viztracer)](https://codecov.io/gh/gaogaotiantian/viztracer)  [![pypi](https://img.shields.io/pypi/v/viztracer.svg)](https://pypi.org/project/viztracer/)  [![support-version](https://img.shields.io/pypi/pyversions/viztracer)](https://img.shields.io/pypi/pyversions/viztracer)  [![license](https://img.shields.io/github/license/gaogaotiantian/viztracer)](https://github.com/gaogaotiantian/viztracer/blob/master/LICENSE)  [![commit](https://img.shields.io/github/last-commit/gaogaotiantian/viztracer)](https://github.com/gaogaotiantian/viztracer/commits/master)  [![sponsor](https://img.shields.io/badge/%E2%9D%A4-Sponsor%20me-%23c96198?style=flat&logo=GitHub)](https://github.com/sponsors/gaogaotiantian)

VizTracer is a low-overhead logging/debugging/profiling tool that can trace and visualize your python code execution.

The front-end UI is powered by [Perfetto](https://perfetto.dev/). **Use "AWSD" to zoom/navigate**.
More help can be found in "Support - Controls".

[![example_img](https://github.com/gaogaotiantian/viztracer/blob/master/img/example.png)](https://github.com/gaogaotiantian/viztracer/blob/master/img/example.png)


## Highlights

* Detailed function entry/exit information on timeline with source code
* Super easy to use, no source code change for most features, no package dependency
* Supports threading, multiprocessing, subprocess and async
* Logs arbitrary function/variable using RegEx without code change
* Powerful front-end, able to render GB-level trace smoothly
* Works on Linux/MacOS/Windows

## Install

The preferred way to install VizTracer is via pip

```sh
pip install viztracer
```

## Basic Usage

### Command Line

Assume you have a python script to run:

```sh
python3 my_script.py arg1 arg2
```

You can simply use VizTracer by

```sh
viztracer my_script.py arg1 arg2
```

<details>

<summary>
A <code>result.json</code> file will be generated, which you can open with <code>vizviewer</code>
</summary>

vizviewer will host an HTTP server on ``http://localhost:9001``. You can also open your browser and use that address.

If you do not want vizviewer to open the webbrowser automatically, you can use

```sh
vizviewer --server_only result.json
```

If you just need to bring up the trace report once, and do not want the persistent server, use

```sh
vizviewer --once result.json
```

</details>

```sh
vizviewer result.json
# You can display all the files in a directory and open them in browser too
vizviewer ./
# For very large trace files, try external trace processor
vizviewer --use_external_processor result.json
```

A [VS Code Extension](https://marketplace.visualstudio.com/items?itemName=gaogaotiantian.viztracer-vscode)
is available to make your life even easier. You can open the corresponding source file in
VS Code from the trace report with the extension.

<details>

<summary>
You can also generate standalone <code>html</code> file
</summary>

```sh
viztracer -o result.html my_script.py arg1 arg2
```

The standalone HTML file is powered by [catapult](https://github.com/catapult-project/catapult) trace viewer which is an old tool Google made and is being replaced by [Perfetto](https://perfetto.dev/) gradually.

Catapult trace viewer is sluggish with larger traces and is not actively maintained. It is recommended to use Perfetto instead.

However, if you really need a standalone HTML file, this is the only option. Perfetto does not support standalone files.

You can use vizviewer to open the html file as well, just to make the interface consistent

```sh
vizviewer result.html
```

</details>

<details>

<summary>
Or add <code>--open</code> to open the reports right after tracing
</summary>

```sh
viztracer --open my_script.py arg1 arg2
viztracer -o result.html --open my_script.py arg1 arg2
```

</details>

<details>

<summary>
modules and console scripts(like <code>flask</code>) are supported as well
</summary>

```sh
viztracer -m your_module
```

```sh
viztracer flask run
```

</details>

### Inline

You can also manually start/stop VizTracer in your script as well.

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
with VizTracer(output_file="optional.json") as tracer:
    # Something happens here
```

### Jupyter

If you are using Jupyter, you can use viztracer cell magics.

```python
# You need to load the extension first
%load_ext viztracer
```

```python
%%viztracer
# Your code after
```

A ``VizTracer Report`` button will appear after the cell and you can click it to view the results

## Advanced Usage

### Trace Filter

VizTracer can filter out the data you don't want to reduce overhead and keep info of a longer time period before you dump the log.

* [Min Duration](https://viztracer.readthedocs.io/en/stable/filter.html#min-duration)
* [Max Stack Depth](https://viztracer.readthedocs.io/en/stable/filter.html#max-stack-depth)
* [Include Files](https://viztracer.readthedocs.io/en/stable/filter.html#include-files)
* [Exclude Files](https://viztracer.readthedocs.io/en/stable/filter.html#exclude-files)
* [Ignore C Function](https://viztracer.readthedocs.io/en/stable/filter.html#ignore-c-function)
* [Sparse Log](https://viztracer.readthedocs.io/en/stable/filter.html#log-sparse)

### Extra Logs without Code Change

VizTracer can log extra information without changing your source code

* [Any Variable/Attribute with RegEx](https://viztracer.readthedocs.io/en/stable/extra_log.html#log-variable)
* [Function Entry](https://viztracer.readthedocs.io/en/stable/extra_log.html#log-function-entry)
* [Variables in Specified Function](https://viztracer.readthedocs.io/en/stable/extra_log.html#log-function-execution)
* [Garbage Collector Operation](https://viztracer.readthedocs.io/en/stable/extra_log.html#log-garbage-collector)
* [Function Input Arguments](https://viztracer.readthedocs.io/en/stable/extra_log.html#log-function-arguments)
* [Function Return Value](https://viztracer.readthedocs.io/en/stable/extra_log.html#log-function-return-value)
* [Audit Events](https://viztracer.readthedocs.io/en/stable/extra_log.html#log-audit)
* [Raised Exceptions](https://viztracer.readthedocs.io/en/stable/extra_log.html#log-exception)

### Add Custom Event

VizTracer supports inserting custom events while the program is running. This works like a print debug, but you can know when this print happens while looking at trace data.

* [Instant Event](https://viztracer.readthedocs.io/en/stable/custom_event_intro.html#instant-event)
* [Variable Event](https://viztracer.readthedocs.io/en/stable/custom_event_intro.html#variable-event)
* [Duration Event](https://viztracer.readthedocs.io/en/stable/custom_event_intro.html#duration-event)

## Misc

### Multi Thread Support

VizTracer supports python native ```threading``` module without the need to do any modification to your code. Just start ```VizTracer``` before you create threads and it will just work.

For other multi-thread scenarios, you can use ``enable_thread_tracing()`` to let VizTracer know about the thread to trace it.

[![example_img](https://github.com/gaogaotiantian/viztracer/blob/master/img/multithread_example.png)](https://github.com/gaogaotiantian/viztracer/blob/master/img/multithread_example.png)

Refer to [multi thread docs](https://viztracer.readthedocs.io/en/stable/concurrency.html) for details


### Multi Process Support

VizTracer supports ```subprocess```, ```multiprocessing```, ```os.fork()```, ```concurrent.futures```, and ```loky``` out of the box.

For more general multi-process cases, VizTracer can support with some extra steps.

[![example_img](https://github.com/gaogaotiantian/viztracer/blob/master/img/multiprocess_example.png)](https://github.com/gaogaotiantian/viztracer/blob/master/img/multiprocess_example.png)

Refer to [multi process docs](https://viztracer.readthedocs.io/en/stable/concurrency.html) for details

### Async Support

VizTracer supports ```asyncio``` natively, but could enhance the report by using ```--log_async```.

[![example_img](https://github.com/gaogaotiantian/viztracer/blob/master/img/async_example.png)](https://github.com/gaogaotiantian/viztracer/blob/master/img/async_example.png)

Refer to [async docs](https://viztracer.readthedocs.io/en/stable/concurrency.html) for details

### Flamegraph

VizTracer can show flamegraph of traced data.

```sh
vizviewer --flamegraph result.json
```

[![example_img](https://github.com/gaogaotiantian/viztracer/blob/master/img/flamegraph.png)](https://github.com/gaogaotiantian/viztracer/blob/master/img/flamegraph.png)

### Remote attach

VizTracer supports remote attach to an arbitrary Python process to trace it, as long as viztracer is importable

Refer to [remote attach docs](https://viztracer.readthedocs.io/en/stable/remote_attach.html)

### JSON alternative

VizTracer needs to dump the internal data to json format. It is recommended for the users to install ```orjson```, which is much faster than the builtin ```json``` library. VizTracer will try to import ```orjson``` and fall back to the builtin ```json``` library if ```orjson``` does not exist.

## Performance

VizTracer will introduce 2x to 3x overhead in the worst case. The overhead is much better if there are less function calls or if filters are applied correctly.

<details>

<summary>
An example run for test_performance with Python 3.8 / Ubuntu 18.04.4 on Github VM
</summary>

```sh
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
</details>

## Documentation

For full documentation, please see [https://viztracer.readthedocs.io/en/stable](https://viztracer.readthedocs.io/en/stable)

## Bugs/Requests

Please send bug reports and feature requests through [github issue tracker](https://github.com/gaogaotiantian/viztracer/issues). VizTracer is currently under development now and it's open to any constructive suggestions.

## License

Copyright 2020-2023 Tian Gao.

Distributed under the terms of the  [Apache 2.0 license](https://github.com/gaogaotiantian/viztracer/blob/master/LICENSE).
