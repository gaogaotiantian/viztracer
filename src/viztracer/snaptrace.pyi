# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt


from typing import Any, Callable, Literal, Optional


class Tracer:
    threadtracefunc: Callable

    include_files: Optional[list[str]]
    exclude_files: Optional[list[str]]

    def __init__(self, tracer_entries: int, /) -> None:
        ...

    def start(self) -> None:
        ...

    def stop(self, stop_option: Optional[str]) -> None:
        ...

    def resume(self) -> None:
        ...

    def pause(self) -> None:
        ...

    def clear(self) -> None:
        ...

    def load(self) -> dict[str, Any]:
        ...

    def dump(self, filename: str, sanitize_function_name: bool = False) -> None:
        ...

    def setignorestackcounter(self, value: int) -> int:
        ...

    def _set_curr_stack_depth(self, stack_depth: int) -> None:
        ...

    def getts(self) -> float:
        ...

    def get_base_time(self) -> int:
        ...

    def setpid(self, pid: int = -1, /) -> None:
        ...

    def add_func_args(self, key: str, value: Any) -> None:
        ...

    def get_func_args(self) -> Optional[dict[str, Any]]:
        ...

    def add_raw(self, raw: dict[str, Any]) -> None:
        ...

    def add_object(self, ph: str, obj_id: str, name: str, args: Optional[dict[str, Any]] = None) -> None:
        ...

    def add_counter(self, name: str, args: dict[str, Any]) -> None:
        ...

    def add_instant(self, name: str, args: Any = None, scope: Literal["g", "p", "t"] = "g") -> None:
        ...
