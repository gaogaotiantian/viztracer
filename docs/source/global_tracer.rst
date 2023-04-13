Global Tracer Object
====================

Some features in VizTracer require a ``VizTracer`` object so it's helpful to make the tracer object accessible globally.

When you are using command line entry ``viztracer your_script.py``, you don't need to worry about it. The tracer will be
automatically registered and you can access it from any file. 

When you instantiate the ``VizTracer`` object like ``tracer = VizTracer()`` in your script, it will be automatically
registered globally. It is *not* recommended to have multiple tracer objects in a single script. However, you can turn off
the global register by ``tracer = VizTracer(register_global=False)``

To access the tracer, do

.. code-block:: python

    from viztracer import get_tracer
    # get_tracer() will return None if no tracer is registered
    tracer = get_tracer()

When you use ``VizLoggingHandler`` or ``VizCounter`` or ``VizObject``, setting their tracer to ``None`` will make 
the logging a ``NOP``. This will enable you to leave the instrumentation code as it is and run your program both
regularly and with ``viztracer``

You can do things like:

.. code-block:: python

    from viztracer import VizLoggingHandler, get_tracer

    handler = VizLoggingHandler()

    handler.setTracer(get_tracer())

.. code-block:: python

    from viztracer import get_tracer, VizObject

    obj = VizObject(get_tracer(), "my variable")