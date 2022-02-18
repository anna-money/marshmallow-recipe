import decimal
import uuid
from typing import Any, Type

import marshmallow as m

from .missing import MISSING, Missing


def str_field(
    *,
    required: bool,
    default: str | None | Missing = MISSING,
    name: str | None = None,
    **_: Any,
) -> m.fields.Field:
    if required:
        if default is not MISSING:
            raise ValueError("Default values is not supported for required fields")

        return m.fields.String(required=True, dump_to=name, load_from=name)

    return m.fields.Str(
        dump_to=name,
        load_from=name,
        allow_none=True,
        missing=None if default is MISSING else default,
        default=None if default is MISSING else default,
    )


def bool_field(
    *,
    required: bool,
    default: bool | None | Missing = MISSING,
    name: str | None = None,
    **_: Any,
) -> m.fields.Field:
    if required:
        if default is not MISSING:
            raise ValueError("Default values is not supported for required fields")
        return m.fields.Boolean(dump_to=name, load_from=name, required=True)

    return m.fields.Bool(
        dump_to=name,
        load_from=name,
        allow_none=True,
        missing=None if default is MISSING else default,
        default=None if default is MISSING else default,
    )


def decimal_field(
    *,
    required: bool,
    default: decimal.Decimal | None | Missing = MISSING,
    name: str | None = None,
    places: int = 2,
    as_string: bool = True,
    **_: Any,
) -> m.fields.Field:
    if required:
        if default is not MISSING:
            raise ValueError("Default values is not supported for required fields")
        return m.fields.Decimal(dump_to=name, load_from=name, as_string=as_string, places=places, required=True)

    return m.fields.Decimal(
        dump_to=name,
        load_from=name,
        as_string=as_string,
        places=places,
        allow_none=True,
        missing=None if default is MISSING else default,
        default=None if default is MISSING else default,
    )


def int_field(
    *,
    required: bool,
    default: int | None | Missing = MISSING,
    name: str | None = None,
    **_: Any,
) -> m.fields.Field:
    if required:
        if default is not MISSING:
            raise ValueError("Default values is not supported for required fields")
        return m.fields.Int(dump_to=name, load_from=name, required=True)

    return m.fields.Int(
        dump_to=name,
        load_from=name,
        allow_none=True,
        missing=None if default is MISSING else default,
        default=None if default is MISSING else default,
    )


def float_field(
    *,
    required: bool,
    default: float | None | Missing = MISSING,
    name: str | None = None,
    **_: Any,
) -> m.fields.Field:
    if required:
        if default is not MISSING:
            raise ValueError("Default values is not supported for required fields")
        return m.fields.Float(dump_to=name, load_from=name, required=True)

    return m.fields.Float(
        dump_to=name,
        load_from=name,
        allow_none=True,
        missing=None if default is MISSING else default,
        default=None if default is MISSING else default,
    )


def uuid_field(
    *,
    required: bool,
    default: uuid.UUID | None | Missing = MISSING,
    name: str | None = None,
    **_: Any,
) -> m.fields.Field:
    if required:
        if default is not MISSING:
            raise ValueError("Default values is not supported for required fields")
        return m.fields.UUID(dump_to=name, load_from=name, required=True)

    return m.fields.UUID(
        dump_to=name,
        load_from=name,
        allow_none=True,
        missing=None if default is MISSING else default,
        default=None if default is MISSING else default,
    )


def nested_field(
    nested_schema: Type[m.Schema],
    *,
    required: bool,
    default: Any | None | Missing = MISSING,
    name: str | None = None,
    **_: Any,
) -> m.fields.Field:
    if required:
        if default is not MISSING:
            raise ValueError("Default values is not supported for required fields")
        return m.fields.Nested(nested_schema, dump_to=name, load_from=name, required=True)

    if default is not MISSING and default is not None:
        raise ValueError("Default values is not supported for required fields")
    return m.fields.Nested(
        nested_schema,
        dump_to=name,
        load_from=name,
        allow_none=True,
        missing=None,
        default=None,
    )


def list_field(
    field: m.fields.Field,
    *,
    required: bool,
    default: Any | None | Missing = MISSING,
    name: str | None = None,
    **_: Any,
) -> m.fields.Field:
    if required:
        if default is not MISSING:
            raise ValueError("Default values is not supported for required fields")
        return m.fields.List(field, dump_to=name, load_from=name, required=True)

    if default is not MISSING and default is not None:
        raise ValueError("Default values is not supported for required fields")
    return m.fields.List(
        field,
        dump_to=name,
        load_from=name,
        allow_none=True,
        missing=None,
        default=None,
    )


def dict_field(
    *,
    required: bool,
    default: Any | None | Missing = MISSING,
    name: str | None = None,
    **_: Any,
) -> m.fields.Field:
    if required:
        if default is not MISSING:
            raise ValueError("Default values is not supported for required fields")
        return m.fields.Dict(dump_to=name, load_from=name, required=True)

    if default is not MISSING and default is not None:
        raise ValueError("Default values is not supported for required fields")
    return m.fields.Dict(
        dump_to=name,
        load_from=name,
        allow_none=True,
        missing=None,
        default=None,
    )
