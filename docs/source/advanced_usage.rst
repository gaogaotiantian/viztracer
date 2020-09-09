Advanced Usage
==============

Both command line usage and inline usage have optional arguments to make VizTracer better suit your requirements. 

Filter
------

Sometimes, you will have too many data entries and you want to filter them out to make your overhead and output file smaller. This is very useful when you are tracing a long program with a lot of function entries/exits.

You can limit maximum stack depth to trace by

.. code-block::

    python3 -m viztracer --max_stack_depth 10 my_script.py

OR

.. code-block:: python

    tracer = VizTracer(max_stack_depth=10)

You can include only certain files/folders to trace by

.. code-block::

    python3 -m viztracer --include_files ./src --run my_script.py

OR

.. code-block:: python

    tracer = VizTracer(include_files=["./src"])

Similarly, you can exclude certain files/folders to trace by

.. code-block::

    python3 -m viztracer --exclude_files ./not_interested.py --run my_script.py

OR

.. code-block:: python

    tracer = VizTracer(include_files=["./not_interested.py"])

By default, VizTracer will trace both python and C functions. You can turn off tracing C functions by

.. code-block:: 

    python3 -m viztracer --ignore_c_function my_script.py

OR

.. code-block:: python
    
    tracer = VizTracer(ignore_c_function=True)

It's possible that you want to ignore some arbitrary functions and their descendants. You can do it using ``@ignore_function`` decorator

.. code-block:: python

    from viztracer import ignore_function
    @ignore_function
    def some_function():
        # nothing inside will be traced

For detailed usage of filters, please refer to :doc:`viztracer`

Custom Events
-------------

You may want to insert custom events to the report while you are tracing the program. This is helpful to debug your code and understand what is going on at a specific time point.

VizTracer supports three kinds of custom events:

* Instant Event
* Counter Event
* Object Event

You can refer to :doc:`custom_event` for how to use these.

Log Return Value
----------------

VizTracer can log every function's return value as ``string``, aka it's ``__repr__``. The reason it can't log it as an object is because
not all object in python are jsonifiable and it may cause problems. The return value will be stored in each python function entry 
under ``args["return_value"]``. You can overwrite the object's ``__repr__`` function to log the object as you need.

You can enable this feature in command line or using inline. 

.. code-block:: 
    
    viztracer --log_return_value my_script.py

.. code-block:: python
    
    tracer = VizTracer(log_return_value=True)

You can log arbitrary (key, value) pairs for your function entry using ``add_functionarg()``. Refer to :doc:`viztracer` for it's usage

Log Print
---------

A very common usage of custom events is to intercept ``print()`` function and record the stuff it prints to the final report. This is like doing print debug on timeline.

You can do this simply by:

.. code-block:: 

    python -m viztracer --log_print my_script.py

OR

.. code-block:: python

    tracer = VizTracer(log_print=True)

Work with ``logging`` module
----------------------------

VizTracer can work with python builtin ``logging`` module by adding a handler to it. The report will show logging
data as instant events.

.. code-block:: python

    from viztracer import VizLoggingHandler

    tracer = VizTracer()
    handler = VizLoggingHandler()
    handler.setTracer(tracer)
    # A handler is added to logging so logging will dump data to VizTracer
    logging.basicConfig(handlers = [handler])

Circular Buffer Size
--------------------

VizTracer used circular buffer to store the entries. When there are too many entries, it will only store the latest ones so you know what happened
recently. The default buffer size is 5,000,000(number of entries), which takes about 600MiB memory. You can specify this when you instantiate ``VizTracer`` object

Be aware that 600MiB is disk space, it requires more RAM to load it on Chrome.

.. code-block:: python

    python -m viztracer --tracer_entries 1000000 my_script.py

OR

.. code-block:: python

    tracer = VizTracer(tracer_entries = 1000000)

Multi-Thread and Multi-Process
------------------------------

VizTracer supports both multi-thread and multi-process tracing. 

VizTracer supports python native ``threading`` module without the need to do any modification to your code. Just start ``VizTracer`` before you create threads and it will just work.

It's a little bit more complicated to do multi processing. You basically need to trace each process separately and generate ``json`` files for each process, then combine them with 

.. code-block:: 

    python -m viztracer --combine <json_files>

For detailed usage, please refer to :doc:`multi_process`

Debug Your Saved Report
-----------------------

VizTracer allows you to debug your json report just like pdb. You can understand how your program is executed by 
interact with it. Even better, you can **go back in time** because you know what happened before. 

.. code-block:: 

    vdb <your_json_report>

For detailed commands, please refer to :doc:`virtual_debug`