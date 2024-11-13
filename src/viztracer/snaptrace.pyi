# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt


from typing import Any, Callable, Dict, List, Optional


class Tracer:
    threadtracefunc: Callable

    include_files: Optional[List[str]]
    exclude_files: Optional[List[str]]

    def __init__(self, tracer_entries: int) -> None:
        ...

    def start(self) -> None:
        ...

    def stop(self, stop_option: Optional[str] = None) -> None:
        ...

    def resume(self) -> None:
        ...

    def pause(self) -> None:
        ...

    def clear(self) -> None:
        ...

    def load(self) -> Dict[str, Any]:
        ...

    def dump(self, filename: str, sanitize_function_name: bool = False) -> None:
        ...

    def setignorestackcounter(self, value: int) -> int:
        ...

    def _set_curr_stack_depth(self, stack_depth: int) -> None:
        ...

    def getts(self) -> float:
        ...

    def setpid(self, pid: int = -1, /) -> None:
        ...

    def add_func_args(self, key: str, value: Any) -> None:
        ...

    def get_func_args(self) -> Optional[Dict[str, Any]]:
        ...

    def add_raw(self, raw: Dict[str, Any]) -> None:
        ...

    def add_object(self, ph: str, obj_id: str, name: str, args: Optional[Dict[str, Any]] = None) -> None:
        ...

    def add_counter(self, name: str, args: Dict[str, Any]) -> None:
        ...

    def add_instant(self, name: str, args: Any = None, scope: str = "g") -> None:
        ...
