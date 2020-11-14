Custom Events
=============

You may want to insert custom events to the report while you are tracing the program. 

VizTracer supports three kinds of custom events:

* Instant Event
* Counter Event
* Object Event

Instant Event
-------------

Instant Event is a log at a specific timestamp, showing as a vertical line. It's useful
to log a transient event. You need to give it an event name and pass in an arbitrary
argument that is **JSONIFIABLE**. The argument will be displayed in the report.

.. code-block:: python

    tracer.add_instant("Event1", {"a": 1})

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