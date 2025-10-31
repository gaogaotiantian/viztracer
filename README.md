# VizTracer

[![build](https://github.com/gaogaotiantian/viztracer/workflows/build/badge.svg)](https://github.com/gaogaotiantian/viztracer/actions?query=workflow%3Abuild)  [![flake8](https://github.com/gaogaotiantian/viztracer/workflows/lint/badge.svg)](https://github.com/gaogaotiantian/viztracer/actions?query=workflow%3ALint)  [![readthedocs](https://img.shields.io/readthedocs/viztracer)](https://viztracer.readthedocs.io/en/stable/)  [![coverage](https://img.shields.io/codecov/c/github/gaogaotiantian/viztracer)](https://codecov.io/gh/gaogaotiantian/viztracer)  [![pypi](https://img.shields.io/pypi/v/viztracer.svg)](https://pypi.org/project/viztracer/)  [![Visual Studio Marketplace Version](https://img.shields.io/visual-studio-marketplace/v/gaogaotiantian.viztracer-vscode?logo=visual-studio)](https://marketplace.visualstudio.com/items?itemName=gaogaotiantian.viztracer-vscode)  [![support-version](https://img.shields.io/pypi/pyversions/viztracer)](https://img.shields.io/pypi/pyversions/viztracer)  [![license](https://img.shields.io/github/license/gaogaotiantian/viztracer)](https://github.com/gaogaotiantian/viztracer/blob/master/LICENSE)  [![commit](https://img.shields.io/github/last-commit/gaogaotiantian/viztracer)](https://github.com/gaogaotiantian/viztracer/commits/master)  [![sponsor](https://img.shields.io/badge/%E2%9D%A4-Sponsor%20me-%23c96198?style=flat&logo=GitHub)](https://github.com/sponsors/gaogaotiantian)

VizTracer is a low-overhead logging/debugging/profiling tool that can trace and visualize your python code execution.

The front-end UI is powered by [Perfetto](https://perfetto.dev/). **Use "AWSD" to zoom/navigate**.
More help can be found in "Support - Controls".

[![example_img](https://github.com/gaogaotiantian/viztracer/blob/master/img/example.png)](https://github.com/gaogaotiantian/viztracer/blob/master/img/example.png)


## Highlights

* Detailed function entry/exit information on timeline with source code
* Super easy to use, no source code change for most features, no package dependency
* Low overhead, probably the fastest tracer in the market
* Supports threading, multiprocessing, subprocess, async and PyTorch
* Powerful front-end, able to render GB-level trace smoothly
* Works on Linux/MacOS/Windows

## Install

The preferred way to install VizTracer is via pip

```sh
pip install viztracer
```

## Basic Usage

### Command Line

```sh
# Instead of "python3 my_script.py arg1 arg2"
viztracer my_script.py arg1 arg2
```

<details>

<summary>
A <code>result.json</code> file will be generated, which you can open with <code>vizviewer</code>
</summary>

```sh
# You can display all the files in a directory and open them in browser too
vizviewer ./
# For very large trace files, try external trace processor
vizviewer --use_external_processor result.json
```

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
```

A [VS Code Extension](https://marketplace.visualstudio.com/items?itemName=gaogaotiantian.viztracer-vscode)
is available to make your life even easier.

<p align="center">
    <img src="https://github.com/gaogaotiantian/viztracer-vscode/raw/master/assets/demo.gif" />
</p>

<details>

<summary>
Add <code>--open</code> to open the reports right after tracing
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

### PyTorch

VizTracer can log native calls and GPU events of PyTorch (based on `torch.profiler`) with
``--log_torch``.

```python
with VizTracer(log_torch=True) as tracer:
    # Your torch code
```

```sh
viztracer --log_torch your_model.py
```

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

For Python3.12+, VizTracer supports Python-level multi-thread tracing without the need to do any modification to your code.

For versions before 3.12, VizTracer supports python native ```threading``` module. Just start ```VizTracer``` before you create threads and it will just work.

For other multi-thread scenarios, you can use ``enable_thread_tracing()`` to notice VizTracer about the thread to trace it.

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

Perfetto supports native flamegraph, just select slices on the UI and choose "Slice Flamegraph".

[![example_img](https://github.com/gaogaotiantian/viztracer/blob/master/img/flamegraph.png)](https://github.com/gaogaotiantian/viztracer/blob/master/img/flamegraph.png)

### Remote attach

VizTracer supports remote attach to an arbitrary Python process to trace it, as long as viztracer is importable

Refer to [remote attach docs](https://viztracer.readthedocs.io/en/stable/remote_attach.html)

### JSON alternative

VizTracer needs to dump the internal data to json format. It is recommended for the users to install ```orjson```, which is much faster than the builtin ```json``` library. VizTracer will try to import ```orjson``` and fall back to the builtin ```json``` library if ```orjson``` does not exist.

## Performance

VizTracer puts in a lot of effort to achieve low overhead. The actual performance impact largely depends on your application.
For typical codebases, the overhead is expected to be below 1x. If your code has infrequent function calls,
the overhead could be minimal.

<details>

<summary>
Detailed explanation
</summary>

The overhead introduced by VizTracer is basically a fixed amount of time during function entry and exit, so the more time spent on
function entries and exits, the more overhead will be observed. A pure recursive ```fib``` function could suffer 3x-4x overhead
on Python3.11+ (when the Python call is optimized, before that Python call was slower so the overhead ratio would be less).

In the real life scenario, your code should not spend too much time on function calls (they don't really do anything useful), so
the overhead would be much smaller.

Many techniques are applied to minimize the overall overhead during code execution to reduce the inevitable skew introduced by
VizTracer (the report saving part is not as critical). For example, VizTracer tries to use the CPU timestamp counter instead of
a syscall to get the time when available. On Python 3.12+, VizTracer uses ```sys.monitoring``` which has less overhead than
```sys.setprofile```. All of the efforts made it observably faster than ```cProfile```, the Python stdlib profiler.

However, VizTracer is a tracer, which means it has to record every single function entry and exit, so it can't be as fast as
the sampling profilers - they are not the same thing. With the extra overhead, VizTracer provides a lot more information than
normal sampling profilers.

</details>

## Sponsors

We thank our sponsors to support VizTracer. If you want your logo here,
check our [sponsor page](https://github.com/sponsors/gaogaotiantian) or contact
the [author](https://github.com/gaogaotiantian) directly.

<a href="https://www.lambdatest.com/?utm_source=viztracer&utm_medium=sponsor" target="_blank">
    <img src="https://www.lambdatest.com/blue-logo.png" style="vertical-align: middle;" width="250" height="45" />
</a>

## Documentation

For full documentation, please see [https://viztracer.readthedocs.io/en/stable](https://viztracer.readthedocs.io/en/stable)

## Bugs/Requests

Please send bug reports and feature requests through [github issue tracker](https://github.com/gaogaotiantian/viztracer/issues). VizTracer is currently under development now and it's open to any constructive suggestions.

## License

Copyright 2020-2025 Tian Gao.

Distributed under the terms of the  [Apache 2.0 license](https://github.com/gaogaotiantian/viztracer/blob/master/LICENSE).
