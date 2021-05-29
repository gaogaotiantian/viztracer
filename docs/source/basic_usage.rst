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

VizTracer will generate a ``result.json`` by default, which could be opened with ``vizviewer``

.. code-block::

    vizviewer result.json

``vizviewer`` will bring up webbrowser and open the report by default. You can disable this feature and
only host an HTTP server on ``localhost:9001``, which you can access through your browser

.. code-block::

    vizviewer --server_only result.json

If you do not want to host the HTTP server forever, you can use ``--once`` so the server will shut down
after serve the trace file

.. code-block::

    vizviewer --once result.json

You can also show flamegraph of the result

.. code-block::

    vizviewer --flamegraph result.json

``vizviewer`` can also show standalone html report - it just host a simple HTTP server for the file

.. code-block::

    vizviewer result.html

Or, you can use ``--open`` for ``viztracer``, it will then open the report after it generates it

.. code-block::

    viztracer --open my_script.py
    viztracer -o result.html --open my_script.py

Circular Buffer Size
--------------------

VizTracer used circular buffer to store the entries. When there are too many entries, it will only store the latest ones so you know what happened
recently. The default buffer size is 1,000,000(number of entries), which takes about 150MiB disk space. You can specify this when you instantiate ``VizTracer`` object

Notice it also takes significant amount of RAM when VizTracer is tracing the program.

VizTracer will preallocate about ``tracer_entries * 100B`` RAM for circular buffer. It also requires about ``1-2MB`` per 10k entries to
dump the json file.

.. code-block:: python

    viztracer --tracer_entries 500000 my_script.py

OR

.. code-block:: python

    tracer = VizTracer(tracer_entries=500000)

Combine Reports
---------------

VizTracer can put multiple json reports together and generate a new trace file. This is especially helpful when you have multiple
trace generators, for example, running multiple processes with VizTracer. As VizTracer uses Monotonic Clock, you can save reports
with different VizTracer instances without worrying about timestamp alignment issue. You can even generate your own data and
combine with VizTracer reports, like VizPlugins does.

.. code-block::

    viztracer --combine process1.json process2.json -o full_report.html

Another usage of combining reports would be to compare between different runs of the same program. Unlike combining from multiple
sources, this requires a pre-alignment of all the trace data. VizTracer also provides a way to align the start of all reports for
this usage.

.. code-block::

    viztracer --align_combine run1.json run2.json -o compare_report.html

Debug Your Saved Report
-----------------------

VizTracer allows you to debug your json report just like pdb. You can understand how your program is executed by 
interact with it. Even better, you can **go back in time** because you know what happened before. 

.. code-block:: 

    vdb <your_json_report>

For detailed commands, please refer to :doc:`virtual_debug`
