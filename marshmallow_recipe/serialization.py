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

if _MARSHMALLOW_VERSION_MAJOR >= 3:

    def schema(cls: Type[_T], *, naming_case: NamingCase = DEFAULT_CASE) -> m.Schema:
        key = _SchemaKey(cls=cls, naming_case=naming_case)
        existent_schema = _schemas.get(key)
        if existent_schema is not None:
            return existent_schema
        new_schema = bake_schema(cls, naming_case=naming_case)()
        _schemas[key] = new_schema
        return new_schema

    def load(cls: Type[_T], data: dict[str, Any], *, naming_case: NamingCase = DEFAULT_CASE) -> _T:
        return cast(_T, schema(cls, naming_case=naming_case).load(data))

    def load_many(cls: Type[_T], data: dict[str, Any], *, naming_case: NamingCase = DEFAULT_CASE) -> list[_T]:
        return cast(list[_T], schema(cls, naming_case=naming_case).load(data, many=True))

    def dump(
        data: _T,
        *,
        naming_case: NamingCase = DEFAULT_CASE,
    ) -> dict[str, Any]:
        return cast(dict[str, Any], schema(type(data), naming_case=naming_case).dump(data))

    def dump_many(data: list[_T], *, naming_case: NamingCase = DEFAULT_CASE) -> list[dict[str, Any]]:
        if not data:
            return []
        return cast(list[dict[str, Any]], schema(type(data[0]), naming_case=naming_case).dump(data, many=True))

else:

    def schema(cls: Type[_T], *, naming_case: NamingCase = DEFAULT_CASE) -> m.Schema:
        key = _SchemaKey(cls=cls, naming_case=naming_case)
        existent_schema = _schemas.get(key)
        if existent_schema is not None:
            return existent_schema
        new_schema = bake_schema(cls, naming_case=naming_case)(strict=True)  # type: ignore
        _schemas[key] = new_schema
        return new_schema

    def load(cls: Type[_T], data: dict[str, Any], *, naming_case: NamingCase = DEFAULT_CASE) -> _T:
        loaded, errors = schema(cls, naming_case=naming_case).load(data)
        if errors:
            raise ValueError(f"Schema {schema} must be strict")
        return cast(_T, loaded)

    def load_many(cls: Type[_T], data: dict[str, Any], *, naming_case: NamingCase = DEFAULT_CASE) -> list[_T]:
        loaded, errors = schema(cls, naming_case=naming_case).load(data, many=True)
        if errors:
            raise ValueError(f"Schema {schema} must be strict")
        return cast(list[_T], loaded)

    def dump(
        data: _T,
        *,
        naming_case: NamingCase = DEFAULT_CASE,
    ) -> dict[str, Any]:
        dumped, errors = schema(type(data), naming_case=naming_case).dump(data)
        if errors:
            raise ValueError(f"Schema {schema} must be strict")
        return cast(dict[str, Any], dumped)

    def dump_many(data: list[_T], *, naming_case: NamingCase = DEFAULT_CASE) -> list[dict[str, Any]]:
        if not data:
            return []
        dumped, errors = schema(type(data[0]), naming_case=naming_case).dump(data, many=True)
        if errors:
            raise ValueError(f"Schema {schema} must be strict")
        return cast(list[dict[str, Any]], dumped)
