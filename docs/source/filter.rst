Filter
======

Sometimes, you may have too many data entries and you want to filter some of them out to either improve the performance or make the report clearer.
VizTracer provides multiple filters for your needs.

Min Duration
------------

You can ask VizTracer to only record entries that last longer than a period of time

.. code-block::

    viztracer --min_duration 0.2ms my_script.py

OR

.. code-block:: python

    tracer = VizTracer(min_duration=200)

Notice that with command line interface, ``viztracer`` expects a string representing a period of time,
which should be in format of ``<val><unit>``. ex. ``0.2ms``, ``300ns``, ``5.5us``. You can also omit
the unit and it would be parsed as ``us``, ex. ``0.5`` is the same as ``0.5us``.

But as an argument to ``VizTracer``, it should be a number of ``us``.

The default value of ``min_duration`` is ``0``, meaning every function entry is recorded.

Max Stack depth
---------------

You can limit maximum stack depth to trace by

.. code-block::

    viztracer --max_stack_depth 10 my_script.py

OR

.. code-block:: python

    tracer = VizTracer(max_stack_depth=10)

Include Files
---------------

You can include only certain files/folders to trace by

.. code-block::

    # -- is used to resolve ambiguity
    viztracer --include_files ./src -- my_script.py

OR

.. code-block:: python

    tracer = VizTracer(include_files=["./src"])

Exclude Files
---------------

Similarly, you can exclude certain files/folders to trace by

.. code-block::

    # -- is used to resolve ambiguity
    viztracer --exclude_files ./not_interested.py -- my_script.py

OR

.. code-block:: python

    tracer = VizTracer(exclude_files=["./not_interested.py"])

Ignore C Function
-----------------

By default, VizTracer will trace both python and C functions. You can turn off tracing C functions by

.. code-block::

    viztracer --ignore_c_function my_script.py

OR

.. code-block:: python

    tracer = VizTracer(ignore_c_function=True)

Since most of the builtin functions(like ``append`` or ``len``) are C functions which are frequently called,
ignoring C functions often improves the overhead and file size significantly.


Ignore Non File
---------------

You can ask VizTracer not to trace any functions that are not in a valid file(mostly import stuff) using ``ignore_frozen``

.. code-block::

    viztracer --ignore_frozen my_script.py

OR

.. code-block:: python

    tracer = VizTracer(ignore_frozen=True)


Ignore Function
---------------

It's possible that you want to ignore some arbitrary functions and their descendants. You can do it using ``@ignore_function`` decorator

.. code-block:: python

    from viztracer import ignore_function
    # This only works when there's a globally registered tracer
    @ignore_function
    def some_function():
        # nothing inside will be traced

.. _log_sparse_label:

Log Sparse
----------

You can make VizTracer log only certain functions using ``--log_sparse``. This is helpful when you are only interested in the time spent on
specific functions for a big picture on larger projects.

First, you need to add decorator ``@log_sparse`` on the function you want to log

.. code-block:: python

    from viztracer import log_sparse

    # @log_sparse will only log this function
    @log_sparse
    def function_you_want_to_log():
        # function body

    # @log_sparse(stack_depth=5) will log this function and its descendants
    # with a limit stack depth of 5
    # Nested @log_sparse with stack_depth won't work
    # (only the outermost function and its stack will be logged)
    @log_sparse(stack_depth=5)
    def function_you_want_to_log():
        # function body

    # Use dynamic_tracer_check=True if you use tracer as a context manager (or with %%viztracer).
    @log_sparse(dynamic_tracer_check=True)
    def function_you_want_to_log():
        # function body

    with VizTracer(log_sparse=True):
        function_you_want_to_log()

Then just call viztracer with ``--log_sparse``

.. code-block::

    viztracer --log_sparse your_script.py

When you are using ``--log_sparse``, due to the nature of the recording, some advanced features may not work with it.

You can leave ``@log_sparse`` as it is when you are not running the script with VizTracer. It will be like a no-op

If you want to log a piece of code, rather than a full function, please check :ref:`duration_event_label`. Duration Event
is compatible with ``log_sparse``

To use ``@log_sparse`` in conjunction with a context manager, you must define decorating functions within the created
context, or set the `dynamic_tracer_check=True`` argument of decorator. The second option leads to runtime checks,
so it increases the overhead.
