from __future__ import annotations

import ctypes
import dataclasses
import datetime
import decimal
import enum
import types
import uuid
from collections.abc import Callable, Mapping
from typing import Annotated, Any, ClassVar, Union, get_args, get_origin

from marshmallow_recipe.generics import get_fields_type_map


class _PyMemberDef(ctypes.Structure):
    _fields_: ClassVar[list[tuple[str, type]]] = [  # type: ignore[assignment]
        ("name", ctypes.c_void_p),
        ("type", ctypes.c_int),
        ("offset", ctypes.c_ssize_t),
    ]


class _PyMemberDescrObject(ctypes.Structure):
    _fields_: ClassVar[list[tuple[str, type]]] = [  # type: ignore[assignment]
        ("ob_refcnt", ctypes.c_ssize_t),
        ("ob_type", ctypes.c_void_p),
        ("d_type", ctypes.c_void_p),
        ("d_name", ctypes.c_void_p),
        ("d_qualname", ctypes.c_void_p),
        ("d_member", ctypes.POINTER(_PyMemberDef)),
    ]


def get_slot_offset(cls: type, field_name: str) -> int | None:
    if not hasattr(cls, "__slots__"):
        return None
    descriptor = getattr(cls, field_name, None)
    if descriptor is None:
        return None
    try:
        ptr = ctypes.cast(id(descriptor), ctypes.POINTER(_PyMemberDescrObject))
        return ptr.contents.d_member.contents.offset
    except Exception:
        return None


@dataclasses.dataclass(slots=True, kw_only=True)
class FieldDescriptor:
    name: str
    serialized_name: str | None
    field_type: str
    optional: bool
    slot_offset: int | None = None
    nested_schema: SchemaDescriptor | None = None
    item_schema: FieldDescriptor | None = None
    key_type: str | None = None
    value_schema: FieldDescriptor | None = None
    strip_whitespaces: bool = False
    decimal_places: int | None = None
    decimal_as_string: bool = True
    datetime_format: str | None = None
    enum_cls: type | None = None
    union_variants: list[FieldDescriptor] | None = None
    default_value: Any = dataclasses.MISSING
    default_factory: Callable[[], Any] | None = None
    field_init: bool = True
    validators: list[Callable] | None = None
    post_load: Callable | None = None


@dataclasses.dataclass(slots=True, kw_only=True)
class SchemaDescriptor:
    cls: type
    fields: list[FieldDescriptor]
    can_use_direct_slots: bool = False
    has_post_init: bool = False


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
    union_variants: list[TypeDescriptor] | None = None
    can_use_direct_slots: bool = False
    has_post_init: bool = False


def build_type_descriptor(cls: Any, naming_case: Callable[[str], str] | None = None) -> TypeDescriptor:
    origin = get_origin(cls)
    args = get_args(cls)

    if origin is types.UnionType or origin is Union:
        non_none_args = [a for a in args if a is not type(None)]
        if len(non_none_args) == 1 and type(None) in args:
            inner_descriptor = build_type_descriptor(non_none_args[0], naming_case)
            return TypeDescriptor(type_kind="optional", optional=True, inner_type=inner_descriptor)
        if len(non_none_args) > 1:
            variants = [build_type_descriptor(a, naming_case) for a in non_none_args]
            is_optional = type(None) in args
            return TypeDescriptor(type_kind="union", optional=is_optional, union_variants=variants)

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

    if origin is set:
        item_hint = args[0] if args else Any
        item_descriptor = build_type_descriptor(item_hint, naming_case)
        return TypeDescriptor(type_kind="set", item_type=item_descriptor)

    if origin is frozenset:
        item_hint = args[0] if args else Any
        item_descriptor = build_type_descriptor(item_hint, naming_case)
        return TypeDescriptor(type_kind="frozenset", item_type=item_descriptor)

    if origin is tuple:
        if len(args) == 2 and args[1] is ...:
            item_hint = args[0]
            item_descriptor = build_type_descriptor(item_hint, naming_case)
            return TypeDescriptor(type_kind="tuple", item_type=item_descriptor)
        raise NotImplementedError("Only homogeneous tuple[T, ...] is supported")

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
            return TypeDescriptor(
                type_kind="dataclass",
                cls=schema.cls,
                fields=schema.fields,
                can_use_direct_slots=schema.can_use_direct_slots,
                has_post_init=schema.has_post_init,
            )

        raise NotImplementedError(f"Unsupported type: {cls}")

    if dataclasses.is_dataclass(origin):
        schema = build_schema_descriptor(cls, naming_case)
        return TypeDescriptor(
            type_kind="dataclass",
            cls=origin,  # type: ignore[arg-type]
            fields=schema.fields,
            can_use_direct_slots=schema.can_use_direct_slots,
            has_post_init=schema.has_post_init,
        )

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
    origin: type = get_origin(cls) or cls  # type: ignore[assignment]

    if not dataclasses.is_dataclass(origin):
        raise TypeError(f"{origin} is not a dataclass")

    type_hints = get_fields_type_map(cls)
    fields: list[FieldDescriptor] = []

    has_post_init = hasattr(origin, "__post_init__")
    dc_params = getattr(origin, "__dataclass_params__", None)
    dataclass_init_enabled = dc_params.init if dc_params else True
    has_slots = hasattr(origin, "__slots__")

    all_fields_have_init = True
    for field in dataclasses.fields(origin):
        if not field.init:
            all_fields_have_init = False

    can_use_direct_slots = has_slots and dataclass_init_enabled and not has_post_init and all_fields_have_init

    for field in dataclasses.fields(origin):
        hint = type_hints[field.name]
        has_default = field.default is not dataclasses.MISSING or field.default_factory is not dataclasses.MISSING
        default_value = field.default if field.default is not dataclasses.MISSING else dataclasses.MISSING
        default_factory = field.default_factory if field.default_factory is not dataclasses.MISSING else None
        field_descriptor = _build_field_descriptor(
            origin,
            field.name,
            hint,
            field.metadata,
            naming_case,
            has_default,
            default_value=default_value,
            default_factory=default_factory,
            field_init=field.init,
        )
        fields.append(field_descriptor)

    return SchemaDescriptor(
        cls=origin, fields=fields, can_use_direct_slots=can_use_direct_slots, has_post_init=has_post_init
    )


def _build_field_descriptor(
    cls: type | None,
    name: str,
    hint: Any,
    metadata: Mapping[str, Any] | None = None,
    naming_case: Callable[[str], str] | None = None,
    has_default: bool = False,
    default_value: Any = dataclasses.MISSING,
    default_factory: Callable[[], Any] | None = None,
    field_init: bool = True,
) -> FieldDescriptor:
    optional = has_default
    serialized_name = None
    strip_whitespaces = False
    decimal_places: int | None = None
    decimal_as_string = True
    datetime_format: str | None = None
    validators: list[Callable] | None = None
    post_load_callback: Callable | None = None

    if metadata:
        serialized_name = metadata.get("name")
        strip_whitespaces = metadata.get("strip_whitespaces", False)
        decimal_places = metadata.get("places")
        decimal_as_string = metadata.get("as_string", True)
        datetime_format = metadata.get("format")
        post_load_callback = metadata.get("post_load")
        validate = metadata.get("validate")
        if validate is not None:
            validators = list(validate) if isinstance(validate, list | tuple) else [validate]

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

    field_type, nested_info = _analyze_type(hint, origin, args, naming_case, metadata)
    slot_offset = get_slot_offset(cls, name) if cls else None

    if field_type == "decimal" and decimal_places is None:
        decimal_places = 2

    return FieldDescriptor(
        name=name,
        serialized_name=serialized_name,
        field_type=field_type,
        optional=optional,
        slot_offset=slot_offset,
        strip_whitespaces=strip_whitespaces,
        decimal_places=decimal_places,
        decimal_as_string=decimal_as_string,
        datetime_format=datetime_format,
        default_value=default_value,
        default_factory=default_factory,
        field_init=field_init,
        validators=validators,
        post_load=post_load_callback,
        **nested_info,
    )


def _analyze_type(
    hint: Any,
    origin: Any,
    args: tuple[Any, ...],
    naming_case: Callable[[str], str] | None = None,
    metadata: Mapping[str, Any] | None = None,
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
        if isinstance(hint, type) and issubclass(hint, enum.Enum):
            if issubclass(hint, str):
                return "str_enum", {"enum_cls": hint}
            if issubclass(hint, int):
                return "int_enum", {"enum_cls": hint}
            raise NotImplementedError(f"Unsupported enum type: {hint} (must inherit from str or int)")
        if dataclasses.is_dataclass(hint):
            nested_schema = build_schema_descriptor(hint, naming_case)  # type: ignore[arg-type]
            return "nested", {"nested_schema": nested_schema}
        raise NotImplementedError(f"Unsupported type: {hint}")

    if origin is list:
        item_hint = args[0] if args else Any
        item_metadata = None
        if metadata and "validate_item" in metadata:
            from marshmallow_recipe.metadata import Metadata

            item_metadata = Metadata({"validate": metadata["validate_item"]})
        item_descriptor = _build_field_descriptor(None, "item", item_hint, item_metadata, naming_case)
        return "list", {"item_schema": item_descriptor}

    if origin is dict:
        key_hint = args[0] if args else str
        value_hint = args[1] if len(args) > 1 else Any
        key_type, _ = _analyze_type(key_hint, None, (), naming_case, None)
        value_descriptor = _build_field_descriptor(None, "value", value_hint, None, naming_case)
        return "dict", {"key_type": key_type, "value_schema": value_descriptor}

    if origin is set:
        item_hint = args[0] if args else Any
        item_metadata = None
        if metadata and "validate_item" in metadata:
            from marshmallow_recipe.metadata import Metadata

            item_metadata = Metadata({"validate": metadata["validate_item"]})
        item_descriptor = _build_field_descriptor(None, "item", item_hint, item_metadata, naming_case)
        return "set", {"item_schema": item_descriptor}

    if origin is frozenset:
        item_hint = args[0] if args else Any
        item_metadata = None
        if metadata and "validate_item" in metadata:
            from marshmallow_recipe.metadata import Metadata

            item_metadata = Metadata({"validate": metadata["validate_item"]})
        item_descriptor = _build_field_descriptor(None, "item", item_hint, item_metadata, naming_case)
        return "frozenset", {"item_schema": item_descriptor}

    if origin is tuple:
        if len(args) == 2 and args[1] is ...:
            item_hint = args[0]
            item_metadata = None
            if metadata and "validate_item" in metadata:
                from marshmallow_recipe.metadata import Metadata

                item_metadata = Metadata({"validate": metadata["validate_item"]})
            item_descriptor = _build_field_descriptor(None, "item", item_hint, item_metadata, naming_case)
            return "tuple", {"item_schema": item_descriptor}
        raise NotImplementedError("Only homogeneous tuple[T, ...] is supported")

    if origin is types.UnionType or origin is Union:
        non_none_args = [a for a in args if a is not type(None)]
        if len(non_none_args) > 1:
            variants = [_build_field_descriptor(None, "variant", a, None, naming_case) for a in non_none_args]
            return "union", {"union_variants": variants}

    if dataclasses.is_dataclass(origin):
        nested_schema = build_schema_descriptor(hint, naming_case)
        return "nested", {"nested_schema": nested_schema}

    raise NotImplementedError(f"Unsupported generic type: {origin}[{args}]")
