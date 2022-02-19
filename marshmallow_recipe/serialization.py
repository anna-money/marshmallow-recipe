import dataclasses
from typing import Any, Type, TypeVar, cast

import marshmallow as m

from .bake import bake_schema
from .naming_case import DEFAULT_CASE, NamingCase

_T = TypeVar("_T")
_MARSHMALLOW_VERSION_MAJOR = int(m.__version__.split(".")[0])


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class _SchemaKey:
    cls: type
    naming_case: NamingCase


_schemas: dict[_SchemaKey, m.Schema] = {}


def schema(cls: Type[_T], *, naming_case: NamingCase = DEFAULT_CASE) -> m.Schema:
    key = _SchemaKey(cls=cls, naming_case=naming_case)
    existent_schema = _schemas.get(key)
    if existent_schema is not None:
        return existent_schema

    if _MARSHMALLOW_VERSION_MAJOR >= 3:
        new_schema = bake_schema(cls, naming_case=naming_case)()
    else:
        new_schema = bake_schema(cls, naming_case=naming_case)(strict=True)  # type: ignore
    _schemas[key] = new_schema
    return new_schema


def load(cls: Type[_T], data: dict[str, Any], *, naming_case: NamingCase = DEFAULT_CASE) -> _T:
    if _MARSHMALLOW_VERSION_MAJOR >= 3:
        loaded = schema(cls, naming_case=naming_case).load(data)
    else:
        loaded, errors = schema(cls, naming_case=naming_case).load(data)
        if errors:
            raise ValueError(f"Schema {schema} must be strict")
    return cast(_T, loaded)


def load_many(cls: Type[_T], data: dict[str, Any], *, naming_case: NamingCase = DEFAULT_CASE) -> list[_T]:
    if _MARSHMALLOW_VERSION_MAJOR >= 3:
        loaded = schema(cls, naming_case=naming_case).load(data, many=True)
    else:
        loaded, errors = schema(cls, naming_case=naming_case).load(data, many=True)
        if errors:
            raise ValueError(f"Schema {schema} must be strict")
    return cast(list[_T], loaded)


def dump(
    data: _T,
    *,
    naming_case: NamingCase = DEFAULT_CASE,
) -> dict[str, Any]:
    if _MARSHMALLOW_VERSION_MAJOR >= 3:
        dumped = schema(type(data), naming_case=naming_case).dump(data)
    else:
        dumped, errors = schema(type(data), naming_case=naming_case).dump(data)
        if errors:
            raise ValueError(f"Schema {schema} must be strict")
    return cast(dict[str, Any], dumped)


def dump_many(data: list[_T], *, naming_case: NamingCase = DEFAULT_CASE) -> list[dict[str, Any]]:
    if not data:
        return []

    if _MARSHMALLOW_VERSION_MAJOR >= 3:
        dumped = schema(type(data[0]), naming_case=naming_case).dump(data, many=True)
    else:
        dumped, errors = schema(type(data[0]), naming_case=naming_case).dump(data, many=True)
        if errors:
            raise ValueError(f"Schema {schema} must be strict")
    return cast(list[dict[str, Any]], dumped)
