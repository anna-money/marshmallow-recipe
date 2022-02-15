import dataclasses
from typing import Any, Type, TypeVar, cast

import marshmallow as m

from .bake import bake_schema
from .naming_case import DEFAULT_CASE, NamingCase
from .none_value_handling import NoneValueHandling

_T = TypeVar("_T")


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class _SchemaKey:
    cls: type
    strict: bool
    naming_case: NamingCase
    none_value_handling: NoneValueHandling


_schemas: dict[_SchemaKey, m.Schema] = {}


def schema(
    cls: Type[_T],
    *,
    strict: bool = True,
    naming_case: NamingCase = DEFAULT_CASE,
    none_value_handling: NoneValueHandling = NoneValueHandling.EXCLUDE,
) -> m.Schema:
    key = _SchemaKey(cls=cls, strict=strict, naming_case=naming_case, none_value_handling=none_value_handling)
    existent_schema = _schemas.get(key)
    if existent_schema is not None:
        return existent_schema

    new_schema = bake_schema(cls, naming_case=naming_case, none_value_handling=none_value_handling)(strict=strict)
    _schemas[key] = new_schema
    return new_schema


def load(
    cls: Type[_T],
    data: dict[str, Any],
    *,
    naming_case: NamingCase = DEFAULT_CASE,
    none_value_handling: NoneValueHandling = NoneValueHandling.EXCLUDE,
) -> _T:
    cls_schema = schema(cls, strict=True, naming_case=naming_case, none_value_handling=none_value_handling)
    loaded, errors = cls_schema.load(data)
    if errors:
        raise ValueError(f"Schema {schema} must be strict")
    return cast(_T, loaded)


def load_many(
    cls: Type[_T],
    data: dict[str, Any],
    *,
    naming_case: NamingCase = DEFAULT_CASE,
    none_value_handling: NoneValueHandling = NoneValueHandling.EXCLUDE,
) -> list[_T]:
    cls_schema = schema(cls, strict=True, naming_case=naming_case, none_value_handling=none_value_handling)
    loaded, errors = cls_schema.load(data, many=True)
    if errors:
        raise ValueError(f"Schema {schema} must be strict")
    return cast(list[_T], loaded)


def dump(
    data: _T,
    *,
    naming_case: NamingCase = DEFAULT_CASE,
    none_value_handling: NoneValueHandling = NoneValueHandling.EXCLUDE,
) -> dict[str, Any]:
    data_schema = schema(type(data), strict=True, naming_case=naming_case, none_value_handling=none_value_handling)
    dumped, errors = data_schema.dump(data)
    if errors:
        raise ValueError(f"Schema {schema} must be strict")
    return cast(dict[str, Any], dumped)


def dump_many(
    data: list[_T],
    *,
    naming_case: NamingCase = DEFAULT_CASE,
    none_value_handling: NoneValueHandling = NoneValueHandling.EXCLUDE,
) -> list[dict[str, Any]]:
    if not data:
        return []

    element_schema = schema(
        type(data[0]), strict=True, naming_case=naming_case, none_value_handling=none_value_handling
    )
    dumped, errors = element_schema.dump(data, many=True)
    if errors:
        raise ValueError(f"Schema {schema} must be strict")
    return cast(list[dict[str, Any]], dumped)
