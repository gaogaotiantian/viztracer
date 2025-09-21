from __future__ import annotations
import json
from typing import Any

json_decode_error_types: tuple[type[Exception], ...] = (
    json.JSONDecodeError,
)

try:
    import orjson
    json_decode_error_types = (
        *json_decode_error_types,
        orjson.JSONDecodeError,
    )
except ImportError:
    orjson = None  # type: ignore[assignment]


def to_json_bytes(o: Any) -> bytes:
    if orjson:
        return orjson.dumps(o)
    return json.dumps(o).encode("utf-8")


def to_json_str(o: Any) -> str:
    if orjson:
        return orjson.dumps(o).decode("utf-8")
    return json.dumps(o)


def from_json(o: str | bytes):
    if orjson:
        return orjson.loads(o)
    return json.loads(o)
