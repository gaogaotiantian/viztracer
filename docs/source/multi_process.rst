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

os.fork()
---------

If you are using ``os.fork()`` or libraries using similiar mechanism, you can use VizTracer the normal way you do, with an extra option ``pid_suffix``.
You will generate one ``json`` file per process, and use ``viztracer`` to combine them to a report.

.. code-block::
    
    python -m viztracer --pid_suffix multi_process_program.py

This way, the program will generate mutliple ``json`` files in current working directory. Notice here, if ``--pid_suffix`` is passed to VizTracer, the default output format will be ``json`` because this is only expected to be used by multi-process programs. 

You can specify the output directory if you want

.. code-block::

    python -m viztracer --pid_suffix --output_dir ./temp_dir multi_process_program.py

After generating ``json`` files, you need to combine them

.. code-block::
    
    python -m viztracer --combine ./temp_dir/*.json

This will generate the HTML report with all the process info. You can specify ``--output_file`` when using ``--combine``.

Actually, you can combine any json reports together to an HTML report. 
