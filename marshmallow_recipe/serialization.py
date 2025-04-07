import dataclasses
import importlib.metadata
from typing import Any, TypeVar, overload

import marshmallow as m

from .bake import bake_schema
from .generics import extract_type
from .naming_case import NamingCase

_T = TypeVar("_T")
_MARSHMALLOW_VERSION_MAJOR = int(importlib.metadata.version("marshmallow").split(".")[0])


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class _SchemaKey:
    cls: type
    many: bool
    naming_case: NamingCase | None


_schemas: dict[_SchemaKey, m.Schema] = {}

if _MARSHMALLOW_VERSION_MAJOR >= 3:

    def schema_v3(cls: type, /, *, many: bool = False, naming_case: NamingCase | None = None) -> m.Schema:
        key = _SchemaKey(cls=cls, many=many, naming_case=naming_case)
        existent_schema = _schemas.get(key)
        if existent_schema is not None:
            return existent_schema
        new_schema = bake_schema(cls, naming_case=naming_case)(many=many)
        _schemas[key] = new_schema
        return new_schema

    schema = schema_v3

    def load_v3(cls: type[_T], data: dict[str, Any], /, *, naming_case: NamingCase | None = None) -> _T:
        return schema_v3(cls, naming_case=naming_case).load(data)  # type: ignore

    load = load_v3

    def load_many_v3(
        cls: type[_T], data: list[dict[str, Any]], /, *, naming_case: NamingCase | None = None
    ) -> list[_T]:
        return schema_v3(cls, many=True, naming_case=naming_case).load(data)  # type: ignore

    load_many = load_many_v3

    def dump_v3(cls: type | None, data: Any, /, *, naming_case: NamingCase | None = None) -> dict[str, Any]:
        data_schema = schema_v3(extract_type(data, cls), naming_case=naming_case)
        dumped: dict[str, Any] = data_schema.dump(data)  # type: ignore
        if errors := data_schema.validate(dumped):
            raise m.ValidationError(errors)
        return dumped

    dump_impl = dump_v3

    def dump_many_v3(
        cls: type | None, data: list[Any], /, *, naming_case: NamingCase | None = None
    ) -> list[dict[str, Any]]:
        if not data:
            return []
        data_schema = schema_v3(extract_type(data[0], cls), many=True, naming_case=naming_case)
        dumped: list[dict[str, Any]] = data_schema.dump(data)  # type: ignore
        if errors := data_schema.validate(dumped):
            raise m.ValidationError(errors)
        return dumped

    dump_many_impl = dump_many_v3

else:

    def schema_v2(cls: type, /, *, many: bool = False, naming_case: NamingCase | None = None) -> m.Schema:
        key = _SchemaKey(cls=cls, many=many, naming_case=naming_case)
        existent_schema = _schemas.get(key)
        if existent_schema is not None:
            return existent_schema
        new_schema = bake_schema(cls, naming_case=naming_case)(strict=True, many=many)  # type: ignore
        _schemas[key] = new_schema
        return new_schema

    schema = schema_v2

    def load_v2(cls: type[_T], data: dict[str, Any], /, *, naming_case: NamingCase | None = None) -> _T:
        loaded, _ = schema_v2(cls, naming_case=naming_case).load(data)  # type: ignore
        return loaded  # type: ignore[return-value]

    load = load_v2

    def load_many_v2(
        cls: type[_T], data: list[dict[str, Any]], /, *, naming_case: NamingCase | None = None
    ) -> list[_T]:
        loaded, _ = schema_v2(cls, many=True, naming_case=naming_case).load(data)  # type: ignore
        return loaded  # type: ignore[return-value]

    load_many = load_many_v2

    def dump_v2(cls: type | None, data: Any, /, *, naming_case: NamingCase | None = None) -> dict[str, Any]:
        data_schema = schema_v2(extract_type(data, cls), naming_case=naming_case)
        dumped, errors = data_schema.dump(data)
        if errors:
            raise m.ValidationError(errors)
        if errors := data_schema.validate(dumped):
            raise m.ValidationError(errors)
        return dumped  # type: ignore

    dump_impl = dump_v2

    def dump_many_v2(
        cls: type | None, data: list[Any], /, *, naming_case: NamingCase | None = None
    ) -> list[dict[str, Any]]:
        if not data:
            return []
        data_schema = schema_v2(extract_type(data[0], cls), many=True, naming_case=naming_case)
        dumped, errors = data_schema.dump(data)
        if errors:
            raise m.ValidationError(errors)
        if errors := data_schema.validate(dumped):
            raise m.ValidationError(errors)
        return dumped  # type: ignore

    dump_many_impl = dump_many_v2

EmptySchema = m.Schema


@overload
def dump(data: Any, /, *, naming_case: NamingCase | None = None) -> dict[str, Any]: ...


@overload
def dump(cls: type, data: Any, /, *, naming_case: NamingCase | None = None) -> dict[str, Any]: ...


def dump(*args: Any, **kwargs: Any) -> dict[str, Any]:
    if len(args) == 1:
        return dump_impl(None, *args, **kwargs)
    return dump_impl(*args, **kwargs)


@overload
def dump_many(data: list[Any], /, *, naming_case: NamingCase | None = None) -> list[dict[str, Any]]: ...


@overload
def dump_many(cls: type, data: list[Any], /, *, naming_case: NamingCase | None = None) -> list[dict[str, Any]]: ...


def dump_many(*args: Any, **kwargs: Any) -> list[dict[str, Any]]:
    if len(args) == 1:
        return dump_many_impl(None, *args, **kwargs)
    return dump_many_impl(*args, **kwargs)
