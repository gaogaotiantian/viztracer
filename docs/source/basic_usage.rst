Basic Usage
===========

Command Line
------------

The easiest way to use VizTracer is through command line. Assume you have a python script to profile and the normal way to run it is:

.. code-block::

    python3 my_script.py


You can simply use VizTracer as 

.. code-block::
    
    # These two commands are equivalent. 
    # In this docs, they might both be used, but you can choose either one that you prefer.
    viztracer my_script.py
    # OR
    python3 -m viztracer my_script.py

which will generate a ``result.html`` file in the directory you run this command. Open it in browser and there's your result.

If your script needs arguments like 

.. code-block::
    
    python3 my_script.py arg1 arg2

Just feed it as it is to ``viztracer``

.. code-block::
    
    viztracer my_script.py arg1 arg2

It's possible that there's a conflict or an ambiguity. ``viztracer`` takes ``--`` as a separator between arguments to ``viztracer`` and
positional arguments to your script.

.. code-block::
    
    viztracer -o result.json -- my_script.py -o output_for_my_script.json

You can also run a module with VizTracer

.. code-block::

    viztracer -m your_module

You can specify the output file using ``-o`` or ``--output_file`` argument. The default output file is ``result.html``. 
Three types of files are supported, html, json and gz(gzip of json file).

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

First of all, you need to import ``VizTracer`` class from the package

.. code-block:: python

    from viztracer import VizTracer

You can trace code with ``with`` statement

.. code-block:: python
    
    with VizTracer(output_file="optional.html") as tracer:
        # Something happens here

Or you can create a ``VizTracer`` object and manually enable/disable the profile using ``start()`` and ``stop()`` function.

.. code-block:: python

    tracer = VizTracer()
    tracer.start()
    # Something happens here
    tracer.stop()
    tracer.save() # also takes output_file as an optional argument

Jupyter
-------

If you are using Jupyter, you can use viztracer cell magics.

.. code-block:: python

    # You need to load the extension first
    %load_ext viztracer

.. code-block:: python

    %%viztracer
    # Your code after

A ``Show VizTracer Report`` button will appear after the cell and you can click it to view the results

Display Report
--------------

VizTracer will generate a ``result.html`` by default, which could be opened in Chrome directly. However, there are multiple ways
to display VizTracer report.

Currently, there are three front-end tools that could be used for VizTracer reports

- Catapult Trace Viewer(Chrome Trace Viewer)
- Perfetto
- Modified Catapult Trace Viewer

The Modified Catapult Trace Viewer can show source code of the program, while perfetto is actively maintained and uses
latest technologies.

The easiest way is to use ``vizviewer`` to load the report, which will open the webbrowser for you and load your report.

.. code-block::

    # Use Modified Catapult Trace Viewer
    vizviewer result.html

    # Use Perfetto
    vizviewer result.json
    vizviewer result.json.gz

Or, you can use ``--open`` for ``viztracer``, it will then open the report after it generates it

.. code-block::

    # Use Modified Catapult Trace Viewer
    viztracer -o result.html --open my_script.py

    # Use Perfetto
    viztracer -o result.json --open my_script.py
    viztracer -o result.json.gz --open my_script.py

If you generate an ``html`` report, you can also just open it in Chrome. If you generate ``json`` or ``gz`` report, you can
load it in `Perfetto <https://ui.perfetto.dev/>`_ or chrome://tracing.

Circular Buffer Size
--------------------

VizTracer used circular buffer to store the entries. When there are too many entries, it will only store the latest ones so you know what happened
recently. The default buffer size is 1,000,000(number of entries), which takes about 150MiB memory. You can specify this when you instantiate ``VizTracer`` object

Be aware that 150MiB is disk space, it requires more RAM to load it on Chrome.

.. code-block:: python

    viztracer --tracer_entries 500000 my_script.py

OR

.. code-block:: python

    tracer = VizTracer(tracer_entries=500000)

Debug Your Saved Report
-----------------------

VizTracer allows you to debug your json report just like pdb. You can understand how your program is executed by 
interact with it. Even better, you can **go back in time** because you know what happened before. 

.. code-block:: 

    vdb <your_json_report>

For detailed commands, please refer to :doc:`virtual_debug`
