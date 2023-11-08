Basic Usage
===========

Command Line
------------

The easiest way to use VizTracer is through command line. Assume you have a python script to profile and the normal way to run it is:

.. code-block::

    python3 my_script.py


You can simply use VizTracer by

.. code-block::
    
    # These two commands are equivalent. 
    # In this docs, they might both be used, but you can choose either one that you prefer.
    viztracer my_script.py
    # OR
    python3 -m viztracer my_script.py

which will generate a ``result.json`` file in the directory you run this command. You can open it with ``vizviewer``

.. code-block::

    vizviewer result.json

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

You can specify the output file using ``-o`` or ``--output_file`` argument. The default output file is ``result.json``. 
Three types of files are supported, html, json and gz(gzip of json file).

.. code-block::

    viztracer -o other_name.html my_script.py
    viztracer -o other_name.json my_script.py
    viztracer -o other_name.json.gz my_script.py

You can also show flamegraph from ``result.json`` file

.. code-block::

    vizviewer --flamegraph result.json

Inline
------

Sometimes the command line may not work as you expected, or you do not want to profile the whole script. You can manually start/stop the profiling in your script as well.

First of all, you need to import ``VizTracer`` class from the package

.. code-block:: python

    from viztracer import VizTracer

You can trace code with the ``with`` statement

.. code-block:: python
    
    with VizTracer(output_file="optional.json") as tracer:
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

.. code-block:: python

    # you can define arguments of VizTracer in magic
    %%viztracer -p 8888
    # Your code after

A ``Show VizTracer Report`` button will appear after the cell and you can click it to view the results.

Cell magic ``%%viztracer`` supports some of the command line arguments:

* ``--port``
* ``--output_file``
* ``--max_stack_depth``
* ``--ignore_c_function``
* ``--ignore_frozen``
* ``--log_func_args``
* ``--log_print``
* ``--log_sparse``

Display Report
--------------

VizTracer will generate a ``result.json`` by default, which could be opened with ``vizviewer``

.. code-block::

    vizviewer result.json

You can also display all the files in a directory and open the reports in browser too. This is helpful
when you have many files in one directory and want to check some or all of them.

This could also be used when you have a report directory where reports are frequently added. You can
leave ``vizviewer`` in the background and browse your reports with pure browser.

.. code-block::

    vizviewer your_directory/

``vizviewer`` will bring up webbrowser and open the report by default. You can disable this feature and
only host an HTTP server on ``localhost:9001``, which you can access through your browser

.. code-block::

    vizviewer --server_only result.json

If you do not want to host the HTTP server forever, you can use ``--once`` so the server will shut down
after serving the trace file

.. code-block::

    vizviewer --once result.json

You can serve your HTTP server on a different port with ``--port`` or its equivalent ``-p``

.. code-block::

    vizviewer --port 10000 result.json

You can also show flamegraph of the result

.. code-block::

    vizviewer --flamegraph result.json

You can use the external trace processor with ``--use_external_processor``, which does not have the
RAM limits as the browser. This is helpful when you try to open a large trace file.

.. code-block::

    vizviewer --use_external_processor result.json

``vizviewer`` can also show standalone html report - it just host a simple HTTP server for the file

.. code-block::

    vizviewer result.html

Or, you can use ``--open`` for ``viztracer``, it will then open the report after it generates it

.. code-block::

    viztracer --open my_script.py
    viztracer -o result.html --open my_script.py

Circular Buffer Size
--------------------

VizTracer uses a circular buffer to store the entries. When there are too many entries, it will only store the latest ones so you know what happened
recently. The default buffer size is 1,000,000(number of entries), which takes about 150MiB disk space. You can specify this when you instantiate a ``VizTracer`` object

Notice it also takes a significant amount of RAM when VizTracer is tracing the program.

VizTracer will preallocate about ``tracer_entries * 100B`` RAM for circular buffer. It also requires about ``1-2MB`` per 10k entries to
dump the json file.

.. code-block:: python

    viztracer --tracer_entries 500000 my_script.py

OR

.. code-block:: python

    tracer = VizTracer(tracer_entries=500000)

Configuration file
------------------

You can use a configuration file to set the default options for ``viztracer``, which could help you avoid typing the same arguments for multiple runs.

The default filename for ``viztracer`` configuration file is ``.viztracerrc``. `viztracer` will try to find ``.viztracerrc`` in current working directory.
You can also specify your own configuration file with
``viztracer --rcfile <your_config_file>``. The format of the configuration file is very similar to ``ini`` file, which could be parsed by
built in ``configparser``.

.. code-block::

    [default]
    log_var = a.* latest
    ignore_c_function = True
    output_file = vizreport.json
    max_stack_depth = 10

``[default]`` can't be omitted and all the arguments should be in a key-value pair format, where the key is the argument name(without ``--``) and the val is the
value you need to pass in. Please notice that there are some arguments in ``viztracer`` that do not take parameters(like `--ignore_c_function``), you
need to pass ``True`` in the config file to make the config parser happy. If you need to pass multiple parameters to an argument(like ``log_var``), just
use space to separate the parameters like you do in cmdline interface.

Combine Reports
---------------

VizTracer can put multiple json reports together and generate a new trace file. This is especially helpful when you have multiple
trace generators, for example, running multiple processes with VizTracer. As VizTracer uses Monotonic Clock, you can save reports
with different VizTracer instances without worrying about timestamp alignment issue. You can even generate your own data and
combine with VizTracer reports, like VizPlugins does.

.. code-block::

    viztracer --combine process1.json process2.json -o full_report.json

Another usage of combining reports would be to compare between different runs of the same program. Unlike combining from multiple
sources, this requires a pre-alignment of all the trace data. VizTracer also provides a way to align the start of all reports for
this usage.

.. code-block::

    viztracer --align_combine run1.json run2.json -o compare_report.json

Compress Your Report
--------------------

VizTracer supports compressing your json report. The general compression ratio is about 50:1 to 100:1 for a large report.

You can compress your report with ``--compress``.

.. code-block:: 

    viztracer --compress result.json -o result.cvf 

You can also decompress your report with ``--decompress``

.. code-block:: 

    viztracer --decompress result.cvf -o result.json 
