VizPlugin
=========

In this doc, we will show how to build your own plugin for VizTracer.

Every plugin should inherit ``VizPluginBase`` from ``viztracer.vizplugin``

.. py:class:: VizPluginBase(self)

    .. py:method:: message(self, m_type, payload)

        :param str m_type: type of message
        :param dict payload: a very flexible payload with the message
        :return: the action you want VizTracer to do
        :rtype: dict

        As of now, ``message()`` only supports one kind if ``m_type`` - ``"event"``. which
        works like a hook when VizTracer is doing something. 

        ``"event"`` has a payload that has key ``"when"``, to indicate when the event happens. 

        ``"when"`` could be ``initialize``, ``pre-start``, ``post-stop`` or ``pre-save``.

        For now, the only action VizTracer supports is ``handle_data``, with which you also
        needs to provide a data handler ``"handler"``

        return ``{}`` if you don't want to do anything

        .. code-block::python

            def message(self, m_type, payload):
                if m_type == "event":
                    if payload["when"] == "pre-start":
                        self.do_something()
                    elif payload["when"] == "pre-save":
                        self.return({"action":"handle_data", "handler", self.handler})
                
                return {}

You will also need a magic function defined to enable VizTracer to load your plugins from command line.
The function has to be named ```get_vizplugin(arg)```, which will return an instance of your plugin object
based on the arg given when it's called. You also need to put this function in the module that you want 
your use to use on command line.

For example, if I want my user to use my plugin as ``viztracer --plugins vizplugins -- my_script.py``, I
should put ``get_vizplugin()`` function in ``vizplugins/__init__.py``. Or if I want them to use as 
``viztracer --plugins vizplugins.cpu_time -- my_script.py``, I should put the function in
``vizplugins/cpu_time.py``

Be aware that **arg is an unparsed string** like "vizplugins.cpu_time f 100". You can split it yourself
and parse it the way you like. Or you can specify something special for your own plugin
