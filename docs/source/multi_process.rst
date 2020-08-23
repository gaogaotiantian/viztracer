Multi Process
=============

VizTracer can support multi process with some extra steps. The current structure of VizTracer keeps one single buffer for one process, which means the user will have to produce multiple results from multiple processes and combine them together. 

If you are using ``os.fork()`` or libraries using similiar mechanism, you can use VizTracer the normal way you do, with an extra option ``pid_suffix``.

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

If your code is using ``subprocess`` to spawn processes, the newly spawned process won't be traced(We could do something to ``PATH`` but that feels sketchy). There are a couple ways to deal with that:

* You can change the ``subprocess`` or ``popen`` code manually, to attach VizTracer to sub-process. You will have json results from differnt processes and you just need to combine them together. This is a generic way to do multi-process tracing and could work pretty smoothly if you don't have many entries for your subprocess

* Or you can hack your ``PATH`` env to use ``python -m viztracer <args>`` to replace ``python``. This will make VizTracer attach your spawned process automatically, but could have other side effects.