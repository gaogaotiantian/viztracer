Concurrency
===========

VizTracer supports concurrency tracing, including asyncio, multi-thread and multi-process. 

asyncio
-------

VizTracer supports ``asyncio`` module natively. However, you can use ``--log_async`` to make the report clearer.

Under the rug, asyncio is a single-thread program that's scheduled by Python built-ins. With ``--log_async``, you can visualize
different tasks as "threads", which could separate the real work from the underlying structure, and give you a more intuitive
understanding of how different tasks consume the runtime.

.. code-block::

    viztracer --log_async my_script.py

threading
---------

VizTracer supports python native ``threading`` module without the need to do any modification to your code. 
Just start ``VizTracer`` before you create threads and it will just work.

other multi-thread
------------------

If you are using multi-thread via other mechanism, for example, PyQt thread, VizTracer can't support it out of the box.
However, you can notice VizTracer that you are in a separate thread and enable tracing in that thread with ``enable_thread_tracing``

.. code-block:: python

    from viztracer import get_tracer

    class YourThread:
        def run(self):
            # This will tell VizTracer to trace the thread
            get_tracer().enable_thread_tracing()

subprocess
----------

VizTracer supports ``subprocess``. You need to make sure the main process exits after subprocesses finish.

.. code-block::

    viztracer my_script_using_subprocess.py

This will generate an HTML file for all processes. There are a couple of things you need to be aware though. 

VizTracer patches subprocess module(to be more specific, ``subprocess.Popen``) to make this work like a magic. However, it will only patch
when the args passed to ``subprocess.Popen`` is a list(``subprocess.Popen(["python", "subscript.py"])``) and the first argument starts with
``python``. This covers most of the cases, but if you do have a situation that can't be solved, you can raise an issue and we can talk
about solutions.

multiprocessing and concurrent.futures
--------------------------------------

VizTracer supports ``multiprocessing`` and ``concurrent.futures``, and it will make the main process wait for all the other processes to finish
so the report can include all processes. You can skip the waiting using Ctrl+C.

.. code-block::

    viztracer my_script_using_multiprocess.py

This feature is available on all platforms and for both ``fork`` and ``spawn`` type ``Process``.

However, on Windows, ``multiprocessing.Pool`` won't work with VizTracer because there's no way to gracefully catch the exit of the process

os.fork()
---------

VizTracer supports ``os.fork``, with some caveats. 

On Python3.8+, it works well, the main process will wait for
forked processes to finish. You can even use ``os.exec()`` and its other forms after you fork the process. Of course
VizTracer only records what happens before ``os.exec()``, you need :ref:`generic multi process support <generic_multi_process>` to record
what happens after.

On Python3.6/3.7, VizTracer is not able to wait for the forked process to finish. It would be user's responsibility
to wait for the forked process to finish if they want to see both processes in the report.

loky
----

VizTracer supports ``loky>=3.0.0`` as ``loky`` implemented the ``viztracer`` initializer. You can log ``loky`` processes
just as easy as builtin ``multiprocessing``

.. _generic_multi_process:

generic multi process support
-----------------------------

VizTracer has a simple instrumentation for all the third party libraries to integrate VizTracer to their multi process code.

First, your main process has to be executed by ``viztracer``. Inline VizTracer won't work. In your program, you need
``get_tracer().init_kwargs``, which is a ``Dict`` that can be easily serializable with ``pickle`` or other libraries.

Then, pass this argument to your sub-process, and instantiate a VizTracer object with it

.. code-block:: python

    # init_kwargs is the argument from main process
    tracer = VizTracer(**init_kwargs)
    tracer.register_exit()
    tracer.start()

And you are good to go. The main process should collect the data from sub-processes automatically and put together a report.

combine reports
---------------

You can generate json reports from different processes and combine them manually as well. It is recommended to use
``--pid_suffix`` so the report will be saved as a json file ending with the pid of the process. You can specify your own file name using ``-o`` too.

.. code-block::
    
    viztracer --pid_suffix single_process.py
    # or
    viztracer -o process1.json single_process.py

You can specify the output directory if you want to

.. code-block::

    viztracer --pid_suffix --output_dir ./temp_dir single_process.py

After generating ``json`` files, you need to combine them

.. code-block::
    
    viztracer --combine ./temp_dir/*.json

This will generate the HTML report with all the process info. You can specify ``--output_file`` when using ``--combine``.
