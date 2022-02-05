Remote Attach
=============

Attach
------

VizTracer supports remote attach so you don't need to start the process with VizTracer.
This is helpful when you don't want to restart the process to trace it. You can run
the process once and forever, and only attach VizTracer when you want to trace it.
The process will run normally without performance hit when you are not attaching VizTracer.

*This feature does not support Windows*

To attach to the process and trace it, you have two ways:

1. You can attach to an arbitrary Python process, as long as viztracer is importable in that process
2. You can attach to a Python process that already installed VizTracer

The first way is more flexible - it will inject code into the process to load `viztracer`. You can even pass
arguments from `viztracer` command line.

.. code-block::

    viztracer --attach <pid> -o result.json

** viztracer has to be importable in the attaching process otherwise it will raise an exception **
** gdb is required on Linux, and lldb is required on MacOS **

All the arguments will be sent to the attached process to instantiate a `VizTracer` object.

By default, you need to Ctrl+C out of viztracer to save the report. Be aware that it is
the attached process rather than attaching process(viztracer) that is saving the report,
so it's the attached process's resource that is being spent.

You can also trace for a period of time using ``-t``

.. code-block::

    viztracer --attach <pid> -t <seconds>

Even though this looks decent, there are some dark magic going under the rug and you may want to do
something cleaner, which brings up the second way - install viztracer in the process you want to profile.
Another good thing about this way is that it's threading-aware. Even if you attach after spawning threads,
you can still get profile data from the other threads.

.. code-block:: python

    from viztracer import VizTracer
    tracer = VizTracer()
    tracer.install()

``tracer.install()`` will basically add handlers for ``SIGUSR1`` and ``SIGUSR2`` which
are only available on Unix. This also requires the program not using these two signals.

Then when you are running this process, you can attach to it with VizTracer, using it's pid

.. code-block::

    viztracer --attach_installed <pid>
    
If you need other options, you should specify them in ``VizTracer`` instance in attached process.

Uninstall
---------

There could be time when you want to "uninstall" VizTracer from a process. For example, for some
reason, the attach process failed and VizTracer is left on in the process. You can do that
with:

.. code-block::

    viztracer --uninstall <pid>
