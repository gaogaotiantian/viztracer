# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

import functools
from typing import Any, Callable, Dict, List, Optional

from .viztracer import VizTracer


class _EventBase:
    def __init__(self, tracer: VizTracer, name: str = "", **kwargs):
        self._viztracer_tracer: VizTracer = tracer
        self._viztracer_name: str = name
        self._viztracer_enable: bool = False
        self._viztracer_config: Dict = {
            "trigger_on_change": True,
            "include_attributes": [],
            "exclude_attributes": []
        }

        for key in kwargs:
            if key in self._viztracer_config:
                self._viztracer_config[key] = kwargs[key]

        self._viztracer_enable = True

    def __setattr__(self, name: str, value: Any) -> None:
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

    def _viztracer_get_attr_list(self) -> List[str]:
        if self._viztracer_config["include_attributes"]:
            return self._viztracer_config["include_attributes"]
        else:
            return [attr for attr in self.__dir__()
                    if not attr.startswith("_") and attr not in self._viztracer_config["exclude_attributes"]]

    def _viztracer_set_config(self, key: str, value: Any) -> None:
        if key not in self._viztracer_config:
            raise ValueError("No config named {}".format(key))
        self._viztracer_config[key] = value

    def config(self, key: str, value: Any) -> None:
        self._viztracer_set_config(key, value)

    def _viztracer_log(self) -> None:
        raise NotImplementedError("You should not use _EventBase class directly")

    def log(self) -> None:
        self._viztracer_log()

    @staticmethod
    def triggerlog(method: Optional[Callable] = None, when: str = "after"):
        if when not in ["after", "before", "both"]:
            raise ValueError("when has to be one of 'after', 'before' or 'both', not {}".format(when))

        def inner(func: Callable) -> Callable:

            @functools.wraps(func)
            def wrapper(self, *args, **kwargs) -> Any:
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
