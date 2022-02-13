from typing import Any

import marshmallow as m

from .missing import MISSING, MissingType


def string(
    required: bool,
    name: str,
    default: str | None | MissingType,
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


def boolean(
    required: bool,
    name: str,
    default: bool | None | MissingType,
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
