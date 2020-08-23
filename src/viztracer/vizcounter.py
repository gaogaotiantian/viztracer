from .event_base import _EventBase


class VizCounter(_EventBase):
    def _viztracer_log(self):
        d = {}
        for attr in self._viztracer_get_attr_list():
            if hasattr(self, attr):
                val = self.__getattribute__(attr)
                if not callable(val):
                    if type(val) is int or type(val) is float:
                        d[attr] = val
                    else:
                        raise Exception("Counter can only take numeric values")
        self._viztracer_tracer.add_counter(self._viztracer_name, d)
