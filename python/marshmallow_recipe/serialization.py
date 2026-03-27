import importlib.metadata
from typing import Any, ClassVar, Protocol, get_args, overload

import marshmallow as m

from .bake import bake_schema
from .generics import extract_type, is_union_type, unwrap_type_alias
from .missing import MISSING
from .naming_case import NamingCase
from .options import NoneValueHandling
from .utils import validate_decimal_places

_MARSHMALLOW_VERSION_MAJOR = int(importlib.metadata.version("marshmallow").split(".")[0])


class Dataclass(Protocol):
    __dataclass_fields__: ClassVar[dict[str, Any]]


SchemaKey = tuple[type, bool, NamingCase | None, NoneValueHandling | None, int | None]


_schemas: dict[SchemaKey, m.Schema] = {}

if _MARSHMALLOW_VERSION_MAJOR >= 3:

    def schema_v3(
        cls: type,
        /,
        *,
        many: bool = False,
        naming_case: NamingCase | None = None,
        none_value_handling: NoneValueHandling | None = None,
        decimal_places: int | None = MISSING,
    ) -> m.Schema:
        validate_decimal_places(decimal_places)
        key: SchemaKey = (cls, many, naming_case, none_value_handling, decimal_places)
        existent_schema = _schemas.get(key)
        if existent_schema is not None:
            return existent_schema
        new_schema = bake_schema(
            cls, naming_case=naming_case, none_value_handling=none_value_handling, decimal_places=decimal_places
        )(many=many)
        _schemas[key] = new_schema
        return new_schema

    schema = schema_v3

    def load_v3[T](
        cls: type[T],
        data: dict[str, Any],
        /,
        *,
        naming_case: NamingCase | None = None,
        none_value_handling: NoneValueHandling | None = None,
        decimal_places: int | None = MISSING,
    ) -> T:
        validate_decimal_places(decimal_places)
        unwrapped = unwrap_type_alias(cls)
        if is_union_type(unwrapped):
            return _load_union_v3(
                unwrapped,
                data,
                naming_case=naming_case,
                none_value_handling=none_value_handling,
                decimal_places=decimal_places,
            )  # type: ignore
        schema = schema_v3(
            unwrapped, naming_case=naming_case, none_value_handling=none_value_handling, decimal_places=decimal_places
        )
        return schema.load(data)  # type: ignore

    def _load_union_v3(
        union_type: Any,
        data: dict[str, Any],
        *,
        naming_case: NamingCase | None,
        none_value_handling: NoneValueHandling | None,
        decimal_places: int | None,
    ) -> Any:
        members = [a for a in get_args(union_type) if a is not type(None)]
        last_error: Exception | None = None
        for member in members:
            try:
                return load_v3(
                    member,
                    data,
                    naming_case=naming_case,
                    none_value_handling=none_value_handling,
                    decimal_places=decimal_places,
                )
            except (m.ValidationError, ValueError) as e:
                last_error = e
        raise last_error  # type: ignore

    load = load_v3

    def load_many_v3[T](
        cls: type[T],
        data: list[dict[str, Any]],
        /,
        *,
        naming_case: NamingCase | None = None,
        none_value_handling: NoneValueHandling | None = None,
        decimal_places: int | None = MISSING,
    ) -> list[T]:
        validate_decimal_places(decimal_places)
        unwrapped = unwrap_type_alias(cls)
        if is_union_type(unwrapped):
            return [
                _load_union_v3(
                    unwrapped,
                    item,
                    naming_case=naming_case,
                    none_value_handling=none_value_handling,
                    decimal_places=decimal_places,
                )
                for item in data
            ]  # type: ignore
        schema = schema_v3(
            unwrapped,
            many=True,
            naming_case=naming_case,
            none_value_handling=none_value_handling,
            decimal_places=decimal_places,
        )
        return schema.load(data)  # type: ignore

    load_many = load_many_v3

    def dump_v3[T](
        cls: type[T] | None,
        data: T,
        /,
        *,
        naming_case: NamingCase | None = None,
        none_value_handling: NoneValueHandling | None = None,
        decimal_places: int | None = MISSING,
    ) -> dict[str, Any]:
        validate_decimal_places(decimal_places)
        data_schema = schema_v3(
            extract_type(data, cls),
            naming_case=naming_case,
            none_value_handling=none_value_handling,
            decimal_places=decimal_places,
        )
        dumped: dict[str, Any] = data_schema.dump(data)  # type: ignore
        if errors := data_schema.validate(dumped):
            raise m.ValidationError(errors)
        return dumped

    dump_impl = dump_v3

    def dump_many_v3[T](
        cls: type[T] | None,
        data: list[T],
        /,
        *,
        naming_case: NamingCase | None = None,
        none_value_handling: NoneValueHandling | None = None,
        decimal_places: int | None = MISSING,
    ) -> list[dict[str, Any]]:
        validate_decimal_places(decimal_places)
        if not data:
            return []
        unwrapped = unwrap_type_alias(cls) if cls is not None else None
        if unwrapped is not None and is_union_type(unwrapped):
            return [
                dump_v3(
                    None,
                    item,
                    naming_case=naming_case,
                    none_value_handling=none_value_handling,
                    decimal_places=decimal_places,
                )
                for item in data
            ]
        data_schema = schema_v3(
            extract_type(data[0], unwrapped),
            many=True,
            naming_case=naming_case,
            none_value_handling=none_value_handling,
            decimal_places=decimal_places,
        )
        dumped: list[dict[str, Any]] = data_schema.dump(data)  # type: ignore
        if errors := data_schema.validate(dumped):
            raise m.ValidationError(errors)
        return dumped

    dump_many_impl = dump_many_v3

else:

    def schema_v2[T](
        cls: type[T],
        /,
        *,
        many: bool = False,
        naming_case: NamingCase | None = None,
        none_value_handling: NoneValueHandling | None = None,
        decimal_places: int | None = MISSING,
    ) -> m.Schema:
        validate_decimal_places(decimal_places)
        key: SchemaKey = (cls, many, naming_case, none_value_handling, decimal_places)
        existent_schema = _schemas.get(key)
        if existent_schema is not None:
            return existent_schema
        new_schema_cls = bake_schema(
            cls, naming_case=naming_case, none_value_handling=none_value_handling, decimal_places=decimal_places
        )
        new_schema = new_schema_cls(strict=True, many=many)  # type: ignore
        _schemas[key] = new_schema
        return new_schema

    schema = schema_v2

    def load_v2[T](
        cls: type[T],
        data: dict[str, Any],
        /,
        *,
        naming_case: NamingCase | None = None,
        none_value_handling: NoneValueHandling | None = None,
        decimal_places: int | None = MISSING,
    ) -> T:
        validate_decimal_places(decimal_places)
        unwrapped = unwrap_type_alias(cls)
        if is_union_type(unwrapped):
            return _load_union_v2(
                unwrapped,
                data,
                naming_case=naming_case,
                none_value_handling=none_value_handling,
                decimal_places=decimal_places,
            )  # type: ignore
        schema = schema_v2(
            unwrapped, naming_case=naming_case, none_value_handling=none_value_handling, decimal_places=decimal_places
        )
        loaded, _ = schema.load(data)  # type: ignore
        return loaded  # type: ignore[return-value]

    def _load_union_v2(
        union_type: Any,
        data: dict[str, Any],
        *,
        naming_case: NamingCase | None,
        none_value_handling: NoneValueHandling | None,
        decimal_places: int | None,
    ) -> Any:
        members = [a for a in get_args(union_type) if a is not type(None)]
        last_error: Exception | None = None
        for member in members:
            try:
                return load_v2(
                    member,
                    data,
                    naming_case=naming_case,
                    none_value_handling=none_value_handling,
                    decimal_places=decimal_places,
                )
            except (m.ValidationError, ValueError) as e:
                last_error = e
        raise last_error  # type: ignore

    load = load_v2

    def load_many_v2[T](
        cls: type[T],
        data: list[dict[str, Any]],
        /,
        *,
        naming_case: NamingCase | None = None,
        none_value_handling: NoneValueHandling | None = None,
        decimal_places: int | None = MISSING,
    ) -> list[T]:
        validate_decimal_places(decimal_places)
        unwrapped = unwrap_type_alias(cls)
        if is_union_type(unwrapped):
            return [
                _load_union_v2(
                    unwrapped,
                    item,
                    naming_case=naming_case,
                    none_value_handling=none_value_handling,
                    decimal_places=decimal_places,
                )
                for item in data
            ]  # type: ignore
        schema = schema_v2(
            unwrapped,
            many=True,
            naming_case=naming_case,
            none_value_handling=none_value_handling,
            decimal_places=decimal_places,
        )
        loaded, _ = schema.load(data)  # type: ignore
        return loaded  # type: ignore[return-value]

    load_many = load_many_v2

    def dump_v2[T](
        cls: type[T] | None,
        data: Any,
        /,
        *,
        naming_case: NamingCase | None = None,
        none_value_handling: NoneValueHandling | None = None,
        decimal_places: int | None = MISSING,
    ) -> dict[str, Any]:
        validate_decimal_places(decimal_places)
        data_schema = schema_v2(
            extract_type(data, cls),
            naming_case=naming_case,
            none_value_handling=none_value_handling,
            decimal_places=decimal_places,
        )
        dumped, errors = data_schema.dump(data)
        if errors:
            raise m.ValidationError(errors)
        if errors := data_schema.validate(dumped):
            raise m.ValidationError(errors)
        return dumped  # type: ignore

    dump_impl = dump_v2

    def dump_many_v2[T](
        cls: type[T] | None,
        data: list[T],
        /,
        *,
        naming_case: NamingCase | None = None,
        none_value_handling: NoneValueHandling | None = None,
        decimal_places: int | None = MISSING,
    ) -> list[dict[str, Any]]:
        validate_decimal_places(decimal_places)
        if not data:
            return []
        unwrapped = unwrap_type_alias(cls) if cls is not None else None
        if unwrapped is not None and is_union_type(unwrapped):
            return [
                dump_v2(
                    None,
                    item,
                    naming_case=naming_case,
                    none_value_handling=none_value_handling,
                    decimal_places=decimal_places,
                )
                for item in data
            ]
        data_schema = schema_v2(
            extract_type(data[0], unwrapped),
            many=True,
            naming_case=naming_case,
            none_value_handling=none_value_handling,
            decimal_places=decimal_places,
        )
        dumped, errors = data_schema.dump(data)
        if errors:
            raise m.ValidationError(errors)
        if errors := data_schema.validate(dumped):
            raise m.ValidationError(errors)
        return dumped  # type: ignore

    dump_many_impl = dump_many_v2

EmptySchema = m.Schema


@overload
def dump(
    data: Any,
    /,
    *,
    naming_case: NamingCase | None = None,
    none_value_handling: NoneValueHandling | None = None,
    decimal_places: int | None = MISSING,
) -> dict[str, Any]: ...


@overload
def dump[T](
    cls: type[T],
    data: T,
    /,
    *,
    naming_case: NamingCase | None = None,
    none_value_handling: NoneValueHandling | None = None,
    decimal_places: int | None = MISSING,
) -> dict[str, Any]: ...


def dump(*args: Any, **kwargs: Any) -> dict[str, Any]:
    if len(args) == 1:
        return dump_impl(None, *args, **kwargs)
    return dump_impl(*args, **kwargs)


@overload
def dump_many[T](
    data: list[T],
    /,
    *,
    naming_case: NamingCase | None = None,
    none_value_handling: NoneValueHandling | None = None,
    decimal_places: int | None = MISSING,
) -> list[dict[str, Any]]: ...


@overload
def dump_many[T](
    cls: type[T],
    data: list[T],
    /,
    *,
    naming_case: NamingCase | None = None,
    none_value_handling: NoneValueHandling | None = None,
    decimal_places: int | None = MISSING,
) -> list[dict[str, Any]]: ...


def dump_many(*args: Any, **kwargs: Any) -> list[dict[str, Any]]:
    if len(args) == 1:
        return dump_many_impl(None, *args, **kwargs)
    return dump_many_impl(*args, **kwargs)
