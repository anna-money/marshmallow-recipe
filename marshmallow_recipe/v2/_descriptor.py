from __future__ import annotations

import dataclasses
import datetime
import decimal
import types
import uuid
from collections.abc import Callable, Mapping
from typing import Annotated, Any, Union, get_args, get_origin, get_type_hints


@dataclasses.dataclass(slots=True, kw_only=True)
class FieldDescriptor:
    name: str
    serialized_name: str | None
    field_type: str
    optional: bool
    nested_schema: SchemaDescriptor | None = None
    item_schema: FieldDescriptor | None = None
    key_type: str | None = None
    value_schema: FieldDescriptor | None = None
    strip_whitespaces: bool = False
    decimal_places: int | None = None
    decimal_as_string: bool = True
    datetime_format: str | None = None


@dataclasses.dataclass(slots=True, kw_only=True)
class SchemaDescriptor:
    cls: type
    fields: list[FieldDescriptor]


@dataclasses.dataclass(slots=True, kw_only=True)
class TypeDescriptor:
    type_kind: str
    primitive_type: str | None = None
    optional: bool = False
    inner_type: TypeDescriptor | None = None
    item_type: TypeDescriptor | None = None
    key_type: str | None = None
    value_type: TypeDescriptor | None = None
    cls: type | None = None
    fields: list[FieldDescriptor] = dataclasses.field(default_factory=list)


def build_type_descriptor(cls: Any, naming_case: Callable[[str], str] | None = None) -> TypeDescriptor:
    origin = get_origin(cls)
    args = get_args(cls)

    if origin is types.UnionType or origin is Union:
        non_none_args = [a for a in args if a is not type(None)]
        if len(non_none_args) == 1 and type(None) in args:
            inner_descriptor = build_type_descriptor(non_none_args[0], naming_case)
            return TypeDescriptor(type_kind="optional", optional=True, inner_type=inner_descriptor)

    if origin is list:
        item_hint = args[0] if args else Any
        item_descriptor = build_type_descriptor(item_hint, naming_case)
        return TypeDescriptor(type_kind="list", item_type=item_descriptor)

    if origin is dict:
        key_hint = args[0] if args else str
        value_hint = args[1] if len(args) > 1 else Any
        key_type_str = _get_primitive_type_name(key_hint)
        value_descriptor = build_type_descriptor(value_hint, naming_case)
        return TypeDescriptor(type_kind="dict", key_type=key_type_str, value_type=value_descriptor)

    if origin is None:
        if cls is str:
            return TypeDescriptor(type_kind="primitive", primitive_type="str")
        if cls is int:
            return TypeDescriptor(type_kind="primitive", primitive_type="int")
        if cls is float:
            return TypeDescriptor(type_kind="primitive", primitive_type="float")
        if cls is bool:
            return TypeDescriptor(type_kind="primitive", primitive_type="bool")
        if cls is decimal.Decimal:
            return TypeDescriptor(type_kind="primitive", primitive_type="decimal")
        if cls is uuid.UUID:
            return TypeDescriptor(type_kind="primitive", primitive_type="uuid")
        if cls is datetime.datetime:
            return TypeDescriptor(type_kind="primitive", primitive_type="datetime")
        if cls is datetime.date:
            return TypeDescriptor(type_kind="primitive", primitive_type="date")
        if cls is datetime.time:
            return TypeDescriptor(type_kind="primitive", primitive_type="time")

        if dataclasses.is_dataclass(cls):
            schema = build_schema_descriptor(cls, naming_case)  # type: ignore[arg-type]
            return TypeDescriptor(type_kind="dataclass", cls=schema.cls, fields=schema.fields)

        raise NotImplementedError(f"Unsupported type: {cls}")

    raise NotImplementedError(f"Unsupported generic type: {origin}[{args}]")


def _get_primitive_type_name(hint: type) -> str:
    if hint is str:
        return "str"
    if hint is int:
        return "int"
    if hint is float:
        return "float"
    if hint is bool:
        return "bool"
    raise NotImplementedError(f"Unsupported key type: {hint}")


def build_schema_descriptor(cls: type, naming_case: Callable[[str], str] | None = None) -> SchemaDescriptor:
    if not dataclasses.is_dataclass(cls):
        raise TypeError(f"{cls} is not a dataclass")

    type_hints = get_type_hints(cls, include_extras=True)
    fields: list[FieldDescriptor] = []

    for field in dataclasses.fields(cls):
        hint = type_hints[field.name]
        field_descriptor = _build_field_descriptor(field.name, hint, field.metadata, naming_case)
        fields.append(field_descriptor)

    return SchemaDescriptor(cls=cls, fields=fields)


def _build_field_descriptor(
    name: str, hint: Any, metadata: Mapping[str, Any] | None = None, naming_case: Callable[[str], str] | None = None
) -> FieldDescriptor:
    optional = False
    serialized_name = None
    strip_whitespaces = False
    decimal_places: int | None = None
    decimal_as_string = True
    datetime_format: str | None = None

    if metadata:
        serialized_name = metadata.get("name")
        strip_whitespaces = metadata.get("strip_whitespaces", False)
        decimal_places = metadata.get("places")
        decimal_as_string = metadata.get("as_string", True)
        datetime_format = metadata.get("format")

    origin = get_origin(hint)
    args = get_args(hint)

    if origin is Annotated:
        hint = args[0]
        for arg in args[1:]:
            if isinstance(arg, dict):
                if "name" in arg:
                    serialized_name = arg["name"]
                if "strip_whitespaces" in arg:
                    strip_whitespaces = arg["strip_whitespaces"]
                if "places" in arg:
                    decimal_places = arg["places"]
                if "as_string" in arg:
                    decimal_as_string = arg["as_string"]
                if "format" in arg:
                    datetime_format = arg["format"]
        origin = get_origin(hint)
        args = get_args(hint)

    if origin is types.UnionType or origin is Union:
        non_none_args = [a for a in args if a is not type(None)]
        if len(non_none_args) == 1 and type(None) in args:
            optional = True
            hint = non_none_args[0]
            origin = get_origin(hint)
            args = get_args(hint)

    if serialized_name is None and naming_case is not None:
        serialized_name = naming_case(name)

    field_type, nested_info = _analyze_type(hint, origin, args, naming_case)

    return FieldDescriptor(
        name=name,
        serialized_name=serialized_name,
        field_type=field_type,
        optional=optional,
        strip_whitespaces=strip_whitespaces,
        decimal_places=decimal_places,
        decimal_as_string=decimal_as_string,
        datetime_format=datetime_format,
        **nested_info,
    )


def _analyze_type(
    hint: Any, origin: Any, args: tuple[Any, ...], naming_case: Callable[[str], str] | None = None
) -> tuple[str, dict[str, Any]]:
    if origin is None:
        if hint is str:
            return "str", {}
        if hint is int:
            return "int", {}
        if hint is float:
            return "float", {}
        if hint is bool:
            return "bool", {}
        if hint is decimal.Decimal:
            return "decimal", {}
        if hint is uuid.UUID:
            return "uuid", {}
        if hint is datetime.datetime:
            return "datetime", {}
        if hint is datetime.date:
            return "date", {}
        if hint is datetime.time:
            return "time", {}
        if dataclasses.is_dataclass(hint):
            nested_schema = build_schema_descriptor(hint, naming_case)  # type: ignore[arg-type]
            return "nested", {"nested_schema": nested_schema}
        raise NotImplementedError(f"Unsupported type: {hint}")

    if origin is list:
        item_hint = args[0] if args else Any
        item_descriptor = _build_field_descriptor("item", item_hint, None, naming_case)
        return "list", {"item_schema": item_descriptor}

    if origin is dict:
        key_hint = args[0] if args else str
        value_hint = args[1] if len(args) > 1 else Any
        key_type, _ = _analyze_type(key_hint, None, (), naming_case)
        value_descriptor = _build_field_descriptor("value", value_hint, None, naming_case)
        return "dict", {"key_type": key_type, "value_schema": value_descriptor}

    raise NotImplementedError(f"Unsupported generic type: {origin}[{args}]")
