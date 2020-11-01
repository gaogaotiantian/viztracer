Multi Process
=============

subprocess
----------

VizTracer supports ``subprocess`` module with ease. You only need to add ``--log_subprocess`` to make it work

.. code-block::

    viztracer --log_subprocess my_script.py

This will generate an HTML file for all processes. There are a couple of things you need to be aware though. 

VizTracer patches subprocess module(to be more specific, ``subprocess.Popen``) to make this work like a magic. However, it will only patch
when the args passed to ``subprocess.Popen`` is a list(``subprocess.Popen(["python", "subscript.py"])``) and the first argument starts with
``python``. This covers most of the cases, but if you do have a situation that can't be solved, you can raise an issue and we can talk
about solutions.

multiprocessing or os.fork()
----------------------------

If you are using multiprocessing library or pure ``os.fork()``. You can enable multi-process log by passing ``--log_multiprocess``. 

.. code-block::

    viztracer --log_multiprocess my_script.py

This will generate an HTML file for all processes.

This feature is only available on UNIX, not Windows. Also it will only work when ``multiprocessing.get_start_method()`` is ``fork``. 
After python3.8, MacOS has start method "spawn" by default and "fork" should be considered unsafe. 

combine reports
---------------

You can generate json reports from different processes and combine them manually as well. It is recommended to use 
``--pid_suffix`` so the report will be json file ends with its pid. You can specify your own file name using ``-o`` too. 

.. code-block::
    
    viztracer --pid_suffix single_process.py
    # or
    viztracer -o process1.json single_process.py

You can specify the output directory if you want

.. code-block::

    viztracer --pid_suffix --output_dir ./temp_dir single_process.py

After generating ``json`` files, you need to combine them

.. code-block::
    
    viztracer --combine ./temp_dir/*.json

This will generate the HTML report with all the process info. You can specify ``--output_file`` when using ``--combine``.
