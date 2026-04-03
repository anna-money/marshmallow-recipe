"""marshmallow-recipe high-performance Rust backend (nuked).

Drop-in replacement for mr.dump/mr.load/mr.schema.
Indicative improvement: ~20x for dump, ~10x for load.

Core API:
    mr.nuked.dump(cls, obj)         Serialize dataclass to dict.
    mr.nuked.load(cls, data)        Deserialize dict to dataclass.
    mr.nuked.schema(cls)            Get cached Schema with Rust-backed load/dump.

    Use help(mr.nuked.dump), help(mr.nuked.load), help(mr.nuked.schema) for details.

Also supports root-level collections: mr.nuked.dump(dict[str, T], data).
"""

import ctypes
import dataclasses
import datetime
import decimal
import enum
import importlib.metadata
import types
import uuid
from collections.abc import Callable, Mapping, Sequence
from typing import Annotated, Any, ClassVar, Literal, NewType, TypeAliasType, Union, get_args, get_origin

import marshmallow

from .. import NamingCase, _nuked as nuked  # type: ignore[attr-defined]
from ..bake import bake_schema
from ..generics import get_fields_type_map
from ..hooks import get_pre_loads
from ..missing import MISSING
from ..options import NoneValueHandling, try_get_options_for
from ..utils import validate_decimal_places

__all__ = ("dump", "load", "schema")

_MARSHMALLOW_VERSION_MAJOR = int(importlib.metadata.version("marshmallow").split(".")[0])


def build_combined_validator(validators: list[Callable]) -> Callable[[Any], list[Any] | None]:
    def combined(value: Any) -> list[Any] | None:
        errors: list[Any] | None = None
        for validator in validators:
            try:
                result = validator(value)
                if result is False:
                    if errors is None:
                        errors = []
                    errors.append("Invalid value.")
            except marshmallow.ValidationError as e:
                if errors is None:
                    errors = []
                if isinstance(e.messages, list):
                    errors.extend(e.messages)
                else:
                    errors.append(e.messages)
            except Exception:
                if errors is None:
                    errors = []
                errors.append("Invalid value.")
        return errors

    return combined


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


def try_get_slot_offset(cls: type, field_name: str) -> int | None:
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
class _FieldMetadata:
    strip_whitespaces: bool = False
    decimal_places: int | None = None
    decimal_places_explicitly_set: bool = False
    decimal_rounding: str | None = None
    decimal_gt: decimal.Decimal | None = None
    decimal_gt_error: str | None = None
    decimal_gte: decimal.Decimal | None = None
    decimal_gte_error: str | None = None
    decimal_lt: decimal.Decimal | None = None
    decimal_lt_error: str | None = None
    decimal_lte: decimal.Decimal | None = None
    decimal_lte_error: str | None = None
    int_gt: int | None = None
    int_gt_error: str | None = None
    int_gte: int | None = None
    int_gte_error: str | None = None
    int_lt: int | None = None
    int_lt_error: str | None = None
    int_lte: int | None = None
    int_lte_error: str | None = None
    float_gt: float | int | None = None
    float_gt_error: str | None = None
    float_gte: float | int | None = None
    float_gte_error: str | None = None
    float_lt: float | int | None = None
    float_lt_error: str | None = None
    float_lte: float | int | None = None
    float_lte_error: str | None = None
    datetime_format: str | None = None
    item_validators: list[Callable] | None = None


@dataclasses.dataclass(slots=True, kw_only=True)
class _DataclassOptions:
    cls: type
    none_value_handling: NoneValueHandling | None
    decimal_places: int | None
    effective_naming_case: NamingCase | None


@dataclasses.dataclass(slots=True, kw_only=True)
class _SlotStrategy:
    can_use_direct_slots: bool
    has_post_init: bool


def build_container(
    cls: Any, naming_case: NamingCase | None, none_value_handling: NoneValueHandling | None, decimal_places: int | None
) -> Any:
    builder = nuked.ContainerBuilder(decimal_places=decimal_places if decimal_places is not MISSING else None)
    ctx = _BuildContext(builder, none_value_handling, decimal_places)
    type_handle = ctx.build_root_type(cls, naming_case)
    return builder.build(type_handle)


def try_get_dataclass_info(cls: Any, naming_case: NamingCase | None) -> _DataclassOptions | None:
    inner_dataclass = _try_find_inner_dataclass(cls)
    if inner_dataclass is None:
        return None
    return _analyze_dataclass_options(inner_dataclass, naming_case)


def _try_find_inner_dataclass(cls: Any) -> type | None:
    origin = get_origin(cls)
    args = get_args(cls)

    if origin is None:
        if dataclasses.is_dataclass(cls) and isinstance(cls, type):
            return cls
        return None

    if origin in (list, set, frozenset, Sequence) and args:
        return _try_find_inner_dataclass(args[0])

    if origin in (dict, Mapping) and len(args) > 1:
        return _try_find_inner_dataclass(args[1])

    if origin is tuple and len(args) == 2 and args[1] is ...:
        return _try_find_inner_dataclass(args[0])

    if origin is types.UnionType or origin is Union:
        non_none_args = [a for a in args if a is not type(None)]
        if len(non_none_args) == 1:
            return _try_find_inner_dataclass(non_none_args[0])
        for arg in non_none_args:
            result = _try_find_inner_dataclass(arg)
            if result is not None:
                return result
        return None

    if dataclasses.is_dataclass(origin):
        return origin  # type: ignore[return-value]

    return None


def _analyze_dataclass_options(cls: Any, naming_case: NamingCase | None) -> _DataclassOptions:
    origin: type = get_origin(cls) or cls  # type: ignore[assignment]

    if not dataclasses.is_dataclass(origin):
        raise TypeError(f"{origin} is not a dataclass")

    options = try_get_options_for(origin)

    cls_decimal_places: int | None = MISSING
    cls_none_value_handling: NoneValueHandling | None = None
    effective_naming_case = naming_case
    if options:
        if options.decimal_places is not MISSING:
            cls_decimal_places = options.decimal_places
        if options.none_value_handling is not None:
            cls_none_value_handling = options.none_value_handling
        if effective_naming_case is None and options.naming_case:
            effective_naming_case = options.naming_case

    return _DataclassOptions(
        cls=origin,
        none_value_handling=cls_none_value_handling,
        decimal_places=cls_decimal_places,
        effective_naming_case=effective_naming_case,
    )


def _analyze_slot_strategy(cls: type) -> _SlotStrategy:
    has_post_init = hasattr(cls, "__post_init__")
    dc_params = getattr(cls, "__dataclass_params__", None)
    dataclass_init_enabled = dc_params.init if dc_params else True
    has_slots = hasattr(cls, "__slots__")

    all_fields_have_init = all(field.init for field in dataclasses.fields(cls))
    can_use_direct_slots = has_slots and dataclass_init_enabled and not has_post_init and all_fields_have_init

    return _SlotStrategy(can_use_direct_slots=can_use_direct_slots, has_post_init=has_post_init)


class _BuildContext:
    __slots__ = ("__builder", "__dataclass_handles", "__decimal_places", "__none_value_handling")

    def __init__(self, builder: Any, none_value_handling: NoneValueHandling | None, decimal_places: int | None) -> None:
        self.__builder = builder
        self.__dataclass_handles: dict[Any, Any] = {}
        self.__none_value_handling = none_value_handling
        self.__decimal_places = decimal_places

    def __resolve_ignore_none(self, opts: _DataclassOptions) -> bool:
        effective = self.__none_value_handling or opts.none_value_handling
        return (effective or NoneValueHandling.IGNORE) == NoneValueHandling.IGNORE

    def build_root_type(self, cls: Any, naming_case: NamingCase | None) -> Any:
        while isinstance(cls, TypeAliasType):
            cls = cls.__value__
        origin = get_origin(cls)
        args = get_args(cls)

        if origin is None:
            if dataclasses.is_dataclass(cls):
                opts = _analyze_dataclass_options(cls, naming_case)
                slots = _analyze_slot_strategy(opts.cls)
                return self.__build_dataclass_type(cls, naming_case, opts, slots)
            field_handle = self.__build_item_field(cls, naming_case)
            return self.__builder.type_primitive(field_handle)

        if origin is list or origin is Sequence:
            item_type = args[0] if args else Any
            item_handle = self.build_root_type(item_type, naming_case)
            return self.__builder.type_list(item_handle)

        if origin is dict or origin is Mapping:
            value_type = args[1] if len(args) > 1 else Any
            value_handle = self.build_root_type(value_type, naming_case)
            return self.__builder.type_dict(value_handle)

        if origin is set:
            item_type = args[0] if args else Any
            item_handle = self.build_root_type(item_type, naming_case)
            return self.__builder.type_set(item_handle)

        if origin is frozenset:
            item_type = args[0] if args else Any
            item_handle = self.build_root_type(item_type, naming_case)
            return self.__builder.type_frozenset(item_handle)

        if origin is tuple:
            if len(args) == 2 and args[1] is ...:
                item_type = args[0]
                item_handle = self.build_root_type(item_type, naming_case)
                return self.__builder.type_tuple(item_handle)
            raise NotImplementedError("Only homogeneous tuple[T, ...] is supported at root level")

        if origin is types.UnionType or origin is Union:
            non_none_args = [a for a in args if a is not type(None)]
            has_none = type(None) in args
            if len(non_none_args) == 1 and has_none:
                inner_handle = self.build_root_type(non_none_args[0], naming_case)
                return self.__builder.type_optional(inner_handle)
            if len(non_none_args) > 1:
                variant_handles = [self.build_root_type(a, naming_case) for a in non_none_args]
                union_handle = self.__builder.type_union(variant_handles)
                if has_none:
                    return self.__builder.type_optional(union_handle)
                return union_handle

        if dataclasses.is_dataclass(origin):
            opts = _analyze_dataclass_options(origin, naming_case)
            slots = _analyze_slot_strategy(opts.cls)
            return self.__build_dataclass_type(cls, naming_case, opts, slots)

        raise TypeError(f"Unsupported root type: {cls}")

    def __build_dataclass_core(
        self, cls: Any, naming_case: NamingCase | None, opts: _DataclassOptions
    ) -> tuple[list[Any], list[tuple[str, str | None]], list[Any]]:
        origin: type = get_origin(cls) or cls  # type: ignore[assignment]

        pre_loads = get_pre_loads(origin)

        type_hints = get_fields_type_map(cls)

        field_handles = []
        field_data_keys: list[tuple[str, str | None]] = []

        for field in dataclasses.fields(origin):
            field_type = type_hints[field.name]
            has_default = field.default is not dataclasses.MISSING or field.default_factory is not dataclasses.MISSING
            default_value = field.default if field.default is not dataclasses.MISSING else dataclasses.MISSING
            default_factory = field.default_factory if field.default_factory is not dataclasses.MISSING else None

            field_handle, data_key = self.__build_field(
                origin,
                field.name,
                field_type,
                field.metadata,
                opts.effective_naming_case,
                has_default,
                default_value=default_value,
                default_factory=default_factory,
                field_init=field.init,
                default_decimal_places=opts.decimal_places
                if self.__decimal_places is MISSING
                else self.__decimal_places,
                nested_naming_case=naming_case,
            )
            field_handles.append(field_handle)
            field_data_keys.append((field.name, data_key))

        return field_handles, field_data_keys, pre_loads

    def __ensure_dataclass(
        self, cls: Any, naming_case: NamingCase | None, opts: _DataclassOptions, slots: _SlotStrategy
    ) -> Any:
        if cls in self.__dataclass_handles:
            return self.__dataclass_handles[cls]

        handle = self.__builder.reserve_dataclass()
        self.__dataclass_handles[cls] = handle

        field_handles, field_data_keys, pre_loads = self.__build_dataclass_core(cls, naming_case, opts)

        for name, data_key in field_data_keys:
            if data_key is None:
                continue
            for other_name, _ in field_data_keys:
                if name != other_name and data_key == other_name:
                    raise ValueError(f"Invalid name={data_key} in metadata for field={name}")

        self.__builder.finalize_dataclass(
            handle,
            opts.cls,
            field_handles,
            can_use_direct_slots=slots.can_use_direct_slots,
            has_post_init=slots.has_post_init,
            ignore_none=self.__resolve_ignore_none(opts),
            pre_loads=pre_loads,
        )
        return handle

    def __build_dataclass_type(
        self, cls: Any, naming_case: NamingCase | None, opts: _DataclassOptions, slots: _SlotStrategy
    ) -> Any:
        handle = self.__ensure_dataclass(cls, naming_case, opts, slots)
        return self.__builder.type_dataclass(handle)

    def __build_nested_dataclass(self, cls: Any, naming_case: NamingCase | None) -> Any:
        opts = _analyze_dataclass_options(cls, naming_case)
        slots = _analyze_slot_strategy(opts.cls)
        return self.__ensure_dataclass(cls, naming_case, opts, slots)

    def __build_field(
        self,
        cls: type | None,
        name: str,
        field_type: Any,
        metadata: Mapping[str, Any] | None,
        naming_case: NamingCase | None,
        has_default: bool,
        default_value: Any = dataclasses.MISSING,
        default_factory: Callable[[], Any] | None = None,
        field_init: bool = True,
        default_decimal_places: int | None = MISSING,
        nested_naming_case: NamingCase | None = None,
    ) -> tuple[Any, str | None]:
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
        decimal_gt: decimal.Decimal | None = None
        decimal_gt_error: str | None = None
        decimal_gte: decimal.Decimal | None = None
        decimal_gte_error: str | None = None
        decimal_lt: decimal.Decimal | None = None
        decimal_lt_error: str | None = None
        decimal_lte: decimal.Decimal | None = None
        decimal_lte_error: str | None = None
        int_gt: int | None = None
        int_gt_error: str | None = None
        int_gte: int | None = None
        int_gte_error: str | None = None
        int_lt: int | None = None
        int_lt_error: str | None = None
        int_lte: int | None = None
        int_lte_error: str | None = None
        float_gt: float | int | None = None
        float_gt_error: str | None = None
        float_gte: float | int | None = None
        float_gte_error: str | None = None
        float_lt: float | int | None = None
        float_lt_error: str | None = None
        float_lte: float | int | None = None
        float_lte_error: str | None = None

        if metadata:
            data_key = metadata.get("name")
            strip_whitespaces = metadata.get("strip_whitespaces", False)
            if "places" in metadata:
                decimal_places = metadata.get("places")
                decimal_places_explicitly_set = True
            decimal_rounding = metadata.get("rounding")
            decimal_gt = metadata.get("gt")
            decimal_gt_error = metadata.get("gt_error")
            decimal_gte = metadata.get("gte")
            decimal_gte_error = metadata.get("gte_error")
            decimal_lt = metadata.get("lt")
            decimal_lt_error = metadata.get("lt_error")
            decimal_lte = metadata.get("lte")
            decimal_lte_error = metadata.get("lte_error")
            int_gt = metadata.get("gt")
            int_gt_error = metadata.get("gt_error")
            int_gte = metadata.get("gte")
            int_gte_error = metadata.get("gte_error")
            int_lt = metadata.get("lt")
            int_lt_error = metadata.get("lt_error")
            int_lte = metadata.get("lte")
            int_lte_error = metadata.get("lte_error")
            float_gt = metadata.get("gt")
            float_gt_error = metadata.get("gt_error")
            float_gte = metadata.get("gte")
            float_gte_error = metadata.get("gte_error")
            float_lt = metadata.get("lt")
            float_lt_error = metadata.get("lt_error")
            float_lte = metadata.get("lte")
            float_lte_error = metadata.get("lte_error")
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

        while isinstance(field_type, TypeAliasType):
            field_type = field_type.__value__

        origin = get_origin(field_type)
        args = get_args(field_type)

        if origin is Annotated:
            field_type = args[0]
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
                    if "gt" in arg:
                        decimal_gt = arg["gt"]
                        int_gt = arg["gt"]
                        float_gt = arg["gt"]
                    if "gt_error" in arg:
                        decimal_gt_error = arg["gt_error"]
                        int_gt_error = arg["gt_error"]
                        float_gt_error = arg["gt_error"]
                    if "gte" in arg:
                        decimal_gte = arg["gte"]
                        int_gte = arg["gte"]
                        float_gte = arg["gte"]
                    if "gte_error" in arg:
                        decimal_gte_error = arg["gte_error"]
                        int_gte_error = arg["gte_error"]
                        float_gte_error = arg["gte_error"]
                    if "lt" in arg:
                        decimal_lt = arg["lt"]
                        int_lt = arg["lt"]
                        float_lt = arg["lt"]
                    if "lt_error" in arg:
                        decimal_lt_error = arg["lt_error"]
                        int_lt_error = arg["lt_error"]
                        float_lt_error = arg["lt_error"]
                    if "lte" in arg:
                        decimal_lte = arg["lte"]
                        int_lte = arg["lte"]
                        float_lte = arg["lte"]
                    if "lte_error" in arg:
                        decimal_lte_error = arg["lte_error"]
                        int_lte_error = arg["lte_error"]
                        float_lte_error = arg["lte_error"]
                    if "format" in arg:
                        datetime_format = arg["format"]
                    if "post_load" in arg:
                        post_load_callback = arg["post_load"]
                    if "validate" in arg:
                        validate = arg["validate"]
                        validators = list(validate) if isinstance(validate, list | tuple) else [validate]
            origin = get_origin(field_type)
            args = get_args(field_type)

        if origin is types.UnionType or origin is Union:
            non_none_args = [a for a in args if a is not type(None)]
            if Any in non_none_args:
                raise ValueError(
                    "Any type cannot be used in Optional or Union (Any | None, Optional[Any], Union[Any, ...] are invalid)"
                )
            if type(None) in args:
                optional = True
            if len(non_none_args) == 1:
                field_type = non_none_args[0]
                origin = get_origin(field_type)
                args = get_args(field_type)

        if data_key is None and naming_case is not None:
            data_key = naming_case(name)

        slot_offset = try_get_slot_offset(cls, name) if cls else None

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

        field_metadata = _FieldMetadata(
            strip_whitespaces=strip_whitespaces,
            decimal_places=decimal_places,
            decimal_places_explicitly_set=decimal_places_explicitly_set,
            decimal_rounding=decimal_rounding,
            decimal_gt=decimal_gt,
            decimal_gt_error=decimal_gt_error,
            decimal_gte=decimal_gte,
            decimal_gte_error=decimal_gte_error,
            decimal_lt=decimal_lt,
            decimal_lt_error=decimal_lt_error,
            decimal_lte=decimal_lte,
            decimal_lte_error=decimal_lte_error,
            int_gt=int_gt,
            int_gt_error=int_gt_error,
            int_gte=int_gte,
            int_gte_error=int_gte_error,
            int_lt=int_lt,
            int_lt_error=int_lt_error,
            int_lte=int_lte,
            int_lte_error=int_lte_error,
            float_gt=float_gt,
            float_gt_error=float_gt_error,
            float_gte=float_gte,
            float_gte_error=float_gte_error,
            float_lt=float_lt,
            float_lt_error=float_lt_error,
            float_lte=float_lte,
            float_lte_error=float_lte_error,
            datetime_format=datetime_format,
            item_validators=item_validators,
        )

        field_handle = self.__build_field_by_type(
            name, field_type, origin, args, optional, field_metadata, default_decimal_places, nested_naming_case, kwargs
        )

        return field_handle, data_key

    def __build_field_by_type(
        self,
        name: str,
        field_type: Any,
        origin: Any,
        args: tuple[Any, ...],
        optional: bool,
        field_metadata: _FieldMetadata,
        default_decimal_places: int | None,
        nested_naming_case: NamingCase | None,
        kwargs: dict[str, Any],
    ) -> Any:
        if isinstance(field_type, TypeAliasType):
            while isinstance(field_type, TypeAliasType):
                field_type = field_type.__value__
            origin = get_origin(field_type)
            args = get_args(field_type)

        if isinstance(field_type, NewType):
            field_type = field_type.__supertype__
            origin = get_origin(field_type)
            args = get_args(field_type)

        if origin is Literal:
            return self.__build_literal_field(name, args, optional, kwargs)

        if origin is None:
            return self.__build_primitive_field(
                name, field_type, optional, field_metadata, default_decimal_places, nested_naming_case, kwargs
            )

        if origin is list:
            item_type = args[0] if args else Any
            item_handle = self.__build_item_field(item_type, nested_naming_case)
            if field_metadata.item_validators:
                kwargs["item_validator"] = build_combined_validator(field_metadata.item_validators)
            return self.__builder.list_field(name, optional, item_handle, **kwargs)

        if origin is dict:
            value_type = args[1] if len(args) > 1 else Any
            value_handle = self.__build_value_field(value_type, nested_naming_case)
            return self.__builder.dict_field(name, optional, value_handle, **kwargs)

        if origin is set:
            item_type = args[0] if args else Any
            item_handle = self.__build_item_field(item_type, nested_naming_case)
            if field_metadata.item_validators:
                kwargs["item_validator"] = build_combined_validator(field_metadata.item_validators)
            return self.__builder.set_field(name, optional, item_handle, **kwargs)

        if origin is frozenset:
            item_type = args[0] if args else Any
            item_handle = self.__build_item_field(item_type, nested_naming_case)
            if field_metadata.item_validators:
                kwargs["item_validator"] = build_combined_validator(field_metadata.item_validators)
            return self.__builder.frozenset_field(name, optional, item_handle, **kwargs)

        if origin is Sequence:
            item_type = args[0] if args else Any
            item_handle = self.__build_item_field(item_type, nested_naming_case)
            if field_metadata.item_validators:
                kwargs["item_validator"] = build_combined_validator(field_metadata.item_validators)
            return self.__builder.list_field(name, optional, item_handle, **kwargs)

        if origin is Mapping:
            value_type = args[1] if len(args) > 1 else Any
            value_handle = self.__build_value_field(value_type, nested_naming_case)
            return self.__builder.dict_field(name, optional, value_handle, **kwargs)

        if origin is tuple:
            if len(args) == 2 and args[1] is ...:
                item_type = args[0]
                item_handle = self.__build_item_field(item_type, nested_naming_case)
                if field_metadata.item_validators:
                    kwargs["item_validator"] = build_combined_validator(field_metadata.item_validators)
                return self.__builder.tuple_field(name, optional, item_handle, **kwargs)
            raise NotImplementedError("Only homogeneous tuple[T, ...] is supported")

        if origin is types.UnionType or origin is Union:
            non_none_args = [a for a in args if a is not type(None)]
            if len(non_none_args) > 1:
                variant_handles = [self.__build_item_field(a, nested_naming_case) for a in non_none_args]
                return self.__builder.union_field(name, optional, variant_handles, **kwargs)

        if dataclasses.is_dataclass(origin):
            dc_handle = self.__build_nested_dataclass(field_type, nested_naming_case)
            return self.__builder.nested_field(name, optional, dc_handle, **kwargs)

        raise NotImplementedError(f"Unsupported generic type: {origin}[{args}]")

    def __build_primitive_field(
        self,
        name: str,
        field_type: Any,
        optional: bool,
        field_metadata: _FieldMetadata,
        default_decimal_places: int | None,
        nested_naming_case: NamingCase | None,
        kwargs: dict[str, Any],
    ) -> Any:
        if field_type is Any:
            return self.__builder.any_field(name, optional, **kwargs)
        if field_type is str:
            if field_metadata.strip_whitespaces:
                kwargs["strip_whitespaces"] = True
            return self.__builder.str_field(name, optional, **kwargs)
        if field_type is int:
            if field_metadata.int_gt is not None:
                kwargs["gt"] = field_metadata.int_gt
            if field_metadata.int_gt_error is not None:
                kwargs["gt_error"] = field_metadata.int_gt_error
            if field_metadata.int_gte is not None:
                kwargs["gte"] = field_metadata.int_gte
            if field_metadata.int_gte_error is not None:
                kwargs["gte_error"] = field_metadata.int_gte_error
            if field_metadata.int_lt is not None:
                kwargs["lt"] = field_metadata.int_lt
            if field_metadata.int_lt_error is not None:
                kwargs["lt_error"] = field_metadata.int_lt_error
            if field_metadata.int_lte is not None:
                kwargs["lte"] = field_metadata.int_lte
            if field_metadata.int_lte_error is not None:
                kwargs["lte_error"] = field_metadata.int_lte_error
            return self.__builder.int_field(name, optional, **kwargs)
        if field_type is float:
            if field_metadata.float_gt is not None:
                kwargs["gt"] = field_metadata.float_gt
            if field_metadata.float_gt_error is not None:
                kwargs["gt_error"] = field_metadata.float_gt_error
            if field_metadata.float_gte is not None:
                kwargs["gte"] = field_metadata.float_gte
            if field_metadata.float_gte_error is not None:
                kwargs["gte_error"] = field_metadata.float_gte_error
            if field_metadata.float_lt is not None:
                kwargs["lt"] = field_metadata.float_lt
            if field_metadata.float_lt_error is not None:
                kwargs["lt_error"] = field_metadata.float_lt_error
            if field_metadata.float_lte is not None:
                kwargs["lte"] = field_metadata.float_lte
            if field_metadata.float_lte_error is not None:
                kwargs["lte_error"] = field_metadata.float_lte_error
            return self.__builder.float_field(name, optional, **kwargs)
        if field_type is bool:
            return self.__builder.bool_field(name, optional, **kwargs)
        if field_type is decimal.Decimal:
            if field_metadata.decimal_places_explicitly_set:
                if field_metadata.decimal_places is not MISSING:
                    kwargs["decimal_places"] = field_metadata.decimal_places
            elif default_decimal_places is not MISSING:
                kwargs["decimal_places"] = default_decimal_places
            if field_metadata.decimal_rounding is not None:
                kwargs["rounding"] = field_metadata.decimal_rounding
            if field_metadata.decimal_gt is not None:
                kwargs["gt"] = field_metadata.decimal_gt
            if field_metadata.decimal_gt_error is not None:
                kwargs["gt_error"] = field_metadata.decimal_gt_error
            if field_metadata.decimal_gte is not None:
                kwargs["gte"] = field_metadata.decimal_gte
            if field_metadata.decimal_gte_error is not None:
                kwargs["gte_error"] = field_metadata.decimal_gte_error
            if field_metadata.decimal_lt is not None:
                kwargs["lt"] = field_metadata.decimal_lt
            if field_metadata.decimal_lt_error is not None:
                kwargs["lt_error"] = field_metadata.decimal_lt_error
            if field_metadata.decimal_lte is not None:
                kwargs["lte"] = field_metadata.decimal_lte
            if field_metadata.decimal_lte_error is not None:
                kwargs["lte_error"] = field_metadata.decimal_lte_error
            return self.__builder.decimal_field(name, optional, **kwargs)
        if field_type is uuid.UUID:
            return self.__builder.uuid_field(name, optional, **kwargs)
        if field_type is bytes:
            return self.__builder.bytes_field(name, optional, **kwargs)
        if field_type is datetime.datetime:
            if field_metadata.datetime_format is not None:
                kwargs["datetime_format"] = field_metadata.datetime_format
            return self.__builder.datetime_field(name, optional, **kwargs)
        if field_type is datetime.date:
            return self.__builder.date_field(name, optional, **kwargs)
        if field_type is datetime.time:
            return self.__builder.time_field(name, optional, **kwargs)
        if isinstance(field_type, type) and issubclass(field_type, enum.Enum):
            return self.__build_enum_field(name, field_type, optional, kwargs)
        if dataclasses.is_dataclass(field_type):
            dc_handle = self.__build_nested_dataclass(field_type, nested_naming_case)
            return self.__builder.nested_field(name, optional, dc_handle, **kwargs)

        raise NotImplementedError(f"Unsupported type: {field_type}")

    def __build_enum_field(self, name: str, field_type: type[enum.Enum], optional: bool, kwargs: dict[str, Any]) -> Any:
        if "invalid_error" not in kwargs:
            kwargs["invalid_error"] = f"Not a valid enum. Allowed values: {[e.value for e in field_type]}"

        if issubclass(field_type, str):
            enum_values = [(m.value, m) for m in field_type]
            return self.__builder.str_enum_field(name, optional, field_type, enum_values, **kwargs)

        if issubclass(field_type, int):
            enum_values = [(m.value, m) for m in field_type]
            return self.__builder.int_enum_field(name, optional, field_type, enum_values, **kwargs)

        raise NotImplementedError(f"Unsupported enum type: {field_type} (must inherit from str or int)")

    def __build_literal_field(self, name: str, values: tuple[Any, ...], optional: bool, kwargs: dict[str, Any]) -> Any:
        if not values:
            raise ValueError("Literal must have at least one value")

        if "invalid_error" not in kwargs:
            kwargs["invalid_error"] = f"Not a valid value. Allowed values: {list(values)}"

        if all(isinstance(v, str) for v in values):
            return self.__builder.str_literal_field(name, optional, list(values), **kwargs)

        if all(isinstance(v, bool) for v in values):
            return self.__builder.bool_literal_field(name, optional, list(values), **kwargs)

        if all(isinstance(v, int) and not isinstance(v, bool) for v in values):
            return self.__builder.int_literal_field(name, optional, list(values), **kwargs)

        raise ValueError(f"Unsupported Literal values: {values}. All values must be the same type (str, int, or bool)")

    def __build_item_field(self, field_type: Any, naming_case: NamingCase | None) -> Any:
        field_handle, _ = self.__build_field(
            None,
            "",
            field_type,
            None,
            naming_case,
            False,
            default_decimal_places=self.__decimal_places,
            nested_naming_case=naming_case,
        )
        return field_handle

    def __build_value_field(self, field_type: Any, naming_case: NamingCase | None) -> Any:
        field_handle, _ = self.__build_field(
            None,
            "value",
            field_type,
            None,
            naming_case,
            False,
            default_decimal_places=self.__decimal_places,
            nested_naming_case=naming_case,
        )
        return field_handle


ContainerKey = tuple[type, NamingCase | None, NoneValueHandling | None, int | None]

_container_cache: dict[ContainerKey, Any] = {}


def _get_container(
    cls: type, naming_case: NamingCase | None, none_value_handling: NoneValueHandling | None, decimal_places: int | None
) -> Any:
    key: ContainerKey = (cls, naming_case, none_value_handling, decimal_places)
    container = _container_cache.get(key)
    if container is None:
        container = build_container(cls, naming_case, none_value_handling, decimal_places)
        _container_cache[key] = container
    return container


def dump[T](
    cls: type[T],
    data: T,
    *,
    naming_case: NamingCase | None = None,
    none_value_handling: NoneValueHandling | None = None,
    decimal_places: int | None = MISSING,
) -> Any:
    """Serialize to a JSON-compatible value using the Rust backend.

    Returns a JSON-compatible value (dict, list, or primitive).

    Args:
        cls: Dataclass type or root collection type (e.g. ``list[User]``, ``dict[str, User]``).
        data: Instance to serialize.
        naming_case: Convert field names. Use ``mr.CAMEL_CASE``,
            ``mr.CAPITAL_CAMEL_CASE``, or ``mr.UPPER_SNAKE_CASE``.
        none_value_handling: Controls None field output.
            ``mr.NoneValueHandling.INCLUDE`` keeps None fields, default excludes them.
        decimal_places: Validate maximum decimal places for all Decimal fields.
    """
    validate_decimal_places(decimal_places)

    container = _get_container(cls, naming_case, none_value_handling, decimal_places)
    return container.dump(data)


def load[T](
    cls: type[T], data: Any, *, naming_case: NamingCase | None = None, decimal_places: int | None = MISSING
) -> T:
    """Deserialize from a JSON-compatible value using the Rust backend.

    Accepts dict for dataclasses, list for collections.

    Args:
        cls: Dataclass type or root collection type (e.g. ``list[User]``, ``dict[str, User]``).
        data: JSON-compatible value to deserialize.
        naming_case: Convert field names. Use ``mr.CAMEL_CASE``,
            ``mr.CAPITAL_CAMEL_CASE``, or ``mr.UPPER_SNAKE_CASE``.
        decimal_places: Validate maximum decimal places for all Decimal fields.
    """
    validate_decimal_places(decimal_places)

    container = _get_container(cls, naming_case, NoneValueHandling.IGNORE, decimal_places)
    return container.load(data)  # type: ignore[return-value]


SchemaKey = tuple[type, bool, NamingCase | None, NoneValueHandling | None, int | None]

_nuked_schemas: dict[SchemaKey, marshmallow.Schema] = {}

if _MARSHMALLOW_VERSION_MAJOR >= 3:

    def schema(
        cls: type,
        /,
        *,
        many: bool = False,
        naming_case: NamingCase | None = None,
        none_value_handling: NoneValueHandling | None = None,
        decimal_places: int | None = MISSING,
    ) -> marshmallow.Schema:
        """Get a cached marshmallow Schema backed by the Rust backend.

        Schema fields are available for introspection (e.g. apispec/OpenAPI),
        but actual serialization runs through Rust.
        Cached per (cls, many, naming_case, none_value_handling, decimal_places).

        Args:
            cls: Dataclass type.
            many: If True, schema handles lists of objects.
            naming_case: Convert field names. Use ``mr.CAMEL_CASE``,
                ``mr.CAPITAL_CAMEL_CASE``, or ``mr.UPPER_SNAKE_CASE``.
            none_value_handling: Controls None field output.
                ``mr.NoneValueHandling.INCLUDE`` keeps None fields, default excludes them.
            decimal_places: Validate maximum decimal places for all Decimal fields.

        Returns:
            Cached marshmallow Schema instance with Rust-backed load/dump.
        """
        validate_decimal_places(decimal_places)
        key: SchemaKey = (cls, many, naming_case, none_value_handling, decimal_places)
        existent = _nuked_schemas.get(key)
        if existent is not None:
            return existent

        schema_cls = bake_schema(
            cls, naming_case=naming_case, none_value_handling=none_value_handling, decimal_places=decimal_places
        )
        container = _get_container(cls, naming_case, none_value_handling, decimal_places)

        class _NukedSchema(schema_cls):  # type: ignore[misc]
            __slots__ = ()

            def load(
                self, data: Any, *, many: bool | None = None, partial: Any = None, unknown: str | None = None
            ) -> Any:  # type: ignore[override]
                if many if many is not None else self.many:
                    return [container.load(item) for item in data]
                return container.load(data)

            def dump(self, obj: Any, *, many: bool | None = None) -> Any:  # type: ignore[override]
                if many if many is not None else self.many:
                    return [container.dump(item) for item in obj]
                return container.dump(obj)

        new_schema = _NukedSchema(many=many)
        _nuked_schemas[key] = new_schema
        return new_schema

else:

    def schema(  # type: ignore[no-redef]
        cls: type,
        /,
        *,
        many: bool = False,
        naming_case: NamingCase | None = None,
        none_value_handling: NoneValueHandling | None = None,
        decimal_places: int | None = MISSING,
    ) -> marshmallow.Schema:
        validate_decimal_places(decimal_places)
        key: SchemaKey = (cls, many, naming_case, none_value_handling, decimal_places)
        existent = _nuked_schemas.get(key)
        if existent is not None:
            return existent

        schema_cls = bake_schema(
            cls, naming_case=naming_case, none_value_handling=none_value_handling, decimal_places=decimal_places
        )
        container = _get_container(cls, naming_case, none_value_handling, decimal_places)

        class _NukedSchema(schema_cls):  # type: ignore[misc]
            __slots__ = ()

            def load(self, data: Any, many: bool | None = None, partial: Any = None) -> Any:  # type: ignore[override]
                if many if many is not None else self.many:
                    loaded = [container.load(item) for item in data]
                else:
                    loaded = container.load(data)
                return marshmallow.UnmarshalResult(loaded, None)

            def dump(self, obj: Any, many: bool | None = None, **kwargs: Any) -> Any:  # type: ignore[override]
                if many if many is not None else self.many:
                    dumped = [container.dump(item) for item in obj]
                else:
                    dumped = container.dump(obj)
                return marshmallow.MarshalResult(dumped, None)

        new_schema = _NukedSchema(strict=True, many=many)  # type: ignore[call-arg]
        _nuked_schemas[key] = new_schema
        return new_schema
