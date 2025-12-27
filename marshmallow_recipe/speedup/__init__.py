import dataclasses
import typing
from collections.abc import Callable
from typing import Annotated, Any, get_args, get_origin, get_type_hints

import marshmallow
from marshmallow_recipe_speedup import _core  # type: ignore[attr-defined]

from marshmallow_recipe.speedup._descriptor import TypeDescriptor, build_type_descriptor

__all__ = ["dump", "load"]

_schema_id_counter: int = 0
_schema_id_map: dict[tuple[type, Callable[[str], str] | None], int] = {}
_schema_cache: dict[int, tuple[dict | None, dict | None]] = {}


def _get_schema_id(cls: type, naming_case: Callable[[str], str] | None) -> int:
    global _schema_id_counter
    key = (cls, naming_case)
    if key not in _schema_id_map:
        _schema_id_map[key] = _schema_id_counter
        _schema_id_counter += 1
    return _schema_id_map[key]


def _convert_rust_error_to_validation_error(e: ValueError) -> marshmallow.ValidationError:
    if hasattr(e, "args") and len(e.args) > 0 and isinstance(e.args[0], dict):
        return marshmallow.ValidationError(e.args[0])
    raise e


def _build_raw_schema(cls: type, naming_case: Callable[[str], str] | None) -> dict:
    descriptor = build_type_descriptor(cls, naming_case)
    return _descriptor_to_dict(descriptor)


def _descriptor_to_dict(descriptor: TypeDescriptor) -> dict:
    result: dict[str, Any] = {"type_kind": descriptor.type_kind}

    if descriptor.cls is not None:
        result["cls"] = descriptor.cls

    if descriptor.primitive_type is not None:
        result["primitive_type"] = descriptor.primitive_type

    if descriptor.optional:
        result["optional"] = True

    if descriptor.inner_type is not None:
        result["inner_type"] = _descriptor_to_dict(descriptor.inner_type)

    if descriptor.item_type is not None:
        result["item_type"] = _descriptor_to_dict(descriptor.item_type)

    if descriptor.key_type is not None:
        result["key_type"] = descriptor.key_type

    if descriptor.value_type is not None:
        result["value_type"] = _descriptor_to_dict(descriptor.value_type)

    if descriptor.fields:
        result["fields"] = [_field_to_dict(f) for f in descriptor.fields]

    if descriptor.union_variants is not None:
        result["union_variants"] = [_descriptor_to_dict(v) for v in descriptor.union_variants]

    if descriptor.can_use_direct_slots:
        result["can_use_direct_slots"] = True

    if descriptor.has_post_init:
        result["has_post_init"] = True

    return result


def _field_to_dict(field: Any) -> dict:
    result: dict[str, Any] = {"name": field.name, "field_type": field.field_type, "optional": field.optional}

    if field.slot_offset is not None:
        result["slot_offset"] = field.slot_offset

    if field.serialized_name is not None:
        result["serialized_name"] = field.serialized_name

    if field.strip_whitespaces:
        result["strip_whitespaces"] = True

    if field.decimal_places is not None:
        result["decimal_places"] = field.decimal_places

    if not field.decimal_as_string:
        result["decimal_as_string"] = False

    if field.datetime_format is not None:
        result["datetime_format"] = field.datetime_format

    if field.nested_schema is not None:
        nested = {"cls": field.nested_schema.cls, "fields": [_field_to_dict(f) for f in field.nested_schema.fields]}
        if field.nested_schema.can_use_direct_slots:
            nested["can_use_direct_slots"] = True
        if field.nested_schema.has_post_init:
            nested["has_post_init"] = True
        result["nested_schema"] = nested

    if field.item_schema is not None:
        result["item_schema"] = _field_to_dict(field.item_schema)

    if field.key_type is not None:
        result["key_type"] = field.key_type

    if field.value_schema is not None:
        result["value_schema"] = _field_to_dict(field.value_schema)

    if field.enum_cls is not None:
        result["enum_cls"] = field.enum_cls

    if field.union_variants is not None:
        result["union_variants"] = [_field_to_dict(v) for v in field.union_variants]

    if field.default_value is not dataclasses.MISSING:
        result["default_value"] = field.default_value

    if field.default_factory is not None:
        result["default_factory"] = field.default_factory

    if not field.field_init:
        result["field_init"] = False

    return result


def _extract_callbacks(cls: type) -> tuple[dict | None, dict | None]:
    if not dataclasses.is_dataclass(cls):
        return None, None

    post_loads: dict[str, Callable] = {}
    validators: dict[str, list[Callable]] = {}

    type_hints = get_type_hints(cls, include_extras=True)

    for field in dataclasses.fields(cls):
        hint = type_hints[field.name]
        post_load, field_validators = _extract_field_callbacks(hint, field.metadata)

        if post_load is not None:
            post_loads[field.name] = post_load
        if field_validators:
            validators[field.name] = field_validators

    return post_loads if post_loads else None, validators if validators else None


def _extract_field_callbacks(
    hint: Any, metadata: typing.Mapping[str, Any] | None
) -> tuple[Callable | None, list[Callable]]:
    post_load: Callable | None = None
    field_validators: list[Callable] = []

    if metadata:
        post_load = metadata.get("post_load")
        validate = metadata.get("validate")
        if validate is not None:
            if isinstance(validate, list | tuple):
                field_validators.extend(validate)
            else:
                field_validators.append(validate)

    origin = get_origin(hint)
    args = get_args(hint)

    if origin is Annotated:
        for arg in args[1:]:
            if isinstance(arg, dict):
                if "post_load" in arg and post_load is None:
                    post_load = arg["post_load"]
                if "validate" in arg:
                    validate = arg["validate"]
                    if isinstance(validate, list | tuple):
                        field_validators.extend(validate)
                    else:
                        field_validators.append(validate)

    return post_load, field_validators


def _ensure_registered(cls: type, naming_case: Callable[[str], str] | None) -> int:
    schema_id = _get_schema_id(cls, naming_case)

    if schema_id not in _schema_cache:
        raw_schema = _build_raw_schema(cls, naming_case)
        callbacks = _extract_callbacks(cls)
        _schema_cache[schema_id] = callbacks
        assert _core is not None
        _core.register_schema(schema_id, raw_schema)

    return schema_id


def dump[T](
    cls: type[T],
    data: T,
    *,
    naming_case: typing.Callable[[str], str] | None = None,
    none_value_handling: str | None = None,
    decimal_places: int | None = None,
    encoding: str = "utf-8",
) -> bytes:
    schema_id = _ensure_registered(cls, naming_case)
    _, validators = _schema_cache[schema_id]
    none_handling = none_value_handling if none_value_handling else "ignore"
    try:
        return _core.dump_cached(schema_id, data, none_handling, validators, decimal_places, encoding)
    except ValueError as e:
        raise _convert_rust_error_to_validation_error(e)


def load[T](
    cls: type[T], data: bytes, *, naming_case: typing.Callable[[str], str] | None = None, encoding: str = "utf-8"
) -> T:
    schema_id = _ensure_registered(cls, naming_case)
    post_loads, validators = _schema_cache[schema_id]
    try:
        return _core.load_cached(schema_id, data, post_loads, validators, encoding)  # type: ignore[return-value]
    except ValueError as e:
        raise _convert_rust_error_to_validation_error(e)
