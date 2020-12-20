# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt


# A third party developer who wants to develop based on VizTracer can do a plugin
# Simply inherit VizPluginBase class and finish the methods. Then you can load it
# by VizTracer(plugins=[YourVizPlugin()])

class VizPluginBase:
    def __init__(self):
        pass

    def message(self, m_type: str, payload: dict):
        """
        This is the only interface with VizTracer. To make it simple and flexible,
        we use m_type for message type, and the payload could be any json compatible
        data. This is more extensible in the future
        :param m_type str: the message type VizPlugin is receiving
        :param payload dict: payload of the message

        :return dict: always return a dict. Return None if nothing needs to be done
                      by VizTracer. Otherwise refer to the docs
        """
        return {}


class VizPluginManager:
    def __init__(self, tracer, plugins):
        self._tracer = tracer
        self._plugins = []
        for plugin in plugins:
            if isinstance(plugin, VizPluginBase):
                plugin_instance = plugin
            elif isinstance(plugin, str):
                plugin_instance = self._get_plugin_from_string(plugin)
            else:
                raise TypeError("Invalid plugin!")
            self._plugins.append(plugin_instance)
            plugin_instance.message("event", {"when": "initialize"})

    def _get_plugin_from_string(self, plugin):
        args = plugin.split()
        module = args[0]
        try:
            package = __import__(module)
        except (ImportError, ModuleNotFoundError):
            print(f"There's no module named {module}, maybe you need to install it")
            exit(1)

        m = package
        if "." in module:
            # package.module
            names = module.split(".")

            try:
                for mod in names[1:]:
                    m = m.__getattribute__(mod)
            except AttributeError:  # pragma: no cover
                # This in theory should never happen
                raise ImportError(f"Unable to import {module}, wrong path")
        try:
            m = m.__getattribute__("get_vizplugin")
        except AttributeError:
            print(f"Unable to find get_vizplugin in {module}. Incorrect plugin.")
            exit(1)

        if callable(m):
            return m(plugin)
        else:
            print(f"Unable to find get_vizplugin as a callable in {module}. Incorrect plugin.")
            exit(1)

    def event(self, when):
        for plugin in self._plugins:
            ret = plugin.message("event", {"when": when})
            self.resolve(ret)

    def resolve(self, ret):
        if not ret or "action" not in ret:
            return
        if ret["action"] == "handle_data":
            ret["handler"](self._tracer.data)
