from typing import Any, TypeVar, cast

from .bake import StrictTypedSchema

_T = TypeVar("_T")


def load(schema: StrictTypedSchema[_T], data: dict[str, Any]) -> _T:
    loaded, errors = schema.load(data)
    if errors:
        raise ValueError(f"Schema {schema} must be strict")
    return cast(_T, loaded)


def load_many(schema: StrictTypedSchema[_T], data: dict[str, Any]) -> list[_T]:
    loaded, errors = schema.load(data, many=True)
    if errors:
        raise ValueError(f"Schema {schema} must be strict")
    return cast(list[_T], loaded)


def dump(schema: StrictTypedSchema[_T], data: _T) -> dict[str, Any]:
    dumped, errors = schema.dump(data)
    if errors:
        raise ValueError(f"Schema {schema} must be strict")
    return cast(dict[str, Any], dumped)


def dump_many(schema: StrictTypedSchema[_T], data: list[_T]) -> list[dict[str, Any]]:
    dumped, errors = schema.dump(data, many=True)
    if errors:
        raise ValueError(f"Schema {schema} must be strict")
    return cast(list[dict[str, Any]], dumped)
