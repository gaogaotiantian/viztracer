Advanced Usage
==============

Both command line usage and inline usage have optional arguments to make VizTracer better suit your requirements. 

Filter
------

Sometimes, you will have too many data entries and you want to filter them out to make your overhead and output file smaller. This is very useful when you are tracing a long program with a lot of function entries/exits.

You can limit maximum stack depth to trace by

.. code-block::

    viztracer --max_stack_depth 10 my_script.py

OR

.. code-block:: python

    tracer = VizTracer(max_stack_depth=10)

You can include only certain files/folders to trace by

.. code-block::

    viztracer --include_files ./src -- my_script.py

OR

.. code-block:: python

    tracer = VizTracer(include_files=["./src"])

Similarly, you can exclude certain files/folders to trace by

.. code-block::

    viztracer --exclude_files ./not_interested.py -- my_script.py

OR

.. code-block:: python

    tracer = VizTracer(exclude_files=["./not_interested.py"])

By default, VizTracer will trace both python and C functions. You can turn off tracing C functions by

.. code-block:: 

    viztracer --ignore_c_function my_script.py

OR

.. code-block:: python
    
    tracer = VizTracer(ignore_c_function=True)

You can ask VizTracer not to trace any functions that are not in a valid file(mostly import stuff) using ``ignore_non_file``

.. code-block:: 

    viztracer --ignore_non_file my_script.py

OR

.. code-block:: python
    
    tracer = VizTracer(ignore_non_file=True)

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

Log Function Arguments 
----------------------

VizTracer can log every function's arguments as ``string``, aka their ``__repr__``. The arguments will be stored in each python function entry 
under ``args["func_args"]``. You can overwrite the object's ``__repr__`` function to log the object as you need.

You can enable this feature in command line or using inline. 

.. code-block:: 
    
    viztracer --log_function_args my_script.py

.. code-block:: python
    
    tracer = VizTracer(log_function_args=True)

**This feature will introduce a very large overhead(depends on your argument list), so be aware of it**

You can log additional arbitrary (key, value) pairs for your function entry using ``add_functionarg()``. Refer to :doc:`viztracer` for it's usage

Log Print
---------

A very common usage of custom events is to intercept ``print()`` function and record the stuff it prints to the final report. This is like doing print debug on timeline.

You can do this simply by:

.. code-block:: 

    viztracer --log_print my_script.py

OR

.. code-block:: python

    tracer = VizTracer(log_print=True)

Log Garbage Collector
---------------------

You can log the optionaml garbage collector module in Python. Notice that in CPython, most garbage collection is done using 
reference count. The garbage collector module is only responsible for the cycle reference. So this feature is mainly used
to detect cycle reference collection status, and the time consumed by running the optional garbage collector.

You can do this simply by:

.. code-block:: 

    viztracer --log_gc my_script.py

OR

.. code-block:: python

    tracer = VizTracer(log_gc=True)

Log Variable
------------

You can log any variable by its name and regex without making any changes to your source code.
This is like adding ``print`` after assigning the variable without actually writing the code.
The log will appear in the report as an instant event, and the variables ``repr`` will be showed

.. code-block:: 

    viztracer --log_var <var_name> -- my_script.py

``--`` is added to resolve the ambiguity. Every time a variable matches regex ``var_name`` is assigned a value, it will be logged.
If you don't know what regex is, simply using the full name of the variable as ``var_name`` will allow you to log the variable

Log Number
----------

Similar to `Log Variable`_, you can log any variable as a number, which will utilize trace viewer's counter event. 
The report will visualize the number through time as a separate signal like ``VizCounter`` did. 

.. code-block:: 

    viztracer --log_number <var_name> -- my_script.py

``--`` is added to resolve the ambiguity. Every time a variable matches regex ``var_name`` is assigned a value, it will be logged.
If you don't know what regex is, simply using the full name of the variable as ``var_name`` will allow you to log the variable

Using ``--log_number`` on non-numeric variables will raise an exception.

Log Attribute
-------------

You can log writes to attributes based on the name of the attribute. This is useful when you want to track an attribute of
an object, but there are just too many entries to it. It could be ``self.attr_name`, `obj.attr_name` or even 
``obj_list[0].attr_name``. With ``log_attr`` you can log the attributes that match the regex.

.. code-block:: 

    viztracer --log_attr <attr_name> -- my_script.py

``--`` is added to resolve the ambiguity. Every time an attribute matches regex ``attr_name`` is assigned a value, it will be logged.
If you don't know what regex is, simply using the full name of the attribute as ``attr_name`` will allow you to log the attribute

Log Function Execution
----------------------

You can log function execution details with VizTracer. VizTracer will record all the assignments in specified functions and display
them in the detailed information of the generated report.

.. code-block:: 

    viztracer --log_func_exec <func_name> -- my_script.py

``--`` is added to resolve the ambiguity. Every time an function matches regex ``func_name`` is called, its execution will be logged.
If you don't know what regex is, simply using the full name of the function as ``func_name`` will allow you to log the function 

Log Exception
-------------

You can log raised exception with VizTracer. All raised exceptions, whether caught or not, will be displayed as an instant event
in the report.

.. code-block:: 

    viztracer --log_exception my_script.py

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

Global ``VizTracer`` object
---------------------------

For many features, you need a tracer object, which you have to instantiate in your code and can not
use the convenient ``viztracer <args>`` commands. You can solve this by using the global ``VizTracer``
object ``viztracer <args>`` generates. 

When you youse ``viztracer <args>`` command to trace your program, a ``__viz_tracer__`` builtin
is passed to your program and it has the tracer object ``viztracer <args>`` used. 

It is recommended to import ``get_tracer`` and use it to get global tracer. The upside of using ``get_tracer()`` function 
is that your program won't crash when it's not started by ``viztracer`` because ``get_tracer()`` will return ``None``

When you use ``VizLoggingHandler`` or ``VizCounter`` or ``VizObject``, setting their tracer to ``None`` will make 
the logging a ``NOP``. This will enable you to leave the instrumentation code as it is and run you program both
regularly and with ``viztracer``

You can do things like:

.. code-block:: python

    from viztracer import VizLoggingHandler, get_tracer

    handler = VizLoggingHandler()

    handler.setTracer(get_tracer())

.. code-block:: python

    from viztracer import get_tracer, VizObject

    obj = VizObject(get_tracer(), "my variable")

Circular Buffer Size
--------------------

VizTracer used circular buffer to store the entries. When there are too many entries, it will only store the latest ones so you know what happened
recently. The default buffer size is 5,000,000(number of entries), which takes about 600MiB memory. You can specify this when you instantiate ``VizTracer`` object

Be aware that 600MiB is disk space, it requires more RAM to load it on Chrome.

.. code-block:: python

    viztracer --tracer_entries 1000000 my_script.py

OR

.. code-block:: python

    tracer = VizTracer(tracer_entries = 1000000)

Multi-Thread and Multi-Process
------------------------------

VizTracer supports both multi-thread and multi-process tracing. 

VizTracer supports python native ``threading`` module without the need to do any modification to your code. Just start ``VizTracer`` before you create threads and it will just work.

It's a little bit more complicated to do multi processing. You basically need to trace each process separately and generate ``json`` files for each process, then combine them with 

.. code-block:: 

    viztracer --combine <json_files>

For detailed usage, please refer to :doc:`multi_process`

Debug Your Saved Report
-----------------------

VizTracer allows you to debug your json report just like pdb. You can understand how your program is executed by 
interact with it. Even better, you can **go back in time** because you know what happened before. 

.. code-block:: 

    vdb <your_json_report>

For detailed commands, please refer to :doc:`virtual_debug`