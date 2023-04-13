Custom Events
=============

You may want to insert custom events to the report while you are tracing the program. 

VizTracer supports three kinds of custom events:

* Instant Event
* Variable Event
* Duration Event

Instant Event
-------------

Instant Event is a log at a specific timestamp, showing as an arrow. It's useful
to log a transient event. You need to give it a ``name`` which is a string, and an
argument ``args``. They will be displayed in the report

``args`` has to be a jsonifiable object, normally a string, or a combination
of dict, list, string and number.

``scope`` can be set to ``t``(default), ``p`` or ``g``, for thread, process and
global.

.. code-block:: python

    tracer.log_instant(f"Event1", args=args, scope="p")

Variable Event
--------------

Variable Event is a way to log a specific variable in your program and display it in the report.

If the variable you log is a number, VizTracer will use a counter event to display it, otherwise
instant event will be used.

A ``name`` should be given for the variable, then the variable itself

.. code-block:: python

    trace.log_var("name for the var", var)


Magic Comment
-------------

You can use magic comment to log instant events and variable events.

In this way, you'll have 0 overhead and side effect when you run your program normally, and log the events when you use
viztracer to trace it

.. code-block:: python

    # !viztracer: log_instant("start logging")
    a = 3
    # !viztracer: log_var("a", a)

Or you can use inline magic comment ``# !viztracer: log``, which will log the assigned value if the statement is an assign
or it will log an instant event indicating this line is executed

.. code-block:: python

    # This will log an instant event with name "f()"
    f()  # !viztracer: log

    # This will log the variable a
    a = 3  # !viztracer: log

You can also do conditional log with ``if``

.. code-block:: python

    # This will log the variable a
    a = 3  # !viztracer: log if a == 3
    # This has the same effect
    # !viztracer: log_var("a", a)

You need ``--magic_comment`` option for ``viztracer`` to trigger the magic comment

.. code-block::

    viztracer --magic_comment your_program.py

.. _duration_event_label:

Duration Event
--------------

Duration Event is almost the same as function call event that normally being logged automatically,
with the only exception that it does not have to be a function.

You can log any piece of code using duration event and it will look like a function call event
in your final report.

.. code-block:: python
    
    from viztracer import get_tracer

    with get_tracer().log_event("my event name"):
        # some code running here

You should use ``log_event`` method of your tracer, which is accessible through ``get_tracer()``
function when you are using CLI, or just pass the tracer if you are using inline.

This feature is especially helpful when you are using :ref:`log_sparse_label`.