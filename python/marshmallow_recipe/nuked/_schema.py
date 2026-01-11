import dataclasses
from collections.abc import Callable
from typing import Any

from ._descriptor import TypeDescriptor
from ._validator import build_combined_validator


def descriptor_to_dict(descriptor: TypeDescriptor) -> dict:
    result: dict[str, Any] = {"type_kind": descriptor.type_kind}

    if descriptor.cls is not None:
        result["cls"] = descriptor.cls

    if descriptor.primitive_type is not None:
        result["primitive_type"] = descriptor.primitive_type

    if descriptor.optional:
        result["optional"] = True

    if descriptor.inner_type is not None:
        result["inner_type"] = descriptor_to_dict(descriptor.inner_type)

    if descriptor.item_type is not None:
        result["item_type"] = descriptor_to_dict(descriptor.item_type)

    if descriptor.key_type is not None:
        result["key_type"] = descriptor.key_type

    if descriptor.value_type is not None:
        result["value_type"] = descriptor_to_dict(descriptor.value_type)

    if descriptor.fields:
        result["fields"] = [field_to_dict(f) for f in descriptor.fields]

    if descriptor.union_variants is not None:
        result["union_variants"] = [descriptor_to_dict(v) for v in descriptor.union_variants]

    if descriptor.can_use_direct_slots:
        result["can_use_direct_slots"] = True

    if descriptor.has_post_init:
        result["has_post_init"] = True

    return result


def field_to_dict(field: Any, visited_schemas: set[type] | None = None) -> dict:
    if visited_schemas is None:
        visited_schemas = set()

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

    if field.decimal_rounding is not None:
        result["decimal_rounding"] = field.decimal_rounding

    if field.datetime_format is not None:
        result["datetime_format"] = field.datetime_format

    if field.nested_schema is not None:
        if field.nested_schema.cls in visited_schemas:
            raise NotImplementedError(
                f"Cyclic dataclass references are not supported in nuked: "
                f"{field.nested_schema.cls.__name__} references itself"
            )
        visited_schemas.add(field.nested_schema.cls)
        nested = {
            "cls": field.nested_schema.cls,
            "fields": [field_to_dict(f, visited_schemas) for f in field.nested_schema.fields],
        }
        if field.nested_schema.can_use_direct_slots:
            nested["can_use_direct_slots"] = True
        if field.nested_schema.has_post_init:
            nested["has_post_init"] = True
        result["nested_schema"] = nested

    if field.item_schema is not None:
        result["item_schema"] = field_to_dict(field.item_schema, visited_schemas)

    if field.key_type is not None:
        result["key_type"] = field.key_type

    if field.value_schema is not None:
        result["value_schema"] = field_to_dict(field.value_schema, visited_schemas)

    if field.enum_cls is not None:
        result["enum_cls"] = field.enum_cls

    if field.enum_values is not None:
        result["enum_values"] = field.enum_values

    if field.enum_name is not None:
        result["enum_name"] = field.enum_name

    if field.enum_members_repr is not None:
        result["enum_members_repr"] = field.enum_members_repr

    if field.union_variants is not None:
        result["union_variants"] = [field_to_dict(v, visited_schemas) for v in field.union_variants]

    if field.default_value is not dataclasses.MISSING:
        result["default_value"] = field.default_value

    if field.default_factory is not None:
        result["default_factory"] = field.default_factory

    if not field.field_init:
        result["field_init"] = False

    if field.required_error is not None:
        result["required_error"] = field.required_error

    if field.none_error is not None:
        result["none_error"] = field.none_error

    if field.invalid_error is not None:
        result["invalid_error"] = field.invalid_error

    if field.validators:
        result["validator"] = build_combined_validator(field.validators)

    if field.item_schema is not None and field.item_schema.validators:
        result["item_validator"] = build_combined_validator(field.item_schema.validators)

    if field.value_schema is not None and field.value_schema.validators:
        result["value_validator"] = build_combined_validator(field.value_schema.validators)

    return result


def extract_post_loads(descriptor: TypeDescriptor) -> dict | None:
    post_loads: dict[str, Callable] = {}

    if descriptor.fields:
        for field in descriptor.fields:
            if hasattr(field, "post_load") and field.post_load is not None:
                post_loads[field.name] = field.post_load

    return post_loads if post_loads else None
