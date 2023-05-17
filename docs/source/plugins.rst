Plugins
=======

VizTracer supports third party plugins that comply to the specification of VizTracer.

To use a plugin, you need to install the plugin first. For example, if you want to use
a plugin named ``vizplugins``

.. code-block::

    pip install vizplugins

Then you need to pass the plugin to ``viztracer`` using ``--plugins``

.. code-block::

    viztracer --plugins vizplugins -- my_script.py

There could be multiple plugins to use in a package, which are differentiate by modules.
You can specify the module where plugin lives(you should refer to the plugin's doc for
detailed usage)

.. code-block::

    viztracer --plugins vizplugins.cpu_time -- my_script.py

You can even pass arguments to the plugin, but you need double quotes to pack them
together.

.. code-block::

    viztracer --plugins "vizplugins.cpu_time -f 100" -- my_script.py

You can also do it inline, just pass the string or the plugin object itself in a list to VizTracer

.. code-block:: python

    tracer = VizTracer(plugins=["vizplugins.cpu_time"])
    # Or
    tracer = VizTracer(plugins=[vizplugins.CpuTimePlugin()])

    # To gracefully terminate all plugins, you need to do terminate
    tracer.terminate()

.. code-block:: python

    # You can use with statement to avoid explicitly terminate
    with VizTracer(plugins=["vizplugins.cpu_time"]):
        # Do your stuff here

If you want to develop your own plugin for VizTracer, take a look at :doc:`viz_plugin`
