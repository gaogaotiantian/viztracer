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

.. py:decorator:: log_sparse(func=None, stack_depth=0, dynamic_tracer_check=False)

    You can make VizTracer log only certain functions using ``--log_sparse`` mode.

    :param function func: callable to decorate
    :param int stack_depth: log the function and its descendants with a limit stack depth
    :param bool dynamic_tracer_check: run time check of tracer

    .. code-block:: python

        from viztracer import log_sparse

        # @log_sparse will only log this function
        @log_sparse
        def function_you_want_to_log():
            # function body

        # @log_sparse(stack_depth=5) will log this function and its descendants
        # with a limit stack depth of 5
        # Nested @log_sparse with stack_depth won't work
        # (only the outermost function and its stack will be logged)
        @log_sparse(stack_depth=5)
        def function_you_want_to_log():
            # function body

        # Use dynamic_tracer_check=True if you use tracer as a context manager (or with %%viztracer).
        @log_sparse(dynamic_tracer_check=True)
        def function_you_want_to_log():
            # function body

        with VizTracer(log_sparse=True):
            function_you_want_to_log()
