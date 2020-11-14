Decorator
=========

.. py:decorator:: ignore_function

    ``@ignore_function`` can tell VizTracer to skip on functions you specified. 

    .. code-block:: python

        # This only works when there's a globally registered tracer
        @ignore_function
        def function_you_want_to_ignore():
            # function body

        # You can specify tracer if no global tracer is registered 
        @ignore_function(tracer=tracer)
        def function_you_want_to_ignore():
            # function body

.. py:decorator:: trace_and_save(method=None, output_dir="./", **viztracer_kwargs)
    
    :param function method: trick to make both ``@trace_and_save`` and ``@trace_and_save(**kwargs)`` work
    :param str output_dir: output directory you want to put your logs in
    :param dict viztracer_kwargs: kwargs for VizTracer

    ``@trace_and_save`` can be used to trace a certain function and save the result as the program goes. 
    This can be very helpful when you are running a very long program and just want to keep recording 
    something periodically. You won't drain your memory and the parsing/dumping will be done in a new process,
    which can minimize the performance impact to your main process. 

    You can pass any argument you want to ``VizTracer`` by giving it to the decorator

    .. code-block:: python

        @trace_and_save(output_dir="./mylogs", ignore_c_function=True)
        def function_you_want_to_trace():
            # function body

        # this works as well
        @trace_and_save
        def function_you_want_to_trace():
            # function body