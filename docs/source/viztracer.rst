VizTracer
=========

.. py:class:: VizTracer(self,\
                 tracer_entries=1000000,\
                 verbose=1,\
                 max_stack_depth=-1,\
                 include_files=None,\
                 exclude_files=None,\
                 ignore_c_function=False,\
                 ignore_frozen=False,\
                 log_func_retval=False,\
                 log_func_args=False,\
                 log_print=False,\
                 log_gc=False,\
                 log_async=False,\
                 pid_suffix=False,\
                 register_global=True,\
                 min_duration=0,\
                 output_file="result.json")

    .. py:attribute:: tracer_entries
        :type: integer
        :value: 1000000

        Size of circular buffer. The user can only specify this value when instantiate ``VizTracer`` object or if they use command line

        Please be aware that a larger number of entries also means more disk space, RAM usage and loading time. Be familiar with your computer's limit.

        ``tracer_entries`` means how many entries ``VizTracer`` can store. It's not a byte number.

        .. code-block::

            viztracer --tracer_entries 500000

    .. py:attribute:: verbose
        :type: integer
        :value: 1

        Verbose level of VizTracer. Can be set to ``0`` so it won't print anything while tracing 

        Setting it to ``0`` is equivalent to 

        .. code-block::

            viztracer --quiet

    .. py:attribute:: max_stack_depth
        :type: integer
        :value: -1

        Specify the maximum stack depth VizTracer will trace. ``-1`` means infinite.

        Equivalent to 

        .. code-block::

            viztracer --max_stack_depth <val>
    
    .. py:attribute:: include_files
        :type: list of string or None
        :value: None

        Specify the files or folders that VizTracer will trace. If it's not empty, VizTracer will function in whitelist mode, any files/folders not included will be ignored.
        
        Because converting code filename in tracer is too expensive, we will only compare the input and its absolute path against code filename, which could be a relative path. That means, if you run your program using relative path, but gives the ``include_files`` an absolute path, it will not be able to detect.

        Can't be set with ``exclude_files``

        Equivalent to 

        .. code-block::

            viztracer --include_files file1[ file2 [file3 ...]]

        **NOTICE**

        In command line, ``--include_files`` takes multiple arguments, which will be ambiguous about the command that actually needs to run, so you need to explicitly specify command using ``--``

        .. code-block::

            viztracer --include_files file1 file2 -- my_scrpit.py

    .. py:attribute:: exclude_files
        :type: list of string or None
        :value: None

        Specify the files or folders that VizTracer will not trace. If it's not empty, VizTracer will function in blacklist mode, any files/folders not included will be ignored.

        Because converting code filename in tracer is too expensive, we will only compare the input and its absolute path against code filename, which could be a relative path. That means, if you run your program using relative path, but gives the ``exclude_files`` an absolute path, it will not be able to detect.

        Can't be set with ``include_files``

        Equivalent to 

        .. code-block::

            viztracer --exclude_files file1[ file2 [file3 ...]]
        
        **NOTICE**

        In command line, ``--exclude_files`` takes multiple arguments, which will be ambiguous about the command that actually needs to run, so you need to explicitly specify command using ``--``

        .. code-block::

            viztracer --exclude_files file1 file2 -- my_scrpit.py

    .. py:attribute:: ignore_c_function
        :type: boolean
        :value: False

        Whether trace c function

        Setting it to ``True`` is equivalent to 

        .. code-block::

            viztracer --ignore_c_function

    .. py:attribute:: ignore_frozen
        :type: boolean
        :value: False

        Whether trace functions from frozen functions(mostly import stuff)

        Setting it to ``True`` is equivalent to 

        .. code-block::

            viztracer --ignore_frozen

    .. py:attribute:: log_func_retval 
        :type: boolean
        :value: False

        Whether log the return value of the function as string in report entry

        Setting it to ``True`` is equivalent to 

        .. code-block::

            viztracer --log_func_retval
    
    .. py:attribute:: log_func_args 
        :type: boolean
        :value: False

        Whether log the arguments of the function as string in report entry

        Setting it to ``True`` is equivalent to 

        .. code-block::

            viztracer --log_func_args
    
    .. py:attribute:: log_print 
        :type: boolean
        :value: False

        Whether replace the ``print`` function to log in VizTracer report

        Setting it to ``True`` is equivalent to 

        .. code-block::

            viztracer --log_print

    .. py:attribute:: log_gc 
        :type: boolean
        :value: False

        Whether log garbage collector

        Setting it to ``True`` is equivalent to 

        .. code-block::

            viztracer --log_gc

    .. py:attribute:: log_async
        :type: boolean
        :value: False

        Whether log async tasks as separate "thread" in vizviewer

        Setting it to ``True`` is equivalent to 

        .. code-block::

            viztracer --log_async
    
    .. py:attribute:: register_global
        :type: boolean
        :value: True
        
        whether register the tracer globally, so every file can use ``get_tracer()`` to get this tracer. When command line
        entry is used, the tracer will be automatically registered. When ``VizTracer()`` is manually instantiated, it will
        be registered as well by default. 
        
        Some functions may require a globally registered tracer to work.

        This attribute will only be effective when the object is initialized:

        .. code-block:: python

            tracer = VizTracer(register_global=False)

    .. py:attribute:: min_duration
        :type: float
        :value: 0

        Minimum duration of a function to be logged. The value is in unit of ``us``.

    .. py:attribute:: output_file
        :type: string
        :value: "result.json"

        Default file path to write report

        Equivalent to 

        .. code-block::

            viztracer -o <filepath>
    
    .. py:method:: run(command, output_file=None)

        run ``command`` and save report to ``output_file``
    
    .. py:method:: save(output_file=None)

        parse data and save report to ``output_file``. If ``output_file`` is ``None``, save to default path.
    
    .. py:method:: start()

        start tracing

    .. py:method:: stop()

        stop tracing

    .. py:method:: clear()

        clear all the data

    .. py:method:: cleanup()

        clear all the data and free the memory allocated

    .. py:method:: parse()

        parse the data collected, return number of total entries

    .. py:method:: enable_thread_tracing()

        enable tracing in the current thread, useful when you use multi-thread without builtin threading module

    .. py:method:: add_instant(name, scope="g")
        
        :param str name: name of this instant event
        :param str scope: one of ``g``, ``p`` or ``t`` for global, process or thread level event

        Add instant event to the report. 

    .. py:method:: add_func_args(name, key, value)
        
        :param str key: key to display in the report
        :param object value: a jsonifiable object

        This method allows you to attach args to the current function, which will show in the report when you click on the function 

    .. py:method:: log_event(event_name)

        :param str event_name: name of this event that will appear in the result
        :return: VizEvent object that should only be used with ``with`` statement
        :rtype: VizEvent

        .. code-block:: python

            with get_tracer().log_event("event name"):
                # some code here

    .. py:method:: set_afterfork(callback, *args, **kwargs)

        :param callable callback: the callback function after fork, should take a ``VizTracer`` object as the first argument
        :param list args: positional arguments to ``callback``
        :param dict kwargs: keyword arguments to ``callback``

        This method will register a callback function after the process is forked. If you want different behavior on child
        processes with ``multiprocessing``, you can utilize this method

        Notice that the ``callback`` argument should be a ``callable`` that takes a ``VizTracer`` object as the first argument

        .. code-block:: python

            from viztracer import get_tracer

            def afterfork_callback(tracer):
                tracer.max_stack_depth = 10
            
            get_tracer().set_afterfork(afterfork_callback)
