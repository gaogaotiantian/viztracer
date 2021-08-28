# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt


import sys
from typing import Dict, Optional, Sequence, Union, TYPE_CHECKING

from . import __version__
from .util import compare_version, color_print


if TYPE_CHECKING:
    from .viztracer import VizTracer  # pragma: no cover


class VizPluginError(Exception):
    pass


# A third party developer who wants to develop based on VizTracer can do a plugin
# Simply inherit VizPluginBase class and finish the methods. Then you can load it
# by VizTracer(plugins=[YourVizPlugin()])

class VizPluginBase:
    def __init__(self):
        pass

    def support_version(self):
        # You have to overload this to return the latest version of viztracer
        # your plugin supports. This is for API backward compatibility.
        # Simply return the version string
        # For example:
        #     return "0.10.5"
        raise NotImplementedError("Plugin of viztracer has to implement support_version method")

    def message(self, m_type: str, payload: Dict) -> Dict:
        """
        This is the only logical interface with VizTracer. To make it simple and flexible,
        we use m_type for message type, and the payload could be any json compatible
        data. This is more extensible in the future
        :param m_type str: the message type VizPlugin is receiving
        :param payload dict: payload of the message

        :return dict: always return a dict. Return None if nothing needs to be done
                      by VizTracer. Otherwise refer to the docs
        """
        if m_type == "command":
            if payload["cmd_type"] == "terminate":
                return {"success": True}

        return {}


class VizPluginManager:
    def __init__(self, tracer: "VizTracer", plugins: Sequence[Union[VizPluginBase, str]]):
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
            self._send_message(plugin_instance, "event", {"when": "initialize"})

    def _get_plugin_from_string(self, plugin: str) -> VizPluginBase:
        args = plugin.split()
        module = args[0]
        try:
            package = __import__(module)
        except (ImportError, ModuleNotFoundError):
            print(f"There's no module named {module}, maybe you need to install it")
            sys.exit(1)

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
            sys.exit(1)

        if callable(m):
            return m(plugin)
        else:
            print(f"Unable to find get_vizplugin as a callable in {module}. Incorrect plugin.")
            sys.exit(1)

    def _send_message(self, plugin: VizPluginBase, m_type: str, payload: Dict):
        # this is the only interface to communicate with vizplugin
        # in the future we may need to do version compatibility
        # here
        support_version = plugin.support_version()
        if compare_version(support_version, __version__) > 0:
            color_print("WARNING", "The plugin support version is higher than "
                                   "viztracer version. Consider update your viztracer")

        ret = plugin.message(m_type, payload)
        if m_type == "command":
            self.assert_success(plugin, payload, ret)
        else:
            self.resolve(support_version, ret)

    def event(self, when: str):
        for plugin in self._plugins:
            self._send_message(plugin, "event", {"when": when})

    def command(self, cmd: Dict):
        for plugin in self._plugins:
            self._send_message(plugin, "command", cmd)

    def terminate(self):
        self.command({"cmd_type": "terminate"})
        for plugin in self._plugins:
            del plugin
        self._plugins = []

    def assert_success(self, plugin: VizPluginBase, cmd: Dict, ret: Optional[Dict]):
        if not ret or "success" not in ret or not ret["success"]:
            raise VizPluginError(f"{plugin} failed to process {cmd}")

    def resolve(self, version: str, ret: Dict):
        if not ret or "action" not in ret:
            return
        if ret["action"] == "handle_data":
            ret["handler"](self._tracer.data)
