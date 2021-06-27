Extra Log
=========

VizTracer features with many extra log possibilities **without even changing your source code**. 
You can start VizTracer from command line and use command line arguments to control what
you need to log.

Log Variable
------------

You can log any variable using regex matching to the variable name.
This is like adding ``print`` after assigning the variable without actually writing the code.
The log will appear in the report as an Instant Event, and the variables ``repr`` will be showed

.. code-block:: 

    viztracer --log_var <var_name> -- my_script.py

``--`` is added to resolve the ambiguity. Every time a variable matches regex ``<var_name>`` is assigned a value, it will be logged.
If you don't know what regex is, simply using the full name of the variable as ``<var_name>`` will allow you to log the variable

Log Number
----------

Similar to `Log Variable`_, you can log any variable as a number, which will be logged as Counter Event. 
The report will visualize the number through time as a separate signal like ``VizCounter`` did. 

.. code-block:: 

    viztracer --log_number <var_name> -- my_script.py

``--`` is added to resolve the ambiguity. Every time a variable matches regex ``<var_name>`` is assigned a value, it will be logged.
If you don't know what regex is, simply using the full name of the variable as ``<var_name>`` will allow you to log the variable

Using ``--log_number`` on non-numeric variables will raise an exception.

Log Attribute
-------------

You can log writes to attributes based on the name of the attribute. This is useful when you want to track an attribute of
an object, but there are just too many entries to it. It could be ``self.attr_name``, ``obj.attr_name`` or even 
``obj_list[0].attr_name``. With ``log_attr`` you can log the attributes matching the regex as an Instant Event.

.. code-block:: 

    viztracer --log_attr <attr_name> -- my_script.py

``--`` is added to resolve the ambiguity. Every time an attribute matches regex ``<attr_name>`` is assigned a value, it will be logged.
If you don't know what regex is, simply using the full name of the attribute as ``<attr_name>`` will allow you to log the attribute

Log Function Entry
------------------

You can log when a function is called. This is helpful to label the timeline for some crucial function.
The log will be displayed as an Instant Event.

.. code-block:: 

    viztracer --log_func_entry <func_name> -- my_script.py

``--`` is added to resolve the ambiguity. Every time an function matches regex ``<func_name>`` is called, it will be logged.
If you don't know what regex is, simply using the full name of the function as ``<func_name>`` will allow you to log the function 

Log Function Execution
----------------------

You can log function execution details. VizTracer will record all the assignments in specified functions and display
them in the detailed information of the generated report. The log will be showed in function entry's ``args`` list.

.. code-block:: 

    viztracer --log_func_exec <func_name> -- my_script.py

``--`` is added to resolve the ambiguity. Every time an function matches regex ``<func_name>`` is called, its execution will be logged.
If you don't know what regex is, simply using the full name of the function as ``<func_name>`` will allow you to log the function 

Log Exception
-------------

You can log raised exception. All raised exceptions, whether caught or not, will be displayed as an Instant Event
in the report.

.. code-block:: 

    viztracer --log_exception my_script.py

Log Function Arguments 
----------------------

You can log every function's arguments as ``string``, aka their ``__repr__``. The arguments will be stored in each python function entry 
under ``args["func_args"]``. You can overwrite the object's ``__repr__`` function to log the object as you need.

You can enable this feature in command line or using inline. 

.. code-block:: 
    
    viztracer --log_func_args my_script.py

.. code-block:: python
    
    tracer = VizTracer(log_func_args=True)

**This feature will introduce a very large overhead(depends on your argument list), so be aware of it**

You can log additional arbitrary (key, value) pairs for your function entry using ``add_func_args()``. Refer to :doc:`viztracer` for it's usage

Log Function Return Value
-------------------------

VizTracer can log every function's return value as ``string``, aka it's ``__repr__``. The return value will be stored in each python function entry 
under ``args["return_value"]``. You can overwrite the object's ``__repr__`` function to log the object as you need.

You can enable this feature in command line or using inline. 

.. code-block:: 
    
    viztracer --log_func_retval my_script.py

.. code-block:: python
    
    tracer = VizTracer(log_func_retval=True)


Log Print
---------

You can intercept ``print()`` function and record the data it prints to the report as an Instant Event. This is like doing print debug on timeline.

You can do this simply by:

.. code-block:: 

    viztracer --log_print my_script.py

OR

.. code-block:: python

    tracer = VizTracer(log_print=True)

Log Garbage Collector
---------------------

You can log the optional garbage collector module in Python. Notice that in CPython, most garbage collection is done using 
reference count. The garbage collector module is only responsible for the cycle reference. So this feature is mainly used
to detect cycle reference collection status, and the time consumed by running the optional garbage collector.

You can do this simply by:

.. code-block:: 

    viztracer --log_gc my_script.py

OR

.. code-block:: python

    tracer = VizTracer(log_gc=True)

Work with ``logging`` module
----------------------------

VizTracer can work with python builtin ``logging`` module by adding a handler to it. The report will show logging
data as Instant Events.

.. code-block:: python

    from viztracer import VizTracer, VizLoggingHandler

    tracer = VizTracer()
    handler = VizLoggingHandler()
    handler.setTracer(tracer)
    # A handler is added to logging so logging will dump data to VizTracer
    logging.basicConfig(handlers = [handler])
