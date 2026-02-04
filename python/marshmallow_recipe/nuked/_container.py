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

from .. import _nuked as nuked  # type: ignore[attr-defined]
from ..generics import get_fields_type_map
from ..missing import MISSING
from ..options import NoneValueHandling, try_get_options_for
from ._validator import build_combined_validator


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
class _DataclassInfo:
    cls: type
    can_use_direct_slots: bool
    has_post_init: bool
    none_value_handling: NoneValueHandling | None
    decimal_places: int | None


def build_container(
    cls: Any,
    naming_case: Callable[[str], str] | None,
    none_value_handling: NoneValueHandling,
    decimal_places: int | None,
) -> Any:
    builder = nuked.ContainerBuilder(none_value_handling=none_value_handling.value, decimal_places=decimal_places)
    type_handle = _build_root_type(builder, cls, naming_case, set())
    return builder.build(type_handle)


def get_dataclass_info(cls: Any, naming_case: Callable[[str], str] | None) -> _DataclassInfo | None:
    inner_dataclass = _find_inner_dataclass(cls)
    if inner_dataclass is None:
        return None
    return _analyze_dataclass(inner_dataclass, naming_case)


def _find_inner_dataclass(cls: Any) -> type | None:
    origin = get_origin(cls)
    args = get_args(cls)

    if origin is None:
        if dataclasses.is_dataclass(cls) and isinstance(cls, type):
            return cls
        return None

    if origin in (list, set, frozenset, Sequence) and args:
        return _find_inner_dataclass(args[0])

    if origin in (dict, Mapping) and len(args) > 1:
        return _find_inner_dataclass(args[1])

    if origin is tuple and len(args) == 2 and args[1] is ...:
        return _find_inner_dataclass(args[0])

    if origin is types.UnionType or origin is Union:
        non_none_args = [a for a in args if a is not type(None)]
        if len(non_none_args) == 1:
            return _find_inner_dataclass(non_none_args[0])
        for arg in non_none_args:
            result = _find_inner_dataclass(arg)
            if result is not None:
                return result
        return None

    if dataclasses.is_dataclass(origin):
        return origin  # type: ignore[return-value]

    return None


def _build_root_type(builder: Any, cls: Any, naming_case: Callable[[str], str] | None, visited: set[type]) -> Any:
    origin = get_origin(cls)
    args = get_args(cls)

    if origin is None:
        if dataclasses.is_dataclass(cls):
            info = _analyze_dataclass(cls, naming_case)
            return _build_dataclass_type(builder, cls, naming_case, info, visited)
        raise TypeError(f"Unsupported root type: {cls}")

    if origin is list or origin is Sequence:
        item_type = args[0] if args else Any
        item_handle = _build_root_type(builder, item_type, naming_case, visited)
        return builder.type_list(item_handle)

    if origin is dict or origin is Mapping:
        value_type = args[1] if len(args) > 1 else Any
        value_handle = _build_root_type(builder, value_type, naming_case, visited)
        return builder.type_dict(value_handle)

    if origin is set:
        item_type = args[0] if args else Any
        item_handle = _build_root_type(builder, item_type, naming_case, visited)
        return builder.type_set(item_handle)

    if origin is frozenset:
        item_type = args[0] if args else Any
        item_handle = _build_root_type(builder, item_type, naming_case, visited)
        return builder.type_frozenset(item_handle)

    if origin is tuple:
        if len(args) == 2 and args[1] is ...:
            item_type = args[0]
            item_handle = _build_root_type(builder, item_type, naming_case, visited)
            return builder.type_tuple(item_handle)
        raise NotImplementedError("Only homogeneous tuple[T, ...] is supported at root level")

    if origin is types.UnionType or origin is Union:
        non_none_args = [a for a in args if a is not type(None)]
        if len(non_none_args) == 1 and type(None) in args:
            inner_handle = _build_root_type(builder, non_none_args[0], naming_case, visited)
            return builder.type_optional(inner_handle)
        if len(non_none_args) > 1:
            variant_handles = [_build_root_type(builder, a, naming_case, visited) for a in non_none_args]
            return builder.type_union(variant_handles)

    if dataclasses.is_dataclass(origin):
        info = _analyze_dataclass(origin, naming_case)
        return _build_dataclass_type(builder, cls, naming_case, info, visited)

    raise TypeError(f"Unsupported root type: {cls}")


def _analyze_dataclass(cls: Any, naming_case: Callable[[str], str] | None) -> _DataclassInfo:
    origin: type = get_origin(cls) or cls  # type: ignore[assignment]

    if not dataclasses.is_dataclass(origin):
        raise TypeError(f"{origin} is not a dataclass")

    options = try_get_options_for(origin)

    cls_decimal_places: int | None = None
    cls_none_value_handling: NoneValueHandling | None = None
    if options:
        if options.decimal_places is not MISSING and options.decimal_places is not None:
            cls_decimal_places = options.decimal_places
        if options.none_value_handling is not None:
            cls_none_value_handling = options.none_value_handling

    has_post_init = hasattr(origin, "__post_init__")
    dc_params = getattr(origin, "__dataclass_params__", None)
    dataclass_init_enabled = dc_params.init if dc_params else True
    has_slots = hasattr(origin, "__slots__")

    all_fields_have_init = all(field.init for field in dataclasses.fields(origin))
    can_use_direct_slots = has_slots and dataclass_init_enabled and not has_post_init and all_fields_have_init

    return _DataclassInfo(
        cls=origin,
        can_use_direct_slots=can_use_direct_slots,
        has_post_init=has_post_init,
        none_value_handling=cls_none_value_handling,
        decimal_places=cls_decimal_places,
    )


def _build_dataclass_type(
    builder: Any, cls: Any, naming_case: Callable[[str], str] | None, info: _DataclassInfo, visited: set[type]
) -> Any:
    origin: type = get_origin(cls) or cls  # type: ignore[assignment]

    if origin in visited:
        raise NotImplementedError(
            f"Cyclic dataclass references are not supported in nuked: {origin.__name__} references itself"
        )
    visited = visited | {origin}

    options = try_get_options_for(origin)
    effective_naming_case = naming_case
    if effective_naming_case is None and options and options.naming_case:
        effective_naming_case = options.naming_case

    type_hints = get_fields_type_map(cls)

    field_handles = []
    field_data_keys: list[tuple[str, str | None]] = []

    for field in dataclasses.fields(origin):
        hint = type_hints[field.name]
        has_default = field.default is not dataclasses.MISSING or field.default_factory is not dataclasses.MISSING
        default_value = field.default if field.default is not dataclasses.MISSING else dataclasses.MISSING
        default_factory = field.default_factory if field.default_factory is not dataclasses.MISSING else None

        field_handle, data_key = _build_field(
            builder,
            origin,
            field.name,
            hint,
            field.metadata,
            effective_naming_case,
            has_default,
            default_value=default_value,
            default_factory=default_factory,
            field_init=field.init,
            default_decimal_places=info.decimal_places,
            nested_naming_case=naming_case,
            visited=visited,
        )
        field_handles.append(field_handle)
        field_data_keys.append((field.name, data_key))

    for name, data_key in field_data_keys:
        if data_key is None:
            continue
        for other_name, _ in field_data_keys:
            if name != other_name and data_key == other_name:
                raise ValueError(f"Invalid name={data_key} in metadata for field={name}")

    dc = builder.dataclass(
        origin, field_handles, can_use_direct_slots=info.can_use_direct_slots, has_post_init=info.has_post_init
    )
    return builder.type_dataclass(dc)


def _build_field(
    builder: Any,
    cls: type | None,
    name: str,
    hint: Any,
    metadata: Mapping[str, Any] | None,
    naming_case: Callable[[str], str] | None,
    has_default: bool,
    default_value: Any = dataclasses.MISSING,
    default_factory: Callable[[], Any] | None = None,
    field_init: bool = True,
    default_decimal_places: int | None = None,
    nested_naming_case: Callable[[str], str] | None = None,
    visited: set[type] | None = None,
) -> tuple[Any, str | None]:
    if visited is None:
        visited = set()

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
    item_validators: list[Callable] | None = None

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
        validate_item = metadata.get("validate_item")
        if validate_item is not None:
            item_validators = list(validate_item) if isinstance(validate_item, list | tuple) else [validate_item]

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

    slot_offset = get_slot_offset(cls, name) if cls else None

    kwargs: dict[str, Any] = {}
    if data_key is not None:
        kwargs["data_key"] = data_key
    if slot_offset is not None:
        kwargs["slot_offset"] = slot_offset
    if default_value is not dataclasses.MISSING:
        kwargs["default_value"] = default_value
    if default_factory is not None:
        kwargs["default_factory"] = default_factory
    if required_error_msg is not None:
        kwargs["required_error"] = required_error_msg
    if none_error_msg is not None:
        kwargs["none_error"] = none_error_msg
    if invalid_error_msg is not None:
        kwargs["invalid_error"] = invalid_error_msg
    if not field_init:
        kwargs["field_init"] = False
    if post_load_callback is not None:
        kwargs["post_load"] = post_load_callback
    if validators:
        kwargs["validator"] = build_combined_validator(validators)

    field_handle = _build_field_by_type(
        builder,
        name,
        hint,
        origin,
        args,
        optional,
        strip_whitespaces,
        decimal_places,
        decimal_places_explicitly_set,
        decimal_rounding,
        datetime_format,
        default_decimal_places,
        nested_naming_case,
        visited,
        item_validators,
        kwargs,
    )

    return field_handle, data_key


def _build_field_by_type(
    builder: Any,
    name: str,
    hint: Any,
    origin: Any,
    args: tuple[Any, ...],
    optional: bool,
    strip_whitespaces: bool,
    decimal_places: int | None,
    decimal_places_explicitly_set: bool,
    decimal_rounding: str | None,
    datetime_format: str | None,
    default_decimal_places: int | None,
    nested_naming_case: Callable[[str], str] | None,
    visited: set[type],
    item_validators: list[Callable] | None,
    kwargs: dict[str, Any],
) -> Any:
    if isinstance(hint, NewType):
        hint = hint.__supertype__
        origin = get_origin(hint)
        args = get_args(hint)

    if origin is None:
        return _build_primitive_field(
            builder,
            name,
            hint,
            optional,
            strip_whitespaces,
            decimal_places,
            decimal_places_explicitly_set,
            decimal_rounding,
            datetime_format,
            default_decimal_places,
            nested_naming_case,
            visited,
            kwargs,
        )

    if origin is list:
        item_hint = args[0] if args else Any
        item_handle = _build_item_field(builder, item_hint, nested_naming_case, visited)
        if item_validators:
            kwargs["item_validator"] = build_combined_validator(item_validators)
        return builder.list_field(name, optional, item_handle, **kwargs)

    if origin is dict:
        value_hint = args[1] if len(args) > 1 else Any
        value_handle = _build_value_field(builder, value_hint, nested_naming_case, visited)
        return builder.dict_field(name, optional, value_handle, **kwargs)

    if origin is set:
        item_hint = args[0] if args else Any
        item_handle = _build_item_field(builder, item_hint, nested_naming_case, visited)
        if item_validators:
            kwargs["item_validator"] = build_combined_validator(item_validators)
        return builder.set_field(name, optional, item_handle, **kwargs)

    if origin is frozenset:
        item_hint = args[0] if args else Any
        item_handle = _build_item_field(builder, item_hint, nested_naming_case, visited)
        if item_validators:
            kwargs["item_validator"] = build_combined_validator(item_validators)
        return builder.frozenset_field(name, optional, item_handle, **kwargs)

    if origin is Sequence:
        item_hint = args[0] if args else Any
        item_handle = _build_item_field(builder, item_hint, nested_naming_case, visited)
        if item_validators:
            kwargs["item_validator"] = build_combined_validator(item_validators)
        return builder.list_field(name, optional, item_handle, **kwargs)

    if origin is Mapping:
        value_hint = args[1] if len(args) > 1 else Any
        value_handle = _build_value_field(builder, value_hint, nested_naming_case, visited)
        return builder.dict_field(name, optional, value_handle, **kwargs)

    if origin is tuple:
        if len(args) == 2 and args[1] is ...:
            item_hint = args[0]
            item_handle = _build_item_field(builder, item_hint, nested_naming_case, visited)
            if item_validators:
                kwargs["item_validator"] = build_combined_validator(item_validators)
            return builder.tuple_field(name, optional, item_handle, **kwargs)
        raise NotImplementedError("Only homogeneous tuple[T, ...] is supported")

    if origin is types.UnionType or origin is Union:
        non_none_args = [a for a in args if a is not type(None)]
        if len(non_none_args) > 1:
            variant_handles = [_build_item_field(builder, a, nested_naming_case, visited) for a in non_none_args]
            return builder.union_field(name, optional, variant_handles, **kwargs)

    if dataclasses.is_dataclass(origin):
        dc_handle = _build_nested_dataclass(builder, hint, nested_naming_case, visited)
        return builder.nested_field(name, optional, dc_handle, **kwargs)

    raise NotImplementedError(f"Unsupported generic type: {origin}[{args}]")


def _build_primitive_field(
    builder: Any,
    name: str,
    hint: Any,
    optional: bool,
    strip_whitespaces: bool,
    decimal_places: int | None,
    decimal_places_explicitly_set: bool,
    decimal_rounding: str | None,
    datetime_format: str | None,
    default_decimal_places: int | None,
    nested_naming_case: Callable[[str], str] | None,
    visited: set[type],
    kwargs: dict[str, Any],
) -> Any:
    if hint is Any:
        return builder.any_field(name, optional, **kwargs)
    if hint is str:
        if strip_whitespaces:
            kwargs["strip_whitespaces"] = True
        return builder.str_field(name, optional, **kwargs)
    if hint is int:
        return builder.int_field(name, optional, **kwargs)
    if hint is float:
        return builder.float_field(name, optional, **kwargs)
    if hint is bool:
        return builder.bool_field(name, optional, **kwargs)
    if hint is decimal.Decimal:
        if decimal_places_explicitly_set:
            if decimal_places is not MISSING:
                kwargs["decimal_places"] = decimal_places
        elif default_decimal_places is not None:
            kwargs["decimal_places"] = default_decimal_places
        if decimal_rounding is not None:
            kwargs["rounding"] = decimal_rounding
        return builder.decimal_field(name, optional, **kwargs)
    if hint is uuid.UUID:
        return builder.uuid_field(name, optional, **kwargs)
    if hint is datetime.datetime:
        if datetime_format is not None:
            kwargs["datetime_format"] = datetime_format
        return builder.datetime_field(name, optional, **kwargs)
    if hint is datetime.date:
        return builder.date_field(name, optional, **kwargs)
    if hint is datetime.time:
        return builder.time_field(name, optional, **kwargs)
    if isinstance(hint, type) and issubclass(hint, enum.Enum):
        return _build_enum_field(builder, name, hint, optional, kwargs)
    if dataclasses.is_dataclass(hint):
        dc_handle = _build_nested_dataclass(builder, hint, nested_naming_case, visited)
        return builder.nested_field(name, optional, dc_handle, **kwargs)

    raise NotImplementedError(f"Unsupported type: {hint}")


def _build_enum_field(builder: Any, name: str, hint: type[enum.Enum], optional: bool, kwargs: dict[str, Any]) -> Any:
    enum_name = hint.__name__
    enum_members_repr = "[" + ", ".join(f"{hint.__name__}.{m.name}" for m in hint) + "]"

    if issubclass(hint, str):
        enum_values = [(m.value, m) for m in hint]
        return builder.str_enum_field(name, optional, hint, enum_values, enum_name, enum_members_repr, **kwargs)

    if issubclass(hint, int):
        enum_values = []
        for m in hint:
            if not (-(2**63) <= m.value < 2**63):
                raise NotImplementedError(f"IntEnum value {m.value} for {m} is outside i64 range [-2^63, 2^63)")
            enum_values.append((m.value, m))
        return builder.int_enum_field(name, optional, hint, enum_values, enum_name, enum_members_repr, **kwargs)

    raise NotImplementedError(f"Unsupported enum type: {hint} (must inherit from str or int)")


def _build_nested_dataclass(
    builder: Any, cls: Any, naming_case: Callable[[str], str] | None, visited: set[type]
) -> Any:
    origin: type = get_origin(cls) or cls  # type: ignore[assignment]

    if origin in visited:
        raise NotImplementedError(
            f"Cyclic dataclass references are not supported in nuked: {origin.__name__} references itself"
        )
    visited = visited | {origin}

    options = try_get_options_for(origin)
    effective_naming_case = naming_case
    if effective_naming_case is None and options and options.naming_case:
        effective_naming_case = options.naming_case

    cls_decimal_places: int | None = None
    if options and options.decimal_places is not MISSING and options.decimal_places is not None:
        cls_decimal_places = options.decimal_places

    has_post_init = hasattr(origin, "__post_init__")
    dc_params = getattr(origin, "__dataclass_params__", None)
    dataclass_init_enabled = dc_params.init if dc_params else True
    has_slots = hasattr(origin, "__slots__")

    all_fields_have_init = all(field.init for field in dataclasses.fields(origin))
    can_use_direct_slots = has_slots and dataclass_init_enabled and not has_post_init and all_fields_have_init

    type_hints = get_fields_type_map(cls)

    field_handles = []
    for field in dataclasses.fields(origin):
        hint = type_hints[field.name]
        has_default = field.default is not dataclasses.MISSING or field.default_factory is not dataclasses.MISSING
        default_value = field.default if field.default is not dataclasses.MISSING else dataclasses.MISSING
        default_factory = field.default_factory if field.default_factory is not dataclasses.MISSING else None

        field_handle, _ = _build_field(
            builder,
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
            visited=visited,
        )
        field_handles.append(field_handle)

    return builder.dataclass(
        origin, field_handles, can_use_direct_slots=can_use_direct_slots, has_post_init=has_post_init
    )


def _build_item_field(builder: Any, hint: Any, naming_case: Callable[[str], str] | None, visited: set[type]) -> Any:
    field_handle, _ = _build_field(
        builder, None, "", hint, None, naming_case, False, nested_naming_case=naming_case, visited=visited
    )
    return field_handle


def _build_value_field(builder: Any, hint: Any, naming_case: Callable[[str], str] | None, visited: set[type]) -> Any:
    field_handle, _ = _build_field(
        builder, None, "value", hint, None, naming_case, False, nested_naming_case=naming_case, visited=visited
    )
    return field_handle
