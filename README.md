<h1 align="center">
VizTracer
</h1>

[![build](https://github.com/gaogaotiantian/viztracer/workflows/build/badge.svg)](https://github.com/gaogaotiantian/viztracer/actions?query=workflow%3Abuild)  [![flake8](https://github.com/gaogaotiantian/viztracer/workflows/lint/badge.svg)](https://github.com/gaogaotiantian/viztracer/actions?query=workflow%3ALint)  [![readthedocs](https://img.shields.io/readthedocs/viztracer)](https://viztracer.readthedocs.io/en/stable/)  [![coverage](https://img.shields.io/codecov/c/github/gaogaotiantian/viztracer)](https://codecov.io/gh/gaogaotiantian/viztracer)  [![pypi](https://img.shields.io/pypi/v/viztracer.svg)](https://pypi.org/project/viztracer/)  [![support-version](https://img.shields.io/pypi/pyversions/viztracer)](https://img.shields.io/pypi/pyversions/viztracer)  [![license](https://img.shields.io/github/license/gaogaotiantian/viztracer)](https://github.com/gaogaotiantian/viztracer/blob/master/LICENSE)  [![commit](https://img.shields.io/github/last-commit/gaogaotiantian/viztracer)](https://github.com/gaogaotiantian/viztracer/commits/master)  [![twitter](https://img.shields.io/twitter/follow/viztracer?label=viztracer&style=flat&logo=twitter)](https://twitter.com/viztracer)

<p align="center">  
  🌐 <a href="#english-introduction">English Introduction</a> | <a href="#中文简介">中文简介</a><br>
</p>

# English Introduction

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

```
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
viztracer --open my_scripy.py arg1 arg2
viztracer -o result.html --open my_script.py arg1 arg2
```

</details>

<details>

<summary>
modules and console scripts(like <code>flask</code>) are supported as well
</summary>

```
viztracer -m your_module
```

```
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

## Virtual Debug

You can virtually debug your program with you saved json report. The interface is very similar to ```pdb```. Even better, you can **go back in time**
because VizTracer has all the info recorded for you.

```sh
vdb <your_json_report>
```

Refer to the [docs](https://viztracer.readthedocs.io/en/stable/virtual_debug.html) for detailed commands

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

Copyright Tian Gao, 2020.

Distributed under the terms of the  [Apache 2.0 license](https://github.com/gaogaotiantian/viztracer/blob/master/LICENSE).

# 中文简介

VizTracer 是一种低开销的日志记录/调试/分析工具，可以跟踪和可视化您的 python 代码.

前端UI基于[Perfetto](https://perfetto.dev/), **使用"WASD"来缩放和导航**
更多帮助可以在 "Support - Controls" 中找到.

[![example_img](https://github.com/gaogaotiantian/viztracer/blob/master/img/example.png)](https://github.com/gaogaotiantian/viztracer/blob/master/img/example.png)


## 亮点

* 时间轴上详细的调用/返回信息以及源代码
* 超级好用，大部分功能无需更改源代码，无包依赖
* 支持线程、多处理、子进程和异步
* 使用 RegEx 记录任意函数/变量，无需更改代码
* 强大的前端，能够流畅渲染GB级trace
* 跨平台 (WLinux/MacOS/Windows)

## 安装

最好的安装 VizTracer 的方式是通过 pip

```sh
pip install viztracer
```

## 基础使用

### 命令行

假设您有一个要运行的 python 脚本：

```sh
python3 my_script.py arg1 arg2
```

那么便可以以如下的代码进行分析

```
viztracer my_script.py arg1 arg2
```

<details>

<summary>
将会生成一个 <code>result.json</code> 文件, 可以通过 <code>vizviewer</code> 打开
</summary>

vizviewer 将在 ``http://localhost:9001`` 开启网络服务, 你也可以直接在浏览器中使用 vizviewer

如果不想 vizviewer 自动打开浏览器, 可以:

```sh
vizviewer --server_only result.json
```

如果您只需要打开一次跟踪报告，并且不想要保持服务开启，请使用

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

<details>

<summary>
你也可以生成独立的 <code>html</code> 文件
</summary>

```sh
viztracer -o result.html my_script.py arg1 arg2
```

此功能基于 [catapult](https://github.com/catapult-project/catapult) 这是 Google 制作的旧工具, 正在逐渐被 [Perfetto](https://perfetto.dev/) 淘汰.

Catapult 跟踪查看器在跟踪较大的情况下运行缓慢，并且没有得到积极维护。 建议改用 Perfetto。

但是，如果您真的需要一个独立的 HTML 文件，这是唯一的选择。 Perfetto 不支持独立文件。

您也可以使用vizviewer打开html文件，只是为了使界面保持一致

```sh
vizviewer result.html
```

</details>

<details>

<summary>
或者添加 <code>--open</code> 在追踪后立马打开报告
</summary>

```sh
viztracer --open my_scripy.py arg1 arg2
viztracer -o result.html --open my_script.py arg1 arg2
```

</details>

<details>

<summary>
模块和控制台脚本(如 <code>flask</code>)也得到了极好的支持
</summary>

```
viztracer -m your_module
```

```
viztracer flask run
```

</details>

### Inline

您也可以在脚本中手动启动/停止 VizTracer。

```python
from viztracer import VizTracer

tracer = VizTracer()
tracer.start()
# Something happens here
tracer.stop()
tracer.save() # also takes output_file as an optional argument
```

或者，您可以使用 ```with``` 语句来实现

```python
with VizTracer(output_file="optional.json") as tracer:
    # Something happens here
```

### Jupyter

如果您使用的是 Jupyter，则可以使用 viztracer 的单元魔法。

```python
# You need to load the extension first
%load_ext viztracer
```

```python
%%viztracer
# Your code after
```

单元格后面会出现一个 ``VizTracer Report`` 按钮，你可以点击它来查看结果

## 进阶使用

### 追踪过滤器

VizTracer 可以过滤掉您不想减少开销的数据，并在您转储日志之前保留较长时间的信息。

* [最短持续时间](https://viztracer.readthedocs.io/en/stable/filter.html#min-duration)
* [最大栈深度](https://viztracer.readthedocs.io/en/stable/filter.html#max-stack-depth)
* [包含的文件](https://viztracer.readthedocs.io/en/stable/filter.html#include-files)
* [排除的文件](https://viztracer.readthedocs.io/en/stable/filter.html#exclude-files)
* [忽略 C 函数](https://viztracer.readthedocs.io/en/stable/filter.html#ignore-c-function)
* [稀疏的日志](https://viztracer.readthedocs.io/en/stable/filter.html#log-sparse)

### 无需更改代码的额外日志

VizTracer 可以在不更改源代码的情况下记录额外信息

* [任何带有正则表达式的变量/属性](https://viztracer.readthedocs.io/en/stable/extra_log.html#log-variable)
* [函数入口](https://viztracer.readthedocs.io/en/stable/extra_log.html#log-function-entry)
* [指定函数中的变量](https://viztracer.readthedocs.io/en/stable/extra_log.html#log-function-execution)
* [垃圾回收选项](https://viztracer.readthedocs.io/en/stable/extra_log.html#log-garbage-collector)
* [函数参数](https://viztracer.readthedocs.io/en/stable/extra_log.html#log-function-arguments)
* [函数返回值](https://viztracer.readthedocs.io/en/stable/extra_log.html#log-function-return-value)
* [审计事件](https://viztracer.readthedocs.io/en/stable/extra_log.html#log-audit)
* [引发的异常](https://viztracer.readthedocs.io/en/stable/extra_log.html#log-exception)

### 添加自定义事件

VizTracer 支持在程序运行时插入自定义事件。 这就像打印调试一样工作，但是您可以在查看跟踪数据时知道此打印何时发生。

* [即时事件](https://viztracer.readthedocs.io/en/stable/custom_event_intro.html#instant-event)
* [可变事件](https://viztracer.readthedocs.io/en/stable/custom_event_intro.html#variable-event)
* [持续时间事件](https://viztracer.readthedocs.io/en/stable/custom_event_intro.html#duration-event)

## 杂项

### 多线程支持

VizTracer 支持 python 原生 ```threading``` 模块，无需对您的代码进行任何修改。 只需在创建线程之前启动 ```VizTracer``` 就可以了。

对于其他多线程场景，您可以使用 ``enable_thread_tracing()`` 让 VizTracer 知道要跟踪它的线程。

[![example_img](https://github.com/gaogaotiantian/viztracer/blob/master/img/multithread_example.png)](https://github.com/gaogaotiantian/viztracer/blob/master/img/multithread_example.png)

参考 [multi thread docs](https://viztracer.readthedocs.io/en/stable/concurrency.html)


### 多进程支持

VizTracer 支持 ```subprocess```, ```multiprocessing```, ```os.fork()```, ```concurrent.futures```, 和 ```loky``` 盒子。

对于更一般的多进程情况，VizTracer 可以支持一些额外的步骤。

[![example_img](https://github.com/gaogaotiantian/viztracer/blob/master/img/multiprocess_example.png)](https://github.com/gaogaotiantian/viztracer/blob/master/img/multiprocess_example.png)

参考 [multi process docs](https://viztracer.readthedocs.io/en/stable/concurrency.html)

### 异步支持

VizTracer 原生支持 ```asyncio```，但可以通过使用 ```--log_async``` 来增强报告。

[![example_img](https://github.com/gaogaotiantian/viztracer/blob/master/img/async_example.png)](https://github.com/gaogaotiantian/viztracer/blob/master/img/async_example.png)

参考 [async docs](https://viztracer.readthedocs.io/en/stable/concurrency.html)

### 火焰图

VizTracer 可以显示跟踪数据的火焰图。

```sh
vizviewer --flamegraph result.json
```

[![example_img](https://github.com/gaogaotiantian/viztracer/blob/master/img/flamegraph.png)](https://github.com/gaogaotiantian/viztracer/blob/master/img/flamegraph.png)

### 远程连接

VizTracer 支持远程附加到任意 Python 进程以跟踪它，只要 viztracer 是可导入的

参考 [remote attach docs](https://viztracer.readthedocs.io/en/stable/remote_attach.html)

### JSON替代品

VizTracer 需要将内部数据转储为 json 格式。 建议用户安装 ```orjson```，比内置的 ```json``` 库要快得多。 VizTracer 将尝试导入 ```orjson``` 并在 ```orjson``` 不存在时回退到内置的 ```json``` 库。

## 虚拟调试

您可以使用保存的 json 报告虚拟调试程序。 该接口与```pdb``` 非常相似。 更好的是，你可以**回到过去**
因为 VizTracer 为您记录了所有信息。

```sh
vdb <your_json_report>
```

具体命令参考 [docs](https://viztracer.readthedocs.io/en/stable/virtual_debug.html)

## 性能

在最坏的情况下，VizTracer 将引入 2 到 3 倍的开销。 如果函数调用较少或过滤器应用正确，开销会好得多。

<details>

<summary>
在 Github VM 上使用 Python 3.8 / Ubuntu 18.04.4 运行 test_performance 的示例
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

## 文档

完整文档参见 [https://viztracer.readthedocs.io/en/stable](https://viztracer.readthedocs.io/en/stable)

## Bugs/Requests

报告 bug 或者申请 feature 通过 [github issue tracker](https://github.com/gaogaotiantian/viztracer/issues). VizTracer 目前正在开发中，欢迎提出任何建设性的建议。

## 许可证

版权所有 Tian Gao, 2020.

根据 [Apache 2.0 license](https://github.com/gaogaotiantian/viztracer/blob/master/LICENSE). 分发
