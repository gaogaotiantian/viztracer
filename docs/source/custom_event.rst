Custom Event
============

``_EventBase`` is the base class of ``VizCounter`` and ``VizObject``. It should never be used directly.

.. py:class:: _EventBase(tracer,\
            name=None,\
            trigger_on_change=True\
            include_attributes=[]\
            exclude_attributes=[])
    
    .. py:attribute:: tracer
        :type: VizTracer

        an object of ``VizTracer``
        
        ``tracer`` can be set to ``None`` so the logging operation will be ``NOP``. Your program will
        run normally with the instrumented code even when you are not using viztracer. 
    
    .. py:attribute:: name
        :type: string
        :value: None

        name of the event which will show on trace viewer. If not specified, class name will be used

    .. py:attribute:: trigger_on_change
        :type: boolean
        :value: True

        whether to trigger log every time a public attribute is changed
    
    .. py:attribute:: include_attributes
        :type: list of string
        :value: []

        a list of attributes that will trigger the log and be included in the report. If not empty, ``_EventBase`` will behave like whitelist

    .. py:attribute:: exclude_attributes
        :type: list of string
        :value: []

        a list of attributes that will not trigger the log and not be included in the report. If not empty, ``_EventBase`` will behave like blacklist

    .. py:method:: log()
    .. py:method:: _viztracer_log()

        manually log the current attributes

    .. py:method:: config()
    .. py:method:: _viztracer_set_config(key, value)

        :param str key: ``"trigger_on_change"``, ``"include_attributes"`` or ``"exclude_attribtues"``
        :param value: the value you want to set on corresponding config
    
    .. py:decoratormethod:: triggerlog(when="after")

        :param str when: ``"after"``, ``"before"`` or ``"both"`` to specify when the ``log()`` function is called

        ``triggerlog`` is a decorator for class methods to do auto-log when the method is called. 


.. py:class:: VizCounter(_EventBase)

    ``VizCounter`` should be used to track a numeric variable through time. You can track CPU usage, memory usage, or any numeric variable you are interested in using ``VizCounter``

    .. code-block:: python

        from viztraer import VizTracer, VizCounter
        tracer = VizTracer()
        tracer.start()
        counter = VizCounter(tracer, "counter name")
    
    Because ``VizCounter`` has ``trigger_on_change`` on by default, any writes to its public attributes(does not start with ``_``) will be automatically logged

    .. code-block:: python

        counter.a = 2
        counter.b = 1.2

    You can turn ``trigger_on_change`` off and manually decide when to log

    .. code-block:: python

        counter = VizCounter(tracer, "counter name", trigger_on_change=False)
        # OR
        counter = VizCounter(tracer, "counter name")
        counter.config("trigger_on_change", False)

    .. code-block:: python

        counter.a = 1
        counter.b = 1
        # Until here, nothing happens
        counter.log() # trigger the log

.. py:class:: VizObject(_EventBase)

    ``VizObject`` is almost exactly the same as ``VizCounter``, with the exception that ``VizObject`` can log jsonifiable objects(``dict``, ``list``, ``string``, ``int``, ``float``)


Inheritance
-----------

In practice, you can inherit from ``VizCounter`` or ``VizObject`` class and build your own class so it will be much easier to track the data in your class. Remember you need to do ``__init__`` function of the base class! If your class has a lot of attributes and they are frequently being written to, it is wise to turn off ``trigger_on_change``

.. code-block:: python

    class MyClass(VizObject):
        def __init__(self, tracer):
            super().__init__(tracer, "my name", trigger_on_change=False)

You can manually do log by

.. code-block:: python

    obj = MyClass(tracer)
    obj.log()

or you can decorate your class method with ``triggerlog`` to trigger log on function call

.. code-block:: python

    class MyClass(VizObject):
        @VizObject.triggerlog
        def log_on_this_function():
            #function