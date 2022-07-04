import dataclasses
from typing import Any, Callable, Type, TypeVar, cast

import marshmallow as m

from .bake import bake_schema
from .naming_case import NamingCase

_T = TypeVar("_T")
_MARSHMALLOW_VERSION_MAJOR = int(m.__version__.split(".")[0])


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class _SchemaKey:
    cls: type
    many: bool
    naming_case: NamingCase | None


_schemas: dict[_SchemaKey, m.Schema] = {}

if _MARSHMALLOW_VERSION_MAJOR >= 3:

    def schema(cls: Type[_T], *, many: bool = False, naming_case: NamingCase | None = None) -> m.Schema:
        key = _SchemaKey(cls=cls, many=many, naming_case=naming_case)
        existent_schema = _schemas.get(key)
        if existent_schema is not None:
            return existent_schema
        new_schema = bake_schema(cls, naming_case=naming_case)(many=many)
        _schemas[key] = new_schema
        return new_schema

    def load(cls: Type[_T], data: dict[str, Any], *, naming_case: NamingCase | None = None) -> _T:
        loaded: _T = schema(cls, naming_case=naming_case).load(data)
        return loaded

    def load_many(cls: Type[_T], data: list[dict[str, Any]], *, naming_case: NamingCase | None = None) -> list[_T]:
        loaded: list[_T] = schema(cls, many=True, naming_case=naming_case).load(data)
        return loaded

    def dump(
        data: _T,
        *,
        naming_case: NamingCase | None = None,
    ) -> dict[str, Any]:
        data_schema = schema(type(data), naming_case=naming_case)
        dumped: dict[str, Any] = data_schema.dump(data)
        if errors := data_schema.validate(dumped):
            raise m.ValidationError(errors)
        return dumped

    def dump_many(data: list[_T], *, naming_case: NamingCase | None = None) -> list[dict[str, Any]]:
        if not data:
            return []
        data_schema = schema(type(data[0]), many=True, naming_case=naming_case)
        dumped: list[dict[str, Any]] = data_schema.dump(data)
        if errors := data_schema.validate(dumped):
            raise m.ValidationError(errors)
        return dumped

else:

    def schema(cls: Type[_T], *, many: bool = False, naming_case: NamingCase | None = None) -> m.Schema:
        key = _SchemaKey(cls=cls, many=many, naming_case=naming_case)
        existent_schema = _schemas.get(key)
        if existent_schema is not None:
            return existent_schema
        new_schema = bake_schema(cls, naming_case=naming_case)(strict=True, many=many)  # type: ignore
        _schemas[key] = new_schema
        return new_schema

    def load(cls: Type[_T], data: dict[str, Any], *, naming_case: NamingCase | None = None) -> _T:
        loaded, _ = schema(cls, naming_case=naming_case).load(data)
        return cast(_T, loaded)

    def load_many(cls: Type[_T], data: list[dict[str, Any]], *, naming_case: NamingCase | None = None) -> list[_T]:
        loaded, _ = schema(cls, many=True, naming_case=naming_case).load(data)
        return cast(list[_T], loaded)

    def dump(
        data: _T,
        *,
        naming_case: NamingCase | None = None,
    ) -> dict[str, Any]:
        dumped, _ = schema(type(data), naming_case=naming_case).dump(data)
        return cast(dict[str, Any], dumped)

    def dump_many(data: list[_T], *, naming_case: NamingCase | None = None) -> list[dict[str, Any]]:
        if not data:
            return []
        dumped, _ = schema(type(data[0]), many=True, naming_case=naming_case).dump(data)
        return cast(list[dict[str, Any]], dumped)


EmptySchema = m.Schema


def get_load_func(cls: Type[_T], *, naming_case: NamingCase | None = None) -> Callable[[dict[str, Any]], _T]:
    def _load(data: dict[str, Any]) -> _T:
        return load(cls, data, naming_case=naming_case)

    return _load


def get_dump_func(_: Type[_T], *, naming_case: NamingCase | None = None) -> Callable[[_T], dict[str, Any]]:
    def _dump(data: _T) -> dict[str, Any]:
        return dump(data, naming_case=naming_case)

    return _dump
