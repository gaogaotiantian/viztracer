Remote Attach
=============

VizTracer supports remote attach so you don't need to start the process with VizTracer.
This is helpful when you don't want to restart the process to trace it. You can run
the process once and forever, and only attach VizTracer when you want to trace it.
The process will run normally without performance hit when you are not attaching VizTracer.

*This feature does not support Windows*

To attach to the process and trace it, you have to install VizTracer on the process you
want to trace

.. code-block:: python

    from viztracer import VizTracer
    tracer = VizTracer()
    tracer.install()

``tracer.install()`` will basically add handlers for ``SIGUSR1`` and ``SIGUSR2`` which
are only available on Unix. This also requires the program not using these two signals.

Then when you are running this process, you can attach to it with VizTracer, using it's pid

.. code-block::

    viztracer --attach <pid>
    
By default, you need to Ctrl+C out of viztracer to save the report. Be aware that it is
the attached process rather than attaching process(viztracer) that is saving the report,
so it's the attached process's resource that is being spent. This also means, if you need
other options, you should specify them in ``VizTracer`` instance in attached process.

You can also trace for a period of time using ``-t``

.. code-block::

    viztracer --attach <pid> -t <seconds>
