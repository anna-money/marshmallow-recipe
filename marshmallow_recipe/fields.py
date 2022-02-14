import decimal
from typing import Any, Type, Union

import marshmallow as m

from .missing import MISSING, MissingType


def str_field(
    *,
    required: bool,
    name: str,
    default: Union[str, None, MissingType],
    **_: Any,
) -> m.fields.Field:
    if required:
        if default is not MISSING:
            raise ValueError("Default values is not supported for required fields")

        return m.fields.String(required=True, dump_to=name, load_from=name)

    return m.fields.String(
        dump_to=name,
        load_from=name,
        allow_none=True,
        missing=None if default is MISSING else default,
        default=None if default is MISSING else default,
    )


def bool_field(
    *,
    required: bool,
    name: str,
    default: Union[bool, None, MissingType],
    **_: Any,
) -> m.fields.Field:
    if required:
        if default is not MISSING:
            raise ValueError("Default values is not supported for required fields")
        return m.fields.Boolean(dump_to=name, load_from=name, required=True)

    return m.fields.Boolean(
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
    name: str,
    default: Union[Any, None, MissingType],
    **_: Any,
) -> m.fields.Field:
    if required:
        if default is not MISSING:
            raise ValueError("Default values is not supported for required fields")
        return m.fields.Nested(nested_schema, dump_to=name, load_from=name, required=True)

    if default is not MISSING and default is not None:
        raise ValueError("Default values is not supported for required fields")
    return (
        m.fields.Nested(nested_schema, dump_to=name, load_from=name, required=True)
        if required
        else m.fields.Nested(nested_schema, dump_to=name, load_from=name, allow_none=True, missing=None, default=None)
    )


def decimal_field(
    required: bool,
    name: str,
    default: Union[decimal.Decimal, None, MissingType],
    **_: Any,
) -> m.fields.Field:
    if required:
        if default is not MISSING:
            raise ValueError("Default values is not supported for required fields")
        return m.fields.Decimal(dump_to=name, load_from=name, as_string=True, places=2, required=True)

    return m.fields.Decimal(
        dump_to=name,
        load_from=name,
        as_string=True,
        places=2,
        allow_none=True,
        missing=None if default is MISSING else default,
        default=None if default is MISSING else default,
    )
