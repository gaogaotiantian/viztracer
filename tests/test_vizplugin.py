# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt


from .cmdline_tmpl import CmdlineTmpl
from viztracer import VizTracer
from viztracer.vizplugin import VizPluginBase


class MyPlugin(VizPluginBase):
    def __init__(self):
        self.event_counter = 0

    def message(self, m_type, payload):

        def f(data):
            pass

        self.event_counter += 1
        if m_type == "pre-parse":
            return {
                "action": "handle_data",
                "handler": f
            }
        return {}


class TestVizPlugin(CmdlineTmpl):
    def test_basic(self):
        pl = MyPlugin()
        tracer = VizTracer(plugins=[pl])
        tracer.start()
        tracer.stop()
        tracer.save()
        self.assertEqual(pl.event_counter, 4)

    def test_invalid(self):
        invalid_pl = []
        with self.assertRaises(TypeError):
            _ = VizTracer(plugins=[invalid_pl])

    def test_cmdline(self):
        self.template(["viztracer", "--plugin", "tests.modules.dummy_vizplugin", "--", "cmdline_test.py"])
        self.template(["viztracer", "--plugin", "tests.modules.dummy_vizplugin_wrong", "--", "cmdline_test.py"], success=False)
        self.template(["viztracer", "--plugin", "tests.modules", "--", "cmdline_test.py"], success=False)
        self.template(["viztracer", "--plugin", "invalid", "--", "cmdline_test.py"], success=False)
