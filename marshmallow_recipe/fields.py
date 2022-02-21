import datetime
import decimal
import uuid
from typing import Any, Type

import marshmallow as m

from .missing import MISSING, Missing

_MARSHMALLOW_VERSION_MAJOR = int(m.__version__.split(".")[0])


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

        return m.fields.String(required=True, **data_key(name))

    return m.fields.Str(
        allow_none=True,
        missing=None if default is MISSING else default,
        default=None if default is MISSING else default,
        **data_key(name),
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

        return m.fields.Boolean(required=True, **data_key(name))

    return m.fields.Bool(
        allow_none=True,
        missing=None if default is MISSING else default,
        default=None if default is MISSING else default,
        **data_key(name),
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
        return m.fields.Decimal(required=True, as_string=as_string, places=places, **data_key(name))

    return m.fields.Decimal(
        allow_none=True,
        missing=None if default is MISSING else default,
        default=None if default is MISSING else default,
        as_string=as_string,
        places=places,
        **data_key(name),
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
        return m.fields.Int(required=True, **data_key(name))

    return m.fields.Int(
        allow_none=True,
        missing=None if default is MISSING else default,
        default=None if default is MISSING else default,
        **data_key(name),
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
        return m.fields.Float(required=True, **data_key(name))

    return m.fields.Float(
        allow_none=True,
        missing=None if default is MISSING else default,
        default=None if default is MISSING else default,
        **data_key(name),
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
        return m.fields.UUID(required=True, **data_key(name))

    return m.fields.UUID(
        allow_none=True,
        missing=None if default is MISSING else default,
        default=None if default is MISSING else default,
        **data_key(name),
    )


def datetime_field(
    *,
    required: bool,
    default: datetime.datetime | None | Missing = MISSING,
    name: str | None = None,
    **_: Any,
) -> m.fields.Field:
    if required:
        if default is not MISSING:
            raise ValueError("Default values is not supported for required fields")
        return DateTimeField(required=True, **data_key(name))

    return DateTimeField(
        allow_none=True,
        missing=None if default is MISSING else default,
        default=None if default is MISSING else default,
        **data_key(name),
    )


def date_field(
    *,
    required: bool,
    default: datetime.date | None | Missing = MISSING,
    name: str | None = None,
    **_: Any,
) -> m.fields.Field:
    if required:
        if default is not MISSING:
            raise ValueError("Default values is not supported for required fields")
        return m.fields.Date(required=True, **data_key(name))

    return m.fields.Date(
        allow_none=True,
        missing=None if default is MISSING else default,
        default=None if default is MISSING else default,
        **data_key(name),
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
        return m.fields.Nested(nested_schema, required=True, **data_key(name))

    if default is not MISSING and default is not None:
        raise ValueError("Default values is not supported for required fields")
    return m.fields.Nested(
        nested_schema,
        allow_none=True,
        missing=None,
        default=None,
        **data_key(name),
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
        return m.fields.List(field, required=True, **data_key(name))

    if default is not MISSING and default is not None:
        raise ValueError("Default values is not supported for required fields")
    return m.fields.List(
        field,
        allow_none=True,
        missing=None,
        default=None,
        **data_key(name),
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
        return m.fields.Dict(required=True, **data_key(name))

    if default is not MISSING and default is not None:
        raise ValueError("Default values is not supported for required fields")
    return m.fields.Dict(
        allow_none=True,
        missing=None,
        default=None,
        **data_key(name),
    )


DateTimeField: Type[m.fields.DateTime]

if _MARSHMALLOW_VERSION_MAJOR >= 3:

    def data_key(name: str | None) -> dict[str, Any]:
        if name is None:
            return {}
        return dict(data_key=name)

    class DateTimeFieldV3(m.fields.DateTime):
        def _deserialize(self, value: Any, attr: Any, data: Any, **kwargs: Any) -> Any:
            result = super()._deserialize(value, attr, data, **kwargs)
            if result.tzinfo is None:
                return result.replace(tzinfo=datetime.timezone.utc)
            return result.astimezone(datetime.timezone.utc)

        def _serialize(self, value: Any, attr: Any, obj: Any, **kwargs: Any) -> Any:
            if value is None:
                return None

            if value.tzinfo is None:
                value = value.replace(tzinfo=datetime.timezone.utc)

            return super()._serialize(value, attr, obj, **kwargs)

    DateTimeField = DateTimeFieldV3
else:
    dateutil_tz_utc_cls: Type[datetime.tzinfo] | None
    try:
        import dateutil.tz  # type: ignore

        dateutil_tz_utc_cls = dateutil.tz.tzutc
    except ImportError:
        dateutil_tz_utc_cls = None

    def data_key(name: str | None) -> dict[str, Any]:
        if name is None:
            return {}
        return dict(dump_to=name, load_from=name)

    class DateTimeFieldV2(m.fields.DateTime):
        def _deserialize(self, value: Any, attr: Any, data: Any, **_: Any) -> Any:
            result = super()._deserialize(value, attr, data)
            if result.tzinfo is None:
                return result.replace(tzinfo=datetime.timezone.utc)
            if dateutil_tz_utc_cls is not None and isinstance(result.tzinfo, dateutil_tz_utc_cls):
                return result.replace(tzinfo=datetime.timezone.utc)
            return result.astimezone(datetime.timezone.utc)

    DateTimeField = DateTimeFieldV2
