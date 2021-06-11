Custom Events
=============

You may want to insert custom events to the report while you are tracing the program. 

VizTracer supports four kinds of custom events:

* Instant Event
* Counter Event
* Object Event
* Duration Event

Instant Event
-------------

Instant Event is a log at a specific timestamp, showing as an arrow. It's useful
to log a transient event. You need to give it a name which is a string and that's
all the information you can get in the report 

.. code-block:: python

    tracer.add_instant(f"Event1 - {my_data}")

Counter Event
-------------

Counter Event is used to log a numerical value over time. You need to instantiate a 
``VizCounter`` object or inherit your class from ``VizCounter``. 

.. code-block:: python

    counter = VizCounter(tracer, "counter name")
    counter.a = 10
    # Something
    counter.a = 20

Every write to the ``VizCounter`` object will trigger a log entry and it will be displayed
on the report as a separate signal

You can refer to :doc:`custom_event` for more details about the usage

Object Event
------------

Counter Event is used to log an object over time. You need to instantiate a 
``VizObject`` object or inherit your class from ``VizObject``. 

.. code-block:: python

    obj = VizObject(tracer, "object name")
    counter.s = "I can log string"
    # Something
    counter.t = "All attributes will be displayed"

Every write to the ``VizObject`` object will trigger a log entry and it will be displayed
on the report as a separate signal

You can refer to :doc:`custom_event` for more details about the usage

.. _duration_event_label:

Duration Event
--------------

Duration Event is almost the same as function call event that normally being logged automatically,
with the only exception that it does not have to be a function.

You can log any piece of code using duration event and it would look like a function call event
in your final report.

.. code-block:: python
    
    from viztracer import get_tracer

    with get_tracer().log_event("my event name"):
        # some code running here

You should use ``log_event`` method of your tracer, which is accessible through ``get_tracer()``
function when you are using CLI, or just pass the tracer if you are using inline.

This feature is especially helpful when you are using :ref:`log_sparse_label`.