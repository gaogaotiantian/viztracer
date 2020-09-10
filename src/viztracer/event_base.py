# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

import functools


class _EventBase:
    def __init__(self, tracer, name=None, **kwargs):
        self._viztracer_tracer = tracer
        self._viztracer_name = name
        self._viztracer_enable = False
        self._viztracer_config = {
            "trigger_on_change": True,
            "include_attributes": [],
            "exclude_attributes": []
        }

        for key in kwargs:
            if key in self._viztracer_config:
                self._viztracer_config[key] = kwargs[key]

        self._viztracer_enable = True

    def __setattr__(self, name, value):
        self.__dict__[name] = value
        if not name.startswith("_"):
            if self._viztracer_enable and self._viztracer_config["trigger_on_change"]:
                if self._viztracer_config["include_attributes"]:
                    if name in self._viztracer_config["include_attributes"]:
                        self._viztracer_log()
                elif self._viztracer_config["exclude_attributes"]:
                    if name not in self._viztracer_config["exclude_attributes"]:
                        self._viztracer_log()
                else:
                    self._viztracer_log()

    def _viztracer_get_attr_list(self):
        if self._viztracer_config["include_attributes"]:
            return self._viztracer_config["include_attributes"]
        else:
            return [attr for attr in self.__dir__()
                    if not attr.startswith("_") and attr not in self._viztracer_config["exclude_attributes"]]

    def _viztracer_set_config(self, key, value):
        if key not in self._viztracer_config:
            raise ValueError("No config named {}".format(key))
        self._viztracer_config[key] = value

    def config(self, key, value):
        self._viztracer_set_config(key, value)

    def _viztracer_log(self):
        raise NotImplementedError("You should not use _EventBase class directly")

    def log(self):
        self._viztracer_log()

    @staticmethod
    def triggerlog(method=None, when="after"):
        if when not in ["after", "before", "both"]:
            raise ValueError("when has to be one of 'after', 'before' or 'both', not {}".format(when))

        def inner(func):

            @functools.wraps(func)
            def wrapper(self, *args, **kwargs):
                if when == "before" or when == "both":
                    self._viztracer_log()
                ret = func(self, *args, **kwargs)
                if when == "after" or when == "both":
                    self._viztracer_log()
                return ret
            return wrapper

        if method:
            return inner(method)
        return inner
