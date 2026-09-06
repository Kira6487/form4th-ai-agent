import json
from typing import Any

from sqlalchemy.types import UserDefinedType


class Vector768(UserDefinedType):
    """pgvector-compatible type that remains usable by the SQLite unit fixture."""

    cache_ok = True

    def __init__(self, dimensions: int = 768) -> None:
        self.dimensions = dimensions

    def get_col_spec(self, **_: Any) -> str:
        return f"vector({self.dimensions})"

    def bind_processor(self, _dialect: Any):
        def process(value: list[float] | None) -> str | None:
            if value is None:
                return None
            return "[" + ",".join(format(float(item), ".12g") for item in value) + "]"

        return process

    def result_processor(self, _dialect: Any, _coltype: Any):
        def process(value: Any) -> list[float] | None:
            if value is None:
                return None
            if isinstance(value, str):
                try:
                    return [float(item) for item in json.loads(value)]
                except (ValueError, TypeError, json.JSONDecodeError):
                    return [float(item) for item in value.strip("[]").split(",") if item]
            return [float(item) for item in value]

        return process
