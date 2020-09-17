# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

from .event_base import _EventBase


class VizObject(_EventBase):
    def __init__(self, tracer, name, **kwargs):
        super().__init__(tracer, name, **kwargs)
        self._viztracer_id = str(id(self))
        if self._viztracer_tracer:
            self._viztracer_tracer.add_object("N", self._viztracer_id, self._viztracer_name)

    def __del__(self):
        if self._viztracer_tracer:
            self._viztracer_tracer.add_object("D", self._viztracer_id, self._viztracer_name)

    def _viztracer_log(self, ph="O"):
        if not self._viztracer_tracer:
            return
        d = {}
        for attr in self._viztracer_get_attr_list():
            if hasattr(self, attr):
                val = self.__getattribute__(attr)
                if type(val) is list or type(val) is dict or type(val) is int or type(val) is float or type(val) is str:
                    d[attr] = val
        self._viztracer_tracer.add_object(ph, self._viztracer_id, self._viztracer_name, {"snapshot": d})
