Basic Usage
===========

Command Line
------------

The easiest way to use VizTracer is through command line. Assume you have a python script to profile and the normal way to run it is:

.. code-block::

    python3 my_script.py


You can simply use VizTracer as 

.. code-block::
    
    # These two commands are equivalent. In this docs, they might both be used, but you can choose either one that you prefer.
    viztracer my_script.py
    # OR
    python3 -m viztracer my_script.py

which will generate a ``result.html`` file in the directory you run this command. Open it in browser and there's your result.

If your script needs arguments like 

.. code-block::
    
    python3 my_script.py arg1 arg2

Just feed it as it is to VizTracer

.. code-block::
    
    viztracer my_script.py arg1 arg2

You can specify the output file using ``-o`` or ``--output_file`` argument. The default output file is ``result.html``. Three types of files are supported, html, json and gz(gzip of json file).

.. code-block::

    viztracer -o other_name.html my_script.py
    viztracer -o other_name.json my_script.py
    viztracer -o other_name.json.gz my_script.py

By default, VizTracer only generates trace file, either in HTML format or json. You can have VizTracer to generate a flamegraph as well by 

.. code-block::
    
    viztracer --save_flamegraph my_script.py

Inline
------

Sometimes the command line may not work as you expected, or you do not want to profile the whole script. You can manually start/stop the profiling in your script as well.

First of all, you need to import ``VizTracer`` class from the package, and make an object of it.

.. code-block:: python

    from viztracer import VizTracer
    
    tracer = VizTracer()

If your code is executable by ``exec`` function, you can simply call ``tracer.run()``

.. code-block:: python
    
    tracer.run("import random;random.randrange(10)")

This will as well generate a ``result.html`` file in your current directory. You can pass other file path to the function if you do not like the name ``result.html``

.. code-block:: python
    
    tracer.run("import random; random.randrange(10)", output_file="better_name.html")

When you need a more delicate profiler, you can manually enable/disable the profile using ``start()`` and ``stop()`` function.

.. code-block:: python

    tracer.start()
    # Something happens here
    tracer.stop()
    tracer.save() # also takes output_file as an optional argument

Or, you can do it with ``with`` statement

.. code-block:: python
    
    with VizTracer(output_file="optional.html") as tracer:
        # Something happens here