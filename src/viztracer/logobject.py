import functools


class LogObject:
    def __init__(self, tracer, name=None):
        self._viztracer_tracer = tracer
        if name:
            self._viztracer_name = name
        else:
            self._viztracer_name = str(self.__class__)
        self._viztracer_id = str(id(self))
        self._viztracer_tracer.add_object("N", self._viztracer_id, self._viztracer_name)
        self._viztracer_attr_list = []

    def __del__(self):
        if self._viztracer_tracer:
            self._viztracer_tracer.add_object("D", self._viztracer_id, self._viztracer_name)

    def _viztracer_snapshot(self):
        d = {}
        for attr in self._viztracer_attr_list:
            val = self.__getattribute__(attr)
            if type(val) is int or type(val) is float:
                d[attr] = val
            else:
                d[attr] = str(val)
        self._viztracer_tracer.add_object("O", self._viztracer_id, self._viztracer_name, {"snapshot": d})

    def set_viztracer_attributes(self, attr_lst):
        if type(attr_lst) is not list:
            raise Exception("You need to pass a list of string to set_viztracer_attributes!")
        for elem in attr_lst:
            if type(elem) is not str:
                raise Exception("You need to pass a list of string to set_viztracer_attributes!")
        self._viztracer_attr_list = attr_lst[:]

    @staticmethod
    def snapshot(method=None, when="after"):
        if when not in ["after", "before", "both"]:
            raise Exception("when has to be one of 'after', 'before' or 'both', not {}".format(when))

        def inner(func):
            functools.wraps(func)

            def wrapper(self, *args, **kwargs):
                if when == "before" or when == "both":
                    self._viztracer_snapshot()
                ret = func(self, *args, **kwargs)
                if when == "after" or when == "both":
                    self._viztracer_snapshot()
                return ret
            return wrapper

        if method:
            return inner(method)
        return inner
