VizPlugin
=========

In this doc, we will show how to build your own plugin for VizTracer.

Every plugin should inherit ``VizPluginBase`` from ``viztracer.vizplugin``

.. py:class:: VizPluginBase(self)

    .. py:method:: message(self, m_type, payload)

        :param str m_type: type of message
        :param dict payload: a very flexible payload with the message
        :return: the corresponding return value. Could be an action, or a respond.
        :rtype: dict

        As of now, ``message()`` only supports two kinds of ``m_type`` - ``"event"`` and ``"command"``.

        ``"event"`` has a payload that has key ``"when"``, to indicate when the event happens. 

        ``"when"`` could be ``initialize``, ``pre-start``, ``post-stop`` or ``pre-save``.

        When ``"event"`` type message is received, the plugin can return an action, with key ``"action"`` set to the
        action it needs. For now the only one supported is ``"handle_data"``, with which you also
        needs to provide a data handler ``"handler"``

        return ``{}`` if you don't want to do anything

        ``"command"`` has a payload that has key ``"cmd_type"``, to indicate what VizTracer expects the plugin to do.

        ``"cmd_type"`` could only be ``"terminate"`` for now. ``"terminate"`` command is guaranteed before viztracer exits
        when commandline interface is used. However, if you are using viztracer inline, you will have to explicitly run
        ``tracer.terminate()`` unless you are using ``with VizTracer()``.

        When ``"command"`` type message is received, the plugin has to return a dict like ``{"success": True}`` to 
        inform VizTracer that the plugin received the command and did what it asked.

        .. code-block::python

            def message(self, m_type, payload):
                if m_type == "event":
                    if payload["when"] == "pre-start":
                        self.do_something()
                    elif payload["when"] == "pre-save":
                        return({"action":"handle_data", "handler", self.handler})
                elif m_type == "command":
                    if payload["cmd_type"] == "terminate":
                        # release all the resources here
                        return({"success": True})
                
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
