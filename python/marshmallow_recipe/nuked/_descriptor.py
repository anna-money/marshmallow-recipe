from __future__ import annotations

import ctypes
import dataclasses
import datetime
import decimal
import enum
import types
import uuid
from collections.abc import Callable, Mapping, Sequence
from typing import Annotated, Any, ClassVar, NewType, Union, get_args, get_origin

from ..generics import get_fields_type_map
from ..metadata import Metadata
from ..missing import MISSING
from ..options import NoneValueHandling, try_get_options_for

_building_schemas: dict[tuple[type, Callable[[str], str] | None], SchemaDescriptor] = {}


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
    data_key: str | None
    field_type: str
    optional: bool
    slot_offset: int | None = None
    nested_schema: SchemaDescriptor | None = None
    item_schema: FieldDescriptor | None = None
    value_schema: FieldDescriptor | None = None
    strip_whitespaces: bool = False
    decimal_places: int | None = MISSING
    decimal_rounding: str | None = None
    datetime_format: str | None = None
    enum_cls: type | None = None
    enum_values: list[tuple[Any, Any]] | None = None
    enum_name: str | None = None
    enum_members_repr: str | None = None
    union_variants: list[FieldDescriptor] | None = None
    default_value: Any = dataclasses.MISSING
    default_factory: Callable[[], Any] | None = None
    field_init: bool = True
    validators: list[Callable] | None = None
    post_load: Callable | None = None
    required_error: str | None = None
    none_error: str | None = None
    invalid_error: str | None = None


@dataclasses.dataclass(slots=True, kw_only=True)
class SchemaDescriptor:
    cls: type
    fields: list[FieldDescriptor]
    can_use_direct_slots: bool = False
    has_post_init: bool = False
    none_value_handling: NoneValueHandling | None = None
    decimal_places: int | None = None


@dataclasses.dataclass(slots=True, kw_only=True)
class TypeDescriptor:
    type_kind: str
    primitive_type: str | None = None
    optional: bool = False
    inner_type: TypeDescriptor | None = None
    item_type: TypeDescriptor | None = None
    value_type: TypeDescriptor | None = None
    cls: type | None = None
    fields: list[FieldDescriptor] = dataclasses.field(default_factory=list)
    union_variants: list[TypeDescriptor] | None = None
    can_use_direct_slots: bool = False
    has_post_init: bool = False
    none_value_handling: NoneValueHandling | None = None
    decimal_places: int | None = None


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
        value_hint = args[1] if len(args) > 1 else Any
        value_descriptor = build_type_descriptor(value_hint, naming_case)
        return TypeDescriptor(type_kind="dict", value_type=value_descriptor)

    if origin is set:
        item_hint = args[0] if args else Any
        item_descriptor = build_type_descriptor(item_hint, naming_case)
        return TypeDescriptor(type_kind="set", item_type=item_descriptor)

    if origin is frozenset:
        item_hint = args[0] if args else Any
        item_descriptor = build_type_descriptor(item_hint, naming_case)
        return TypeDescriptor(type_kind="frozenset", item_type=item_descriptor)

    if origin is Sequence:
        item_hint = args[0] if args else Any
        item_descriptor = build_type_descriptor(item_hint, naming_case)
        return TypeDescriptor(type_kind="list", item_type=item_descriptor)

    if origin is Mapping:
        value_hint = args[1] if len(args) > 1 else Any
        value_descriptor = build_type_descriptor(value_hint, naming_case)
        return TypeDescriptor(type_kind="dict", value_type=value_descriptor)

    if origin is tuple:
        if len(args) == 2 and args[1] is ...:
            item_hint = args[0]
            item_descriptor = build_type_descriptor(item_hint, naming_case)
            return TypeDescriptor(type_kind="tuple", item_type=item_descriptor)
        raise NotImplementedError("Only homogeneous tuple[T, ...] is supported")

    if origin is None:
        if cls is Any:
            return TypeDescriptor(type_kind="primitive", primitive_type="any")
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
                none_value_handling=schema.none_value_handling,
                decimal_places=schema.decimal_places,
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
            none_value_handling=schema.none_value_handling,
            decimal_places=schema.decimal_places,
        )

    raise NotImplementedError(f"Unsupported generic type: {origin}[{args}]")


def build_schema_descriptor(cls: type, naming_case: Callable[[str], str] | None = None) -> SchemaDescriptor:
    origin: type = get_origin(cls) or cls  # type: ignore[assignment]

    if not dataclasses.is_dataclass(origin):
        raise TypeError(f"{origin} is not a dataclass")

    # Read options from @mr.options decorator
    options = try_get_options_for(origin)
    effective_naming_case = naming_case
    if effective_naming_case is None and options and options.naming_case:
        effective_naming_case = options.naming_case

    # Get class-level decimal_places and none_value_handling from options
    cls_decimal_places: int | None = None
    cls_none_value_handling: NoneValueHandling | None = None
    if options:
        if options.decimal_places is not MISSING and options.decimal_places is not None:
            cls_decimal_places = options.decimal_places
        if options.none_value_handling is not None:
            cls_none_value_handling = options.none_value_handling

    cache_key = (origin, effective_naming_case)
    if cache_key in _building_schemas:
        return _building_schemas[cache_key]

    type_hints = get_fields_type_map(cls)

    has_post_init = hasattr(origin, "__post_init__")
    dc_params = getattr(origin, "__dataclass_params__", None)
    dataclass_init_enabled = dc_params.init if dc_params else True
    has_slots = hasattr(origin, "__slots__")

    all_fields_have_init = True
    for field in dataclasses.fields(origin):
        if not field.init:
            all_fields_have_init = False

    can_use_direct_slots = has_slots and dataclass_init_enabled and not has_post_init and all_fields_have_init

    schema = SchemaDescriptor(
        cls=origin,
        fields=[],
        can_use_direct_slots=can_use_direct_slots,
        has_post_init=has_post_init,
        none_value_handling=cls_none_value_handling,
        decimal_places=cls_decimal_places,
    )
    _building_schemas[cache_key] = schema

    try:
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
                effective_naming_case,
                has_default,
                default_value=default_value,
                default_factory=default_factory,
                field_init=field.init,
                default_decimal_places=cls_decimal_places,
                nested_naming_case=naming_case,
            )
            schema.fields.append(field_descriptor)

        for field in schema.fields:
            if field.data_key is None:
                continue
            for other in schema.fields:
                if field is other:
                    continue
                if field.data_key == other.name:
                    raise ValueError(f"Invalid name={field.data_key} in metadata for field={field.name}")
    finally:
        del _building_schemas[cache_key]

    return schema


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
    default_decimal_places: int | None = None,
    nested_naming_case: Callable[[str], str] | None = None,
) -> FieldDescriptor:
    optional = has_default
    data_key = None
    strip_whitespaces = False
    decimal_places: int | None = None
    decimal_places_explicitly_set = False
    decimal_rounding: str | None = None
    datetime_format: str | None = None
    validators: list[Callable] | None = None
    post_load_callback: Callable | None = None
    required_error_msg: str | None = None
    none_error_msg: str | None = None
    invalid_error_msg: str | None = None

    if metadata:
        data_key = metadata.get("name")
        strip_whitespaces = metadata.get("strip_whitespaces", False)
        if "places" in metadata:
            decimal_places = metadata.get("places")
            decimal_places_explicitly_set = True
        decimal_rounding = metadata.get("rounding")
        datetime_format = metadata.get("format")
        post_load_callback = metadata.get("post_load")
        required_error_msg = metadata.get("required_error")
        none_error_msg = metadata.get("none_error")
        invalid_error_msg = metadata.get("invalid_error")
        validate = metadata.get("validate")
        if validate is not None:
            validators = list(validate) if isinstance(validate, list | tuple) else [validate]

    origin = get_origin(hint)
    args = get_args(hint)

    if origin is Annotated:
        hint = args[0]
        for arg in args[1:]:
            if isinstance(arg, Mapping):
                if "name" in arg:
                    data_key = arg["name"]
                if "strip_whitespaces" in arg:
                    strip_whitespaces = arg["strip_whitespaces"]
                if "places" in arg:
                    decimal_places = arg["places"]
                    decimal_places_explicitly_set = True
                if "rounding" in arg:
                    decimal_rounding = arg["rounding"]
                if "format" in arg:
                    datetime_format = arg["format"]
                if "validate" in arg:
                    validate = arg["validate"]
                    validators = list(validate) if isinstance(validate, list | tuple) else [validate]
        origin = get_origin(hint)
        args = get_args(hint)

    if origin is types.UnionType or origin is Union:
        non_none_args = [a for a in args if a is not type(None)]
        if Any in non_none_args:
            raise ValueError(
                "Any type cannot be used in Optional or Union (Any | None, Optional[Any], Union[Any, ...] are invalid)"
            )
        if len(non_none_args) == 1 and type(None) in args:
            optional = True
            hint = non_none_args[0]
            origin = get_origin(hint)
            args = get_args(hint)

    if data_key is None and naming_case is not None:
        data_key = naming_case(name)

    field_type, nested_info = _analyze_type(hint, origin, args, nested_naming_case, metadata)
    slot_offset = get_slot_offset(cls, name) if cls else None

    if field_type == "decimal":
        if decimal_places_explicitly_set:
            pass
        elif default_decimal_places is not None:
            decimal_places = default_decimal_places
        elif decimal_places is None:
            decimal_places = MISSING

    return FieldDescriptor(
        name=name,
        data_key=data_key,
        field_type=field_type,
        optional=optional,
        slot_offset=slot_offset,
        strip_whitespaces=strip_whitespaces,
        decimal_places=decimal_places,
        decimal_rounding=decimal_rounding,
        datetime_format=datetime_format,
        default_value=default_value,
        default_factory=default_factory,
        field_init=field_init,
        validators=validators,
        post_load=post_load_callback,
        required_error=required_error_msg,
        none_error=none_error_msg,
        invalid_error=invalid_error_msg,
        **nested_info,
    )


def _analyze_type(
    hint: Any,
    origin: Any,
    args: tuple[Any, ...],
    naming_case: Callable[[str], str] | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> tuple[str, dict[str, Any]]:
    if isinstance(hint, NewType):
        hint = hint.__supertype__
        origin = get_origin(hint)
        args = get_args(hint)

    if origin is None:
        if hint is Any:
            return "any", {}
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
            enum_name = hint.__name__
            enum_members_repr = "[" + ", ".join(f"{hint.__name__}.{m.name}" for m in hint) + "]"
            if issubclass(hint, str):
                enum_values = [(m.value, m) for m in hint]
                return "str_enum", {
                    "enum_cls": hint,
                    "enum_values": enum_values,
                    "enum_name": enum_name,
                    "enum_members_repr": enum_members_repr,
                }
            if issubclass(hint, int):
                enum_values = []
                for m in hint:
                    if not (-(2**63) <= m.value < 2**63):
                        raise NotImplementedError(f"IntEnum value {m.value} for {m} is outside i64 range [-2^63, 2^63)")
                    enum_values.append((m.value, m))
                return "int_enum", {
                    "enum_cls": hint,
                    "enum_values": enum_values,
                    "enum_name": enum_name,
                    "enum_members_repr": enum_members_repr,
                }
            raise NotImplementedError(f"Unsupported enum type: {hint} (must inherit from str or int)")
        if dataclasses.is_dataclass(hint):
            nested_schema = build_schema_descriptor(hint, naming_case)  # type: ignore[arg-type]
            return "nested", {"nested_schema": nested_schema}
        raise NotImplementedError(f"Unsupported type: {hint}")

    if origin is list:
        item_hint = args[0] if args else Any
        item_metadata = None
        if metadata and "validate_item" in metadata:
            item_metadata = Metadata({"validate": metadata["validate_item"]})
        item_descriptor = _build_field_descriptor(
            None, "", item_hint, item_metadata, naming_case, nested_naming_case=naming_case
        )
        return "list", {"item_schema": item_descriptor}

    if origin is dict:
        value_hint = args[1] if len(args) > 1 else Any
        value_descriptor = _build_field_descriptor(
            None, "value", value_hint, None, naming_case, nested_naming_case=naming_case
        )
        return "dict", {"value_schema": value_descriptor}

    if origin is set:
        item_hint = args[0] if args else Any
        item_metadata = None
        if metadata and "validate_item" in metadata:
            item_metadata = Metadata({"validate": metadata["validate_item"]})
        item_descriptor = _build_field_descriptor(
            None, "", item_hint, item_metadata, naming_case, nested_naming_case=naming_case
        )
        return "set", {"item_schema": item_descriptor}

    if origin is frozenset:
        item_hint = args[0] if args else Any
        item_metadata = None
        if metadata and "validate_item" in metadata:
            item_metadata = Metadata({"validate": metadata["validate_item"]})
        item_descriptor = _build_field_descriptor(
            None, "", item_hint, item_metadata, naming_case, nested_naming_case=naming_case
        )
        return "frozenset", {"item_schema": item_descriptor}

    if origin is Sequence:
        item_hint = args[0] if args else Any
        item_metadata = None
        if metadata and "validate_item" in metadata:
            item_metadata = Metadata({"validate": metadata["validate_item"]})
        item_descriptor = _build_field_descriptor(
            None, "", item_hint, item_metadata, naming_case, nested_naming_case=naming_case
        )
        return "list", {"item_schema": item_descriptor}

    if origin is Mapping:
        value_hint = args[1] if len(args) > 1 else Any
        value_descriptor = _build_field_descriptor(
            None, "value", value_hint, None, naming_case, nested_naming_case=naming_case
        )
        return "dict", {"value_schema": value_descriptor}

    if origin is tuple:
        if len(args) == 2 and args[1] is ...:
            item_hint = args[0]
            item_metadata = None
            if metadata and "validate_item" in metadata:
                item_metadata = Metadata({"validate": metadata["validate_item"]})
            item_descriptor = _build_field_descriptor(
                None, "", item_hint, item_metadata, naming_case, nested_naming_case=naming_case
            )
            return "tuple", {"item_schema": item_descriptor}
        raise NotImplementedError("Only homogeneous tuple[T, ...] is supported")

    if origin is types.UnionType or origin is Union:
        non_none_args = [a for a in args if a is not type(None)]
        if len(non_none_args) > 1:
            variants = [
                _build_field_descriptor(None, "variant", a, None, naming_case, nested_naming_case=naming_case)
                for a in non_none_args
            ]
            return "union", {"union_variants": variants}

    if dataclasses.is_dataclass(origin):
        nested_schema = build_schema_descriptor(hint, naming_case)
        return "nested", {"nested_schema": nested_schema}

    raise NotImplementedError(f"Unsupported generic type: {origin}[{args}]")
