# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

from viztracer.vizplugin import VizPluginBase


class DummyVizPlugin(VizPluginBase):
    def support_version(self):
        return "0.10.5"


def get_vizplugin(arg):
    return DummyVizPlugin()
