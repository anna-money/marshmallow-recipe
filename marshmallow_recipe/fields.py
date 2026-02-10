import collections
import collections.abc
import dataclasses
import datetime
import decimal
import enum
import importlib.metadata
import math
import types
from typing import Any

import marshmallow as m
import marshmallow.validate

from .validation import ValidationFunc, combine_validators

_MARSHMALLOW_VERSION_MAJOR = int(importlib.metadata.version("marshmallow").split(".")[0])


def str_field(
    *,
    required: bool,
    allow_none: bool,
    default: Any = dataclasses.MISSING,
    name: str | None = None,
    validate: ValidationFunc | collections.abc.Sequence[ValidationFunc] | None = None,
    strip_whitespaces: bool = False,
    post_load: collections.abc.Callable[[str], str] | None = None,
    required_error: str | None = None,
    none_error: str | None = None,
    invalid_error: str | None = None,
    description: str | None = None,
    **_: Any,
) -> m.fields.Field:
    if default is m.missing:
        return StrField(
            allow_none=allow_none,
            validate=validate,
            strip_whitespaces=strip_whitespaces,
            post_load=post_load,
            **default_fields(m.missing),
            **data_key_fields(name),
            **description_fields(description),
            error_messages=build_error_messages(
                required_error=required_error, none_error=none_error, invalid_error=invalid_error
            ),
        )

    if required:
        if default is None:
            raise ValueError("Default value cannot be none")

        return StrField(
            required=True,
            allow_none=allow_none,
            validate=validate,
            strip_whitespaces=strip_whitespaces,
            post_load=post_load,
            **data_key_fields(name),
            **description_fields(description),
            error_messages=build_error_messages(
                required_error=required_error, none_error=none_error, invalid_error=invalid_error
            ),
        )

    return StrField(
        allow_none=allow_none,
        validate=validate,
        strip_whitespaces=strip_whitespaces,
        post_load=post_load,
        **(default_fields(None) if default is dataclasses.MISSING else {}),
        **data_key_fields(name),
        **description_fields(description),
        error_messages=build_error_messages(
            required_error=required_error, none_error=none_error, invalid_error=invalid_error
        ),
    )


def bool_field(
    *,
    required: bool,
    allow_none: bool,
    default: Any = dataclasses.MISSING,
    name: str | None = None,
    validate: ValidationFunc | collections.abc.Sequence[ValidationFunc] | None = None,
    required_error: str | None = None,
    none_error: str | None = None,
    invalid_error: str | None = None,
    description: str | None = None,
    **_: Any,
) -> m.fields.Field:
    if default is m.missing:
        return m.fields.Bool(
            allow_none=allow_none,
            validate=validate,
            **default_fields(m.missing),
            **data_key_fields(name),
            **description_fields(description),
            error_messages=build_error_messages(
                required_error=required_error, none_error=none_error, invalid_error=invalid_error
            ),
        )

    if required:
        if default is None:
            raise ValueError("Default value cannot be none")

        return m.fields.Bool(
            required=True,
            allow_none=allow_none,
            validate=validate,
            **data_key_fields(name),
            **description_fields(description),
            error_messages=build_error_messages(
                required_error=required_error, none_error=none_error, invalid_error=invalid_error
            ),
        )

    return m.fields.Bool(
        allow_none=allow_none,
        validate=validate,
        **(default_fields(None) if default is dataclasses.MISSING else {}),
        **data_key_fields(name),
        **description_fields(description),
        error_messages=build_error_messages(
            required_error=required_error, none_error=none_error, invalid_error=invalid_error
        ),
    )


def decimal_field(
    *,
    required: bool,
    allow_none: bool,
    default: Any = dataclasses.MISSING,
    name: str | None = None,
    places: int | None = 2,
    rounding: str | None = None,
    validate: ValidationFunc | collections.abc.Sequence[ValidationFunc] | None = None,
    required_error: str | None = None,
    none_error: str | None = None,
    invalid_error: str | None = None,
    description: str | None = None,
    **_: Any,
) -> m.fields.Field:
    if default is m.missing:
        return DecimalField(
            allow_none=allow_none,
            as_string=True,
            places=places,
            rounding=rounding,
            validate=validate,
            **default_fields(m.missing),
            **data_key_fields(name),
            **description_fields(description),
            error_messages=build_error_messages(
                required_error=required_error, none_error=none_error, invalid_error=invalid_error
            ),
        )

    if required:
        if default is None:
            raise ValueError("Default value cannot be none")
        return DecimalField(
            required=True,
            allow_none=allow_none,
            as_string=True,
            places=places,
            rounding=rounding,
            validate=validate,
            **data_key_fields(name),
            **description_fields(description),
            error_messages=build_error_messages(
                required_error=required_error, none_error=none_error, invalid_error=invalid_error
            ),
        )

    return DecimalField(
        allow_none=allow_none,
        as_string=True,
        places=places,
        rounding=rounding,
        validate=validate,
        **(default_fields(None) if default is dataclasses.MISSING else {}),
        **data_key_fields(name),
        **description_fields(description),
        error_messages=build_error_messages(
            required_error=required_error, none_error=none_error, invalid_error=invalid_error
        ),
    )


def int_field(
    *,
    required: bool,
    allow_none: bool,
    default: Any = dataclasses.MISSING,
    name: str | None = None,
    validate: ValidationFunc | collections.abc.Sequence[ValidationFunc] | None = None,
    required_error: str | None = None,
    none_error: str | None = None,
    invalid_error: str | None = None,
    description: str | None = None,
    **_: Any,
) -> m.fields.Field:
    if default is m.missing:
        field = m.fields.Int(
            allow_none=allow_none,
            validate=validate,
            **default_fields(m.missing),
            **data_key_fields(name),
            **description_fields(description),
            error_messages=build_error_messages(
                required_error=required_error, none_error=none_error, invalid_error=invalid_error
            ),
        )
    elif required:
        if default is None:
            raise ValueError("Default value cannot be none")
        field = m.fields.Int(
            required=True,
            allow_none=allow_none,
            validate=validate,
            **data_key_fields(name),
            **description_fields(description),
            error_messages=build_error_messages(
                required_error=required_error, none_error=none_error, invalid_error=invalid_error
            ),
        )
    else:
        field = m.fields.Int(
            allow_none=allow_none,
            validate=validate,
            **(default_fields(None) if default is dataclasses.MISSING else {}),
            **data_key_fields(name),
            **description_fields(description),
            error_messages=build_error_messages(
                required_error=required_error, none_error=none_error, invalid_error=invalid_error
            ),
        )
    return with_type_checks_on_validated(field, (int, str))


def float_field(
    *,
    required: bool,
    allow_none: bool,
    default: Any = dataclasses.MISSING,
    name: str | None = None,
    validate: ValidationFunc | collections.abc.Sequence[ValidationFunc] | None = None,
    required_error: str | None = None,
    none_error: str | None = None,
    invalid_error: str | None = None,
    description: str | None = None,
    **_: Any,
) -> m.fields.Field:
    if default is m.missing:
        return FloatField(
            allow_none=allow_none,
            validate=validate,
            **default_fields(m.missing),
            **data_key_fields(name),
            **description_fields(description),
            error_messages=build_error_messages(
                required_error=required_error, none_error=none_error, invalid_error=invalid_error
            ),
        )

    if required:
        if default is None:
            raise ValueError("Default value cannot be none")
        return FloatField(
            required=True,
            allow_none=allow_none,
            validate=validate,
            **data_key_fields(name),
            **description_fields(description),
            error_messages=build_error_messages(
                required_error=required_error, none_error=none_error, invalid_error=invalid_error
            ),
        )

    return FloatField(
        allow_none=allow_none,
        validate=validate,
        **(default_fields(None) if default is dataclasses.MISSING else {}),
        **data_key_fields(name),
        **description_fields(description),
        error_messages=build_error_messages(
            required_error=required_error, none_error=none_error, invalid_error=invalid_error
        ),
    )


def uuid_field(
    *,
    required: bool,
    allow_none: bool,
    default: Any = dataclasses.MISSING,
    name: str | None = None,
    validate: ValidationFunc | collections.abc.Sequence[ValidationFunc] | None = None,
    required_error: str | None = None,
    none_error: str | None = None,
    invalid_error: str | None = None,
    description: str | None = None,
    **_: Any,
) -> m.fields.Field:
    if default is m.missing:
        return m.fields.UUID(
            allow_none=allow_none,
            validate=validate,
            **default_fields(m.missing),
            **data_key_fields(name),
            **description_fields(description),
            error_messages=build_uuid_error_messages(
                required_error=required_error, none_error=none_error, invalid_error=invalid_error
            ),
        )

    if required:
        if default is None:
            raise ValueError("Default value cannot be none")
        return m.fields.UUID(
            required=True,
            allow_none=allow_none,
            validate=validate,
            **data_key_fields(name),
            **description_fields(description),
            error_messages=build_uuid_error_messages(
                required_error=required_error, none_error=none_error, invalid_error=invalid_error
            ),
        )

    return m.fields.UUID(
        allow_none=allow_none,
        validate=validate,
        **(default_fields(None) if default is dataclasses.MISSING else {}),
        **data_key_fields(name),
        **description_fields(description),
        error_messages=build_uuid_error_messages(
            required_error=required_error, none_error=none_error, invalid_error=invalid_error
        ),
    )


def datetime_field(
    *,
    required: bool,
    allow_none: bool,
    default: Any = dataclasses.MISSING,
    name: str | None = None,
    validate: ValidationFunc | collections.abc.Sequence[ValidationFunc] | None = None,
    format: str | None = None,
    required_error: str | None = None,
    none_error: str | None = None,
    invalid_error: str | None = None,
    description: str | None = None,
    **_: Any,
) -> m.fields.Field:
    if default is m.missing:
        return DateTimeField(
            allow_none=allow_none,
            validate=validate,
            format=format,
            **default_fields(m.missing),
            **data_key_fields(name),
            **description_fields(description),
            error_messages=build_error_messages(
                required_error=required_error, none_error=none_error, invalid_error=invalid_error
            ),
        )

    if required:
        if default is None:
            raise ValueError("Default value cannot be none")
        return DateTimeField(
            required=True,
            allow_none=allow_none,
            validate=validate,
            format=format,
            **data_key_fields(name),
            **description_fields(description),
            error_messages=build_error_messages(
                required_error=required_error, none_error=none_error, invalid_error=invalid_error
            ),
        )

    return DateTimeField(
        allow_none=allow_none,
        validate=validate,
        format=format,
        **(default_fields(None) if default is dataclasses.MISSING else {}),
        **data_key_fields(name),
        **description_fields(description),
        error_messages=build_error_messages(
            required_error=required_error, none_error=none_error, invalid_error=invalid_error
        ),
    )


def time_field(
    *,
    required: bool,
    allow_none: bool,
    default: Any = dataclasses.MISSING,
    name: str | None = None,
    validate: ValidationFunc | collections.abc.Sequence[ValidationFunc] | None = None,
    required_error: str | None = None,
    none_error: str | None = None,
    invalid_error: str | None = None,
    description: str | None = None,
    **_: Any,
) -> m.fields.Field:
    if default is m.missing:
        return m.fields.Time(
            allow_none=allow_none,
            validate=validate,
            **default_fields(m.missing),
            **data_key_fields(name),
            **description_fields(description),
            error_messages=build_error_messages(
                required_error=required_error, none_error=none_error, invalid_error=invalid_error
            ),
        )

    if required:
        if default is None:
            raise ValueError("Default value cannot be none")
        return m.fields.Time(
            required=True,
            allow_none=allow_none,
            validate=validate,
            **data_key_fields(name),
            **description_fields(description),
            error_messages=build_error_messages(
                required_error=required_error, none_error=none_error, invalid_error=invalid_error
            ),
        )

    return m.fields.Time(
        allow_none=allow_none,
        validate=validate,
        **(default_fields(None) if default is dataclasses.MISSING else {}),
        **data_key_fields(name),
        **description_fields(description),
        error_messages=build_error_messages(
            required_error=required_error, none_error=none_error, invalid_error=invalid_error
        ),
    )


def date_field(
    *,
    required: bool,
    allow_none: bool,
    default: Any = dataclasses.MISSING,
    name: str | None = None,
    validate: ValidationFunc | collections.abc.Sequence[ValidationFunc] | None = None,
    required_error: str | None = None,
    none_error: str | None = None,
    invalid_error: str | None = None,
    description: str | None = None,
    **_: Any,
) -> m.fields.Field:
    if default is m.missing:
        return DateField(
            allow_none=allow_none,
            validate=validate,
            **default_fields(m.missing),
            **data_key_fields(name),
            **description_fields(description),
            error_messages=build_error_messages(
                required_error=required_error, none_error=none_error, invalid_error=invalid_error
            ),
        )

    if required:
        if default is None:
            raise ValueError("Default value cannot be none")
        return DateField(
            required=True,
            allow_none=allow_none,
            validate=validate,
            **data_key_fields(name),
            **description_fields(description),
            error_messages=build_error_messages(
                required_error=required_error, none_error=none_error, invalid_error=invalid_error
            ),
        )

    return DateField(
        allow_none=allow_none,
        validate=validate,
        **(default_fields(None) if default is dataclasses.MISSING else {}),
        **data_key_fields(name),
        **description_fields(description),
        error_messages=build_error_messages(
            required_error=required_error, none_error=none_error, invalid_error=invalid_error
        ),
    )


def nested_field(
    nested_schema: type[m.Schema] | collections.abc.Callable[[], type[m.Schema]],
    *,
    required: bool,
    allow_none: bool,
    default: Any = dataclasses.MISSING,
    name: str | None = None,
    validate: ValidationFunc | collections.abc.Sequence[ValidationFunc] | None = None,
    required_error: str | None = None,
    none_error: str | None = None,
    invalid_error: str | None = None,
    description: str | None = None,
    **_: Any,
) -> m.fields.Field:
    if default is m.missing:
        return NestedField(
            nested_schema,
            allow_none=allow_none,
            validate=validate,
            **default_fields(m.missing),
            **data_key_fields(name),
            **description_fields(description),
            error_messages=build_error_messages(
                required_error=required_error, none_error=none_error, invalid_error=invalid_error
            ),
        )

    if required:
        if default is None:
            raise ValueError("Default value cannot be none")
        return NestedField(
            nested_schema,
            required=True,
            allow_none=allow_none,
            validate=validate,
            **data_key_fields(name),
            **description_fields(description),
            error_messages=build_error_messages(
                required_error=required_error, none_error=none_error, invalid_error=invalid_error
            ),
        )

    return NestedField(
        nested_schema,
        allow_none=allow_none,
        validate=validate,
        **(default_fields(None) if default is dataclasses.MISSING else {}),
        **data_key_fields(name),
        **description_fields(description),
        error_messages=build_error_messages(
            required_error=required_error, none_error=none_error, invalid_error=invalid_error
        ),
    )


def list_field(
    field: m.fields.Field,
    *,
    required: bool,
    allow_none: bool,
    default: Any = dataclasses.MISSING,
    name: str | None = None,
    validate: ValidationFunc | collections.abc.Sequence[ValidationFunc] | None = None,
    required_error: str | None = None,
    none_error: str | None = None,
    invalid_error: str | None = None,
    description: str | None = None,
    **_: Any,
) -> m.fields.Field:
    if default is m.missing:
        return m.fields.List(
            field,
            allow_none=allow_none,
            validate=validate,
            **default_fields(m.missing),
            **data_key_fields(name),
            **description_fields(description),
            error_messages=build_error_messages(
                required_error=required_error, none_error=none_error, invalid_error=invalid_error
            ),
        )

    if required:
        if default is None:
            raise ValueError("Default value cannot be none")
        return m.fields.List(
            field,
            required=True,
            allow_none=allow_none,
            validate=validate,
            **data_key_fields(name),
            **description_fields(description),
            error_messages=build_error_messages(
                required_error=required_error, none_error=none_error, invalid_error=invalid_error
            ),
        )

    return m.fields.List(
        field,
        allow_none=allow_none,
        validate=validate,
        **(default_fields(None) if default is dataclasses.MISSING else {}),
        **data_key_fields(name),
        **description_fields(description),
        error_messages=build_error_messages(
            required_error=required_error, none_error=none_error, invalid_error=invalid_error
        ),
    )


def set_field(
    field: m.fields.Field,
    *,
    required: bool,
    allow_none: bool,
    default: Any = dataclasses.MISSING,
    name: str | None = None,
    validate: ValidationFunc | collections.abc.Sequence[ValidationFunc] | None = None,
    required_error: str | None = None,
    none_error: str | None = None,
    invalid_error: str | None = None,
    description: str | None = None,
    **_: Any,
) -> m.fields.Field:
    if default is m.missing:
        return SetField(
            field,
            allow_none=allow_none,
            validate=validate,
            **default_fields(m.missing),
            **data_key_fields(name),
            **description_fields(description),
            error_messages=build_error_messages(
                required_error=required_error, none_error=none_error, invalid_error=invalid_error
            ),
        )

    if required:
        if default is None:
            raise ValueError("Default value cannot be none")
        return SetField(
            field,
            required=True,
            allow_none=allow_none,
            validate=validate,
            **data_key_fields(name),
            **description_fields(description),
            error_messages=build_error_messages(
                required_error=required_error, none_error=none_error, invalid_error=invalid_error
            ),
        )

    return SetField(
        field,
        allow_none=allow_none,
        validate=validate,
        **(default_fields(None) if default is dataclasses.MISSING else {}),
        **data_key_fields(name),
        **description_fields(description),
        error_messages=build_error_messages(
            required_error=required_error, none_error=none_error, invalid_error=invalid_error
        ),
    )


def frozen_set_field(
    field: m.fields.Field,
    *,
    required: bool,
    allow_none: bool,
    default: Any = dataclasses.MISSING,
    name: str | None = None,
    validate: ValidationFunc | collections.abc.Sequence[ValidationFunc] | None = None,
    required_error: str | None = None,
    none_error: str | None = None,
    invalid_error: str | None = None,
    description: str | None = None,
    **_: Any,
) -> m.fields.Field:
    if default is m.missing:
        return FrozenSetField(
            field,
            allow_none=allow_none,
            validate=validate,
            **default_fields(m.missing),
            **data_key_fields(name),
            **description_fields(description),
            error_messages=build_error_messages(
                required_error=required_error, none_error=none_error, invalid_error=invalid_error
            ),
        )

    if required:
        if default is None:
            raise ValueError("Default value cannot be none")
        return FrozenSetField(
            field,
            required=True,
            allow_none=allow_none,
            validate=validate,
            **data_key_fields(name),
            **description_fields(description),
            error_messages=build_error_messages(
                required_error=required_error, none_error=none_error, invalid_error=invalid_error
            ),
        )

    return FrozenSetField(
        field,
        allow_none=allow_none,
        validate=validate,
        **(default_fields(None) if default is dataclasses.MISSING else {}),
        **data_key_fields(name),
        **description_fields(description),
        error_messages=build_error_messages(
            required_error=required_error, none_error=none_error, invalid_error=invalid_error
        ),
    )


def tuple_field(
    field: m.fields.Field,
    *,
    required: bool,
    allow_none: bool,
    default: Any = dataclasses.MISSING,
    name: str | None = None,
    validate: ValidationFunc | collections.abc.Sequence[ValidationFunc] | None = None,
    required_error: str | None = None,
    none_error: str | None = None,
    invalid_error: str | None = None,
    description: str | None = None,
    **_: Any,
) -> m.fields.Field:
    if default is m.missing:
        return TupleField(
            field,
            allow_none=allow_none,
            validate=validate,
            **default_fields(m.missing),
            **data_key_fields(name),
            **description_fields(description),
            error_messages=build_error_messages(
                required_error=required_error, none_error=none_error, invalid_error=invalid_error
            ),
        )

    if required:
        if default is None:
            raise ValueError("Default value cannot be none")
        return TupleField(
            field,
            required=True,
            allow_none=allow_none,
            validate=validate,
            **data_key_fields(name),
            **description_fields(description),
            error_messages=build_error_messages(
                required_error=required_error, none_error=none_error, invalid_error=invalid_error
            ),
        )

    return TupleField(
        field,
        allow_none=allow_none,
        validate=validate,
        **(default_fields(None) if default is dataclasses.MISSING else {}),
        **data_key_fields(name),
        **description_fields(description),
        error_messages=build_error_messages(
            required_error=required_error, none_error=none_error, invalid_error=invalid_error
        ),
    )


def dict_field(
    keys_field: m.fields.Field | None,
    values_field: m.fields.Field | None,
    *,
    required: bool,
    allow_none: bool,
    default: Any = dataclasses.MISSING,
    name: str | None = None,
    validate: ValidationFunc | collections.abc.Sequence[ValidationFunc] | None = None,
    required_error: str | None = None,
    none_error: str | None = None,
    invalid_error: str | None = None,
    description: str | None = None,
    **_: Any,
) -> m.fields.Field:
    if default is m.missing:
        return DictField(
            keys=keys_field,
            values=values_field,
            allow_none=allow_none,
            validate=validate,
            **default_fields(m.missing),
            **data_key_fields(name),
            **description_fields(description),
            error_messages=build_error_messages(
                required_error=required_error, none_error=none_error, invalid_error=invalid_error
            ),
        )

    if required:
        if default is None:
            raise ValueError("Default value cannot be none")
        return DictField(
            keys=keys_field,
            values=values_field,
            required=True,
            allow_none=allow_none,
            validate=validate,
            **data_key_fields(name),
            **description_fields(description),
            error_messages=build_error_messages(
                required_error=required_error, none_error=none_error, invalid_error=invalid_error
            ),
        )

    return DictField(
        keys=keys_field,
        values=values_field,
        allow_none=allow_none,
        validate=validate,
        **(default_fields(None) if default is dataclasses.MISSING else {}),
        **data_key_fields(name),
        **description_fields(description),
        error_messages=build_error_messages(
            required_error=required_error, none_error=none_error, invalid_error=invalid_error
        ),
    )


def enum_field(
    enum_type: type[enum.Enum],
    *,
    required: bool,
    allow_none: bool,
    name: str | None = None,
    default: Any = dataclasses.MISSING,
    validate: ValidationFunc | collections.abc.Sequence[ValidationFunc] | None = None,
    required_error: str | None = None,
    none_error: str | None = None,
    invalid_error: str | None = None,
    description: str | None = None,
    **_: Any,
) -> marshmallow.fields.Field:
    if default is m.missing:
        return EnumField(
            enum_type=enum_type,
            allow_none=allow_none,
            validate=validate,
            **default_fields(m.missing),
            **data_key_fields(name),
            **description_fields(description),
            error_messages=build_error_messages(
                required_error=required_error, none_error=none_error, invalid_error=invalid_error
            ),
        )

    if required:
        if default is None:
            raise ValueError("Default value cannot be none")
        return EnumField(
            enum_type=enum_type,
            required=True,
            allow_none=allow_none,
            validate=validate,
            **data_key_fields(name),
            **description_fields(description),
            error_messages=build_error_messages(
                required_error=required_error, none_error=none_error, invalid_error=invalid_error
            ),
        )

    return EnumField(
        enum_type=enum_type,
        allow_none=allow_none,
        validate=validate,
        **(default_fields(None) if default is dataclasses.MISSING else {}),
        **data_key_fields(name),
        **description_fields(description),
        error_messages=build_error_messages(
            required_error=required_error, none_error=none_error, invalid_error=invalid_error
        ),
    )


def raw_field(
    *,
    default: Any = dataclasses.MISSING,
    name: str | None = None,
    validate: ValidationFunc | collections.abc.Sequence[ValidationFunc] | None = None,
    required_error: str | None = None,
    none_error: str | None = None,
    invalid_error: str | None = None,
    description: str | None = None,
    **_: Any,
) -> m.fields.Field:
    return JsonRawField(
        allow_none=True,
        validate=validate,
        **(default_fields(None) if default is dataclasses.MISSING else {}),
        **data_key_fields(name),
        **description_fields(description),
        error_messages=build_error_messages(
            required_error=required_error, none_error=none_error, invalid_error=invalid_error
        ),
    )


def union_field(
    fields: list[m.fields.Field],
    *,
    required: bool,
    allow_none: bool,
    default: Any = dataclasses.MISSING,
    name: str | None = None,
    validate: ValidationFunc | collections.abc.Sequence[ValidationFunc] | None = None,
    required_error: str | None = None,
    none_error: str | None = None,
    invalid_error: str | None = None,
    description: str | None = None,
    **_: Any,
) -> m.fields.Field:
    if default is m.missing:
        return UnionField(
            fields=fields,
            allow_none=allow_none,
            validate=validate,
            **default_fields(m.missing),
            **data_key_fields(name),
            **description_fields(description),
            error_messages=build_error_messages(
                required_error=required_error, none_error=none_error, invalid_error=invalid_error
            ),
        )

    if required:
        if default is None:
            raise ValueError("Default value cannot be none")
        return UnionField(
            fields=fields,
            required=True,
            allow_none=allow_none,
            validate=validate,
            **data_key_fields(name),
            **description_fields(description),
            error_messages=build_error_messages(
                required_error=required_error, none_error=none_error, invalid_error=invalid_error
            ),
        )

    return UnionField(
        fields=fields,
        allow_none=allow_none,
        validate=validate,
        **(default_fields(None) if default is dataclasses.MISSING else {}),
        **data_key_fields(name),
        **description_fields(description),
        error_messages=build_error_messages(
            required_error=required_error, none_error=none_error, invalid_error=invalid_error
        ),
    )


DateTimeField: type[m.fields.Field]
DateField: type[m.fields.Date]
DecimalField: type[m.fields.Decimal]
EnumField: type[m.fields.Field]
DictField: type[m.fields.Field]
SetField: type[m.fields.List]
FrozenSetField: type[m.fields.List]
TupleField: type[m.fields.List]
StrField: type[m.fields.Str]
UnionField: type[m.fields.Field]
JsonRawField: type[m.fields.Raw]


def build_error_messages(
    *, required_error: str | None = None, none_error: str | None = None, invalid_error: str | None = None
) -> dict[str, str] | None:
    error_messages = {}
    if required_error is not None:
        error_messages["required"] = required_error
    if none_error is not None:
        error_messages["null"] = none_error
    if invalid_error is not None:
        error_messages["invalid"] = invalid_error

    return error_messages if error_messages else None


def build_uuid_error_messages(
    *, required_error: str | None = None, none_error: str | None = None, invalid_error: str | None = None
) -> dict[str, str] | None:
    error_messages = {}
    if required_error is not None:
        error_messages["required"] = required_error
    if none_error is not None:
        error_messages["null"] = none_error
    if invalid_error is not None:
        error_messages["invalid_uuid"] = invalid_error

    return error_messages if error_messages else None


if _MARSHMALLOW_VERSION_MAJOR >= 3:

    def with_type_checks_on_serialize_v3[TField: m.fields.Field](
        field: TField, type_guards: type | tuple[type, ...], type_guards_to_exclude: type | tuple[type, ...] = ()
    ) -> TField:
        fail_key = "invalid" if "invalid" in field.default_error_messages else "validator_failed"
        invalid_msg = str(field.default_error_messages.get("invalid", ""))
        obj_type = getattr(field, "OBJ_TYPE", None) if "{obj_type}" in invalid_msg else None

        old = field._serialize  # type: ignore

        def _serialize_with_validate(self: TField, value: Any, attr: Any, obj: Any, **kwargs: Any) -> Any:
            if value is not None and not (
                isinstance(value, type_guards) and not isinstance(value, type_guards_to_exclude)
            ):
                if obj_type is not None:
                    raise self.make_error(fail_key, obj_type=obj_type)  # type: ignore
                raise self.make_error(fail_key)  # type: ignore
            return old(value, attr, obj, **kwargs)

        field._serialize = types.MethodType(_serialize_with_validate, field)  # type: ignore

        return field

    with_type_checks_on_serialize = with_type_checks_on_serialize_v3

    def with_type_checks_on_validated_v3[TField: m.fields.Field](
        field: TField, type_guards: type | tuple[type, ...]
    ) -> TField:
        if not hasattr(field, "_validated"):
            raise TypeError("Field doesn't have _validated method")

        fail_key = "invalid" if "invalid" in field.default_error_messages else "validator_failed"

        old = field._validated  # type: ignore

        def _validated(self: TField, value: Any) -> Any:
            if not isinstance(value, type_guards):
                raise self.make_error(fail_key)  # type: ignore
            return old(value)

        field._validated = types.MethodType(_validated, field)  # type: ignore

        return field

    with_type_checks_on_validated = with_type_checks_on_validated_v3

    def data_key_fields(name: str | None) -> collections.abc.Mapping[str, Any]:
        if name is None:
            return {}
        return {"data_key": name}

    def default_fields(value: Any) -> collections.abc.Mapping[str, Any]:
        return {"dump_default": value, "load_default": value}

    def description_fields(description: str | None) -> collections.abc.Mapping[str, Any]:
        if description is None:
            return {}
        return {"metadata": {"description": description}}

    class StrFieldV3(m.fields.Str):
        def __init__(
            self,
            strip_whitespaces: bool = False,
            post_load: collections.abc.Callable[[str], str] | None = None,
            **kwargs: Any,
        ):
            super().__init__(**kwargs)
            self.post_load = post_load
            self.strip_whitespaces = strip_whitespaces

        def _serialize(self, value: Any, attr: Any, obj: Any, **kwargs: Any) -> Any:
            result = super()._serialize(value, attr, obj, **kwargs)
            if self.strip_whitespaces and result is not None:
                result = result.strip()
                if self.allow_none and len(result) == 0:
                    result = None
            return result

        def _deserialize(self, value: Any, attr: Any, data: Any, **kwargs: Any) -> Any:
            result = super()._deserialize(value, attr, data, **kwargs)
            if result is not None:  # type: ignore
                if self.strip_whitespaces:
                    result = result.strip()
                    if self.allow_none and len(result) == 0:
                        return None

                if self.post_load is not None:
                    result = self.post_load(result)

            return result

        def _validate(self, value: Any) -> None:
            if self.allow_none and value is None:
                return
            super()._validate(value)

    StrField = StrFieldV3

    class FloatFieldV3(m.fields.Float):
        def _format_num(self, value: Any) -> float | int:
            if isinstance(value, int):
                return value
            return super()._format_num(value)

    FloatField = FloatFieldV3

    class DecimalFieldV3(m.fields.Decimal):
        def __init__(
            self,
            places: int | None = None,
            rounding: str | None = None,
            validate: ValidationFunc | collections.abc.Sequence[ValidationFunc] | None = None,
            **kwargs: Any,
        ):
            if places is not None and rounding is None:
                local_places = places

                def places_validator(value: decimal.Decimal) -> None:
                    _, _, exponent = value.normalize().as_tuple()
                    if isinstance(exponent, int) and exponent < 0 and -exponent > local_places:
                        raise self.make_error("invalid")

                validate = combine_validators(validate, places_validator)
                places = None

            super().__init__(places=places, rounding=rounding, validate=validate, **kwargs)

    DecimalField = DecimalFieldV3

    class DateTimeFieldV3(m.fields.DateTime):
        SERIALIZATION_FUNCS = {  # noqa: RUF012
            "iso": datetime.datetime.isoformat,
            "timestamp": m.fields.DateTime.SERIALIZATION_FUNCS["timestamp"],  # type: ignore
        }

        DESERIALIZATION_FUNCS = {  # noqa: RUF012
            "iso": datetime.datetime.fromisoformat,
            "timestamp": m.fields.DateTime.DESERIALIZATION_FUNCS["timestamp"],  # type: ignore
        }

        def _deserialize(self, value: Any, attr: Any, data: Any, **kwargs: Any) -> Any:
            result = super()._deserialize(value, attr, data, **kwargs)
            if result.tzinfo is None:
                return result.replace(tzinfo=datetime.UTC)
            if result.tzinfo == datetime.UTC:
                return result
            return result.astimezone(datetime.UTC)

        def _serialize(self, value: Any, attr: Any, obj: Any, **kwargs: Any) -> Any:
            if value is None:
                return None

            if value.tzinfo is None:
                value = value.replace(tzinfo=datetime.UTC)

            return super()._serialize(value, attr, obj, **kwargs)

    DateTimeField = DateTimeFieldV3

    class DateFieldV3(m.fields.Date):
        def _serialize(self, value: Any, attr: Any, obj: Any, **kwargs: Any) -> Any:
            if isinstance(value, datetime.datetime):
                value = value.date()
            return super()._serialize(value, attr, obj, **kwargs)

    DateField = DateFieldV3

    class SetFieldV3(m.fields.List):
        default_error_messages = {"invalid": "Not a valid set."}  # noqa: RUF012

        def _deserialize(self, value: Any, attr: Any, data: Any, **kwargs: Any) -> Any:
            result = super()._deserialize(value, attr, data, **kwargs)
            return None if None else set(result)

    SetField = SetFieldV3

    class FrozenSetFieldV3(m.fields.List):
        default_error_messages = {"invalid": "Not a valid frozenset."}  # noqa: RUF012

        def _deserialize(self, value: Any, attr: Any, data: Any, **kwargs: Any) -> Any:
            result = super()._deserialize(value, attr, data, **kwargs)
            return None if None else frozenset(result)

    FrozenSetField = FrozenSetFieldV3

    class TupleFieldV3(m.fields.List):
        default_error_messages = {"invalid": "Not a valid tuple."}  # noqa: RUF012

        def _deserialize(self, value: Any, attr: Any, data: Any, **kwargs: Any) -> Any:
            result = super()._deserialize(value, attr, data, **kwargs)
            return None if None else tuple(result)

    TupleField = TupleFieldV3

    class EnumFieldV3(m.fields.Field):
        default_error_messages = {"invalid": "Not a valid enum."}  # noqa: RUF012

        def __init__(self, *args: Any, enum_type: type[enum.Enum], **kwargs: Any):
            self.enum_type = enum_type
            super().__init__(*args, **kwargs)

        def _validated(self, value: Any) -> Any:
            if value is None:
                return None
            if isinstance(value, bool):
                raise self.make_error("invalid")
            if isinstance(value, self.enum_type):
                return value
            try:
                return self.enum_type(value)
            except (ValueError, KeyError):
                raise self.make_error("invalid")

        def _serialize(self, value: Any, attr: Any, obj: Any, **kwargs: Any) -> Any:
            if value is None:
                return None
            return value.value

        def _deserialize(self, value: Any, attr: Any, data: Any, **kwargs: Any) -> Any:
            return self._validated(value)

    EnumField = EnumFieldV3

    class DictFieldV3(m.fields.Dict):
        default_error_messages = {"invalid": "Not a valid dict."}  # noqa: RUF012

    DictField = DictFieldV3

    class UnionFieldV3(m.fields.Field):
        def __init__(self, fields: list[m.fields.Field], **kwargs: Any):
            self.fields = fields
            super().__init__(**kwargs)

        def _serialize(self, value: Any, attr: Any, obj: Any, **kwargs: Any) -> Any:
            errors = []
            for field in self.fields:
                try:
                    return field._serialize(value, attr, obj, **kwargs)
                except m.ValidationError as e:
                    errors.append(e.messages)
            raise m.ValidationError(message=errors, field_name=attr)

        def _deserialize(self, value: Any, attr: Any, data: Any, **kwargs: Any) -> Any:
            errors = []
            for field in self.fields:
                try:
                    return field.deserialize(value, attr, data, **kwargs)
                except m.ValidationError as exc:
                    errors.append(exc.messages)
            raise m.ValidationError(message=errors, field_name=attr)

    UnionField = UnionFieldV3

    NestedField = m.fields.Nested

    class JsonRawFieldV3(m.fields.Raw):
        default_error_messages = {"invalid": "Not a valid JSON-serializable value."}  # noqa: RUF012

        def _validate(self, value: Any) -> None:
            if self.allow_none and value is None:
                return
            super()._validate(value)
            self.__validate_json_serializable(value)

        def __validate_json_serializable(self, value: Any) -> None:
            stack = [value]
            while stack:
                v = stack.pop()
                if v is None or isinstance(v, bool | str | int):
                    continue
                if isinstance(v, float) and not math.isnan(v) and v != float("inf") and v != float("-inf"):
                    continue
                if isinstance(v, list):
                    stack.extend(v)
                    continue
                if isinstance(v, dict):
                    for k, val in v.items():
                        if not isinstance(k, str):
                            raise self.make_error("invalid")
                        stack.append(val)
                    continue
                raise self.make_error("invalid")

    JsonRawField = JsonRawFieldV3
else:

    def with_type_checks_on_serialize_v2[TField: m.fields.Field](
        field: TField, type_guards: type | tuple[type, ...], type_guards_to_exclude: type | tuple[type, ...] = ()
    ) -> TField:
        fail_key = "invalid" if "invalid" in field.default_error_messages else "validator_failed"

        old = field._serialize  # type: ignore

        def _serialize_with_validate(self: TField, value: Any, attr: Any, obj: Any, **kwargs: Any) -> Any:
            if value is not None and not (
                isinstance(value, type_guards) and not isinstance(value, type_guards_to_exclude)
            ):
                self.fail(fail_key)  # type: ignore
            return old(value, attr, obj, **kwargs)

        field._serialize = types.MethodType(_serialize_with_validate, field)  # type: ignore

        return field

    with_type_checks_on_serialize = with_type_checks_on_serialize_v2

    def with_type_checks_on_validated_v2[TField: m.fields.Field](
        field: TField, type_guards: type | tuple[type, ...]
    ) -> TField:
        if not hasattr(field, "_validated"):
            raise TypeError("Field doesn't have _validated method")

        fail_key = "invalid" if "invalid" in field.default_error_messages else "validator_failed"

        old = field._validated  # type: ignore

        def _validated(self: TField, value: Any) -> Any:
            if value not in (None, m.missing) and not isinstance(value, type_guards):
                raise self.fail(fail_key)  # type: ignore
            return old(value)

        field._validated = types.MethodType(_validated, field)  # type: ignore

        return field

    with_type_checks_on_validated = with_type_checks_on_validated_v2

    dateutil_tz_utc_cls: type[datetime.tzinfo] | None
    try:
        import dateutil.tz  # type: ignore

        dateutil_tz_utc_cls = dateutil.tz.tzutc
    except ImportError:
        dateutil_tz_utc_cls = None

    def data_key_fields(name: str | None) -> collections.abc.Mapping[str, Any]:
        if name is None:
            return {}
        return {"dump_to": name, "load_from": name}

    def default_fields(value: Any) -> collections.abc.Mapping[str, Any]:
        return {"missing": value, "default": value}

    def description_fields(description: str | None) -> collections.abc.Mapping[str, Any]:
        if description is None:
            return {}
        return {"description": description}

    class StrFieldV2(m.fields.Str):
        def __init__(
            self,
            strip_whitespaces: bool = False,
            post_load: collections.abc.Callable[[str], str] | None = None,
            **kwargs: Any,
        ):
            super().__init__(**kwargs)
            self.post_load = post_load
            self.strip_whitespaces = strip_whitespaces

        def _serialize(self, value: Any, attr: Any, obj: Any, **_: Any) -> Any:
            result = super()._serialize(value, attr, obj)
            if self.strip_whitespaces and result is not None:
                result = result.strip()
                if self.allow_none and len(result) == 0:
                    result = None
            return result

        def _deserialize(self, value: Any, attr: Any, data: Any, **_: Any) -> Any:
            result = super()._deserialize(value, attr, data)

            if result is not None:  # type: ignore
                if self.strip_whitespaces:
                    result = result.strip()
                    if self.allow_none and len(result) == 0:
                        return None

                if self.post_load is not None:
                    result = self.post_load(result)

            return result

        def _validate(self, value: Any) -> None:
            if self.allow_none and value is None:
                return
            super()._validate(value)

    StrField = StrFieldV2

    class FloatFieldV2(m.fields.Float):
        default_error_messages = {  # noqa: RUF012
            **m.fields.Float.default_error_messages,
            "special": "Special numeric values (nan or infinity) are not permitted.",
        }

        def _validated(self, value: Any) -> float:
            num = super()._validated(value)
            if num is not None and (math.isnan(num) or num == float("inf") or num == float("-inf")):  # type: ignore[reportUnnecessaryComparison]
                self.fail("special")
            return num

        def _format_num(self, value: Any) -> float | int:
            if isinstance(value, int):
                return value
            return super()._format_num(value)

    FloatField = FloatFieldV2

    class DecimalFieldV2(m.fields.Decimal):
        def __init__(
            self,
            places: int | None = None,
            rounding: str | None = None,
            validate: ValidationFunc | collections.abc.Sequence[ValidationFunc] | None = None,
            **kwargs: Any,
        ):
            if places is not None and rounding is None:
                local_places = places

                def places_validator(value: decimal.Decimal) -> None:
                    _, _, exponent = value.normalize().as_tuple()
                    if isinstance(exponent, int) and exponent < 0 and -exponent > local_places:
                        self.fail("invalid")

                validate = combine_validators(validate, places_validator)
                places = None

            super().__init__(places=places, rounding=rounding, validate=validate, **kwargs)

    DecimalField = DecimalFieldV2

    class DateTimeFieldV2(m.fields.Field):
        @staticmethod
        def __iso_serialize(v: datetime.datetime) -> str:  # type: ignore
            return datetime.datetime.isoformat(v)

        @staticmethod
        def __timestamp_serialize(v: datetime.datetime) -> float:  # type: ignore
            return v.timestamp()

        @staticmethod
        def __timestamp_deserialize(value: Any) -> datetime.datetime:
            if isinstance(value, bool) or not isinstance(value, float | int):
                raise TypeError("argument must be number")
            if value < 0:
                raise ValueError("Not a valid POSIX timestamp")

            return datetime.datetime.fromtimestamp(value, tz=datetime.UTC)

        DATEFORMAT_SERIALIZATION_FUNCS = {  # noqa: RUF012
            "iso": __iso_serialize,
            "timestamp": __timestamp_serialize,
        }

        DATEFORMAT_DESERIALIZATION_FUNCS = {  # noqa: RUF012
            "iso": datetime.datetime.fromisoformat,
            "timestamp": __timestamp_deserialize,
        }

        localtime = False
        default_error_messages = {  # noqa: RUF012
            "invalid": "Not a valid datetime.",
            "format": '"{input}" cannot be formatted as a datetime.',
        }

        def __init__(self, format: str | None = None, **kwargs: Any):
            super().__init__(**kwargs)
            self.format = format or "iso"

        def _add_to_schema(self, field_name: str, schema: Any) -> None:
            super()._add_to_schema(field_name, schema)  # type: ignore[misc]

        def _serialize(self, value: Any, attr: Any, obj: Any, **kwargs: Any) -> Any:
            if value is None:
                return None
            if value.tzinfo is None:
                value = value.replace(tzinfo=datetime.UTC)
            format_func = self.DATEFORMAT_SERIALIZATION_FUNCS.get(self.format, None)
            if format_func:
                try:
                    return format_func(value)
                except (AttributeError, ValueError):
                    self.fail("format", input=value)
            else:
                try:
                    return value.strftime(self.format)
                except (AttributeError, ValueError):
                    self.fail("format", input=value)

        def _deserialize(self, value: Any, attr: Any, data: Any, **_: Any) -> Any:
            if value is None:
                raise self.fail("invalid")
            func = self.DATEFORMAT_DESERIALIZATION_FUNCS.get(self.format)
            if func:
                try:
                    result = func(value)
                except (TypeError, AttributeError, ValueError):
                    raise self.fail("invalid")
            else:
                try:
                    result = datetime.datetime.strptime(value, self.format)
                except (TypeError, AttributeError, ValueError):
                    raise self.fail("invalid")

            if result.tzinfo is None:
                return result.replace(tzinfo=datetime.UTC)
            if result.tzinfo == datetime.UTC:
                return result
            if dateutil_tz_utc_cls is not None and isinstance(result.tzinfo, dateutil_tz_utc_cls):
                return result.replace(tzinfo=datetime.UTC)
            return result.astimezone(datetime.UTC)

    DateTimeField = DateTimeFieldV2

    class DateFieldV2(m.fields.Date):
        def _serialize(self, value: Any, attr: Any, obj: Any, **kwargs: Any) -> Any:
            if isinstance(value, datetime.datetime):
                value = value.date()
            return super()._serialize(value, attr, obj, **kwargs)

    DateField = DateFieldV2

    class SetFieldV2(m.fields.List):
        default_error_messages = {"invalid": "Not a valid set."}  # noqa: RUF012

        def _deserialize(self, value: Any, attr: Any, data: Any, **_: Any) -> Any:
            result = super()._deserialize(value, attr, data)
            return None if None else set(result)

    SetField = SetFieldV2

    class FrozenSetFieldV2(m.fields.List):
        default_error_messages = {"invalid": "Not a valid frozenset."}  # noqa: RUF012

        def _deserialize(self, value: Any, attr: Any, data: Any, **_: Any) -> Any:
            result = super()._deserialize(value, attr, data)
            return None if None else frozenset(result)

    FrozenSetField = FrozenSetFieldV2

    class TupleFieldV2(m.fields.List):
        default_error_messages = {"invalid": "Not a valid tuple."}  # noqa: RUF012

        def _deserialize(self, value: Any, attr: Any, data: Any, **_: Any) -> Any:
            result = super()._deserialize(value, attr, data)
            return None if None else tuple(result)

    TupleField = TupleFieldV2

    class EnumFieldV2(m.fields.Field):
        default_error_messages = {"invalid": "Not a valid enum."}  # noqa: RUF012

        def __init__(self, *args: Any, enum_type: type[enum.Enum], **kwargs: Any):
            self.enum_type = enum_type
            super().__init__(*args, **kwargs)

        def _validated(self, value: Any) -> Any:
            if value is None:
                return None
            if isinstance(value, bool):
                self.fail("invalid")
            if isinstance(value, self.enum_type):
                return value
            try:
                return self.enum_type(value)
            except (ValueError, KeyError):
                self.fail("invalid")

        def _serialize(self, value: Any, attr: Any, obj: Any, **kwargs: Any) -> Any:
            if value is None:
                return None
            return value.value

        def _deserialize(self, value: Any, attr: Any, data: Any, **kwargs: Any) -> Any:
            return self._validated(value)

    EnumField = EnumFieldV2

    class TypedDict(m.fields.Field):
        default_error_messages = {"invalid": "Not a valid dict."}  # noqa: RUF012

        def __init__(
            self, keys: m.fields.Field | None = None, values: m.fields.Field | None = None, *args: Any, **kwargs: Any
        ):
            self.keys = keys
            self.values = values
            super().__init__(*args, **kwargs)

        def _serialize(self, value: Any, attr: Any, obj: Any, **kwargs: Any) -> Any:
            if value is None:
                return None
            if self.values is None and self.keys is None:
                return value

            if self.keys is None:
                keys = {k: k for k in value}
            else:
                keys = {k: self.keys._serialize(k, None, None, **kwargs) for k in value}

            result = {}
            if self.values is None:
                for k, v in value.items():
                    if k in keys:
                        result[keys[k]] = v
            else:
                for k, v in value.items():
                    result[keys[k]] = self.values._serialize(v, None, None, **kwargs)

            return result

        def _deserialize(self, value: Any, attr: Any, data: Any, **kwargs: Any) -> Any:
            if not isinstance(value, dict):
                self.fail("invalid")

            if self.keys is None and self.values is None:
                return value

            errors = collections.defaultdict(dict)  # type: ignore

            if self.keys is None:
                keys = {k: k for k in value}
            else:
                keys = {}
                for key in value:
                    try:
                        keys[key] = self.keys.deserialize(key, **kwargs)
                    except m.ValidationError as error:
                        errors[key]["key"] = error.messages

            result = {}
            if self.values is None:
                for k, v in value.items():
                    if k in keys:
                        result[keys[k]] = v
            else:
                for key, val in value.items():
                    try:
                        deserialized_value = self.values.deserialize(val, **kwargs)
                    except m.ValidationError as error:
                        errors[key]["value"] = error.messages
                        if error.data is not None and key in keys:
                            result[keys[key]] = error.data
                    else:
                        if key in keys:
                            result[keys[key]] = deserialized_value

            if errors:
                raise m.ValidationError(errors, data=result)

            return result

    DictField = TypedDict

    class UnionFieldV2(m.fields.Field):
        def __init__(self, fields: list[m.fields.Field], **kwargs: Any):
            self.fields = fields
            super().__init__(**kwargs)

        def _serialize(self, value: Any, attr: Any, obj: Any, **kwargs: Any) -> Any:
            errors = []
            for field in self.fields:
                try:
                    return field._serialize(value, attr, obj, **kwargs)
                except m.ValidationError as e:
                    errors.append(e.messages)
            raise m.ValidationError(message=errors, field_name=attr)

        def _deserialize(self, value: Any, attr: Any, data: Any, **kwargs: Any) -> Any:
            errors = []
            for field in self.fields:
                try:
                    return field.deserialize(value, attr, data, **kwargs)
                except m.ValidationError as exc:
                    errors.append(exc.messages)
            raise m.ValidationError(message=errors, field_name=attr)

    UnionField = UnionFieldV2

    class NestedFieldV2(m.fields.Nested):
        def __init__(self, nested: Any, **kwargs: Any):
            super().__init__(nested, **kwargs)

        def deserialize(self, value: Any, attr: str | None = None, data: Any = None, **kwargs: Any) -> Any:
            # v2 doesn't check required before _deserialize, so nested schema
            # validates its own fields. Match v3 behavior: check required first.
            if value is m.missing and self.required:
                self.fail("required")
            return super().deserialize(value, attr, data, **kwargs)

        @property
        def schema(self) -> Any:
            nested = self.nested
            if callable(nested) and not isinstance(nested, type):
                self.nested = nested()
            return super().schema

    NestedField = NestedFieldV2

    class JsonRawFieldV2(m.fields.Raw):
        default_error_messages = {"invalid": "Not a valid JSON-serializable value."}  # noqa: RUF012

        def _validate(self, value: Any) -> None:
            if self.allow_none and value is None:
                return
            super()._validate(value)
            self.__validate_json_serializable(value)

        def __validate_json_serializable(self, value: Any) -> None:
            stack = [value]
            while stack:
                v = stack.pop()
                if v is None or isinstance(v, bool | str | int):
                    continue
                if isinstance(v, float) and not math.isnan(v) and v != float("inf") and v != float("-inf"):
                    continue
                if isinstance(v, list):
                    stack.extend(v)
                    continue
                if isinstance(v, dict):
                    for k, val in v.items():
                        if not isinstance(k, str):
                            self.fail("invalid")
                        stack.append(val)
                    continue
                self.fail("invalid")

    JsonRawField = JsonRawFieldV2
