import dataclasses
import datetime
import decimal
import enum
import inspect
import unittest.mock
import uuid
from typing import Any, Dict, Optional

import marshmallow as m
import pytest

import marshmallow_recipe as mr
import marshmallow_recipe.fields

_MARSHMALLOW_VERSION_MAJOR = int(m.__version__.split(".")[0])


if _MARSHMALLOW_VERSION_MAJOR >= 3:

    def data_key_fields(name: str | None) -> dict[str, Any]:
        if name is None:
            return {}
        return dict(data_key=name)

    def default_fields(value: Any) -> dict[str, Any]:
        return dict(dump_default=value, load_default=value)

else:

    def data_key_fields(name: str | None) -> dict[str, Any]:
        if name is None:
            return {}
        return dict(dump_to=name, load_from=name)

    def default_fields(value: Any) -> dict[str, Any]:
        return dict(missing=value, default=value)


def assert_fields_equal(a: m.fields.Field, b: m.fields.Field) -> None:
    assert a.__class__ == b.__class__, "field class"

    def attrs(x: Any) -> dict[str, str]:
        return {
            k: f"{v!r} ({v.__mro__!r})" if inspect.isclass(v) else repr(v)
            for k, v in x.__dict__.items()
            if not k.startswith("_")
        }

    assert attrs(a) == attrs(b)


@dataclasses.dataclass
class EmptyDataclass:
    pass


class Enum(str, enum.Enum):
    pass


EMPTY = EmptyDataclass()
EMPTY_SCHEMA = m.Schema()


@pytest.mark.parametrize(
    "type, metadata, field",
    [
        # Any
        (Any, {}, m.fields.Raw(allow_none=True, **default_fields(None))),
        (Any, mr.metadata(name="i"), m.fields.Raw(allow_none=True, **default_fields(None), **data_key_fields("i"))),
        # simple types: bool
        (bool, {}, m.fields.Bool(required=True)),
        (Optional[bool], {}, m.fields.Bool(allow_none=True, **default_fields(None))),
        (bool | None, {}, m.fields.Bool(allow_none=True, **default_fields(None))),
        (bool, mr.metadata(name="i"), m.fields.Bool(required=True, **data_key_fields("i"))),
        (
            Optional[bool],
            mr.metadata(name="i"),
            m.fields.Bool(allow_none=True, **default_fields(None), **data_key_fields("i")),
        ),
        (
            bool | None,
            mr.metadata(name="i"),
            m.fields.Bool(allow_none=True, **default_fields(None), **data_key_fields("i")),
        ),
        # simple types: str
        (str, {}, m.fields.Str(required=True)),
        (Optional[str], {}, m.fields.Str(allow_none=True, **default_fields(None))),
        (str | None, {}, m.fields.Str(allow_none=True, **default_fields(None))),
        (str, mr.metadata(name="i"), m.fields.Str(required=True, **data_key_fields("i"))),
        (
            Optional[str],
            mr.metadata(name="i"),
            m.fields.Str(allow_none=True, **default_fields(None), **data_key_fields("i")),
        ),
        (
            str | None,
            mr.metadata(name="i"),
            m.fields.Str(allow_none=True, **default_fields(None), **data_key_fields("i")),
        ),
        # simple types: int
        (int, {}, m.fields.Int(required=True)),
        (Optional[int], {}, m.fields.Int(allow_none=True, **default_fields(None))),
        (int | None, {}, m.fields.Int(allow_none=True, **default_fields(None))),
        (int, mr.metadata(name="i"), m.fields.Int(required=True, **data_key_fields("i"))),
        (
            Optional[int],
            mr.metadata(name="i"),
            m.fields.Int(allow_none=True, **default_fields(None), **data_key_fields("i")),
        ),
        (
            int | None,
            mr.metadata(name="i"),
            m.fields.Int(allow_none=True, **default_fields(None), **data_key_fields("i")),
        ),
        # simple types: float
        (float, {}, m.fields.Float(required=True)),
        (Optional[float], {}, m.fields.Float(allow_none=True, **default_fields(None))),
        (float | None, {}, m.fields.Float(allow_none=True, **default_fields(None))),
        (float, mr.metadata(name="i"), m.fields.Float(required=True, **data_key_fields("i"))),
        (
            Optional[float],
            mr.metadata(name="i"),
            m.fields.Float(allow_none=True, **default_fields(None), **data_key_fields("i")),
        ),
        (
            float | None,
            mr.metadata(name="i"),
            m.fields.Float(allow_none=True, **default_fields(None), **data_key_fields("i")),
        ),
        # simple types: uuid
        (uuid.UUID, {}, m.fields.UUID(required=True)),
        (Optional[uuid.UUID], {}, m.fields.UUID(allow_none=True, **default_fields(None))),
        (uuid.UUID | None, {}, m.fields.UUID(allow_none=True, **default_fields(None))),
        (uuid.UUID, mr.metadata(name="i"), m.fields.UUID(required=True, **data_key_fields("i"))),
        (
            Optional[uuid.UUID],
            mr.metadata(name="i"),
            m.fields.UUID(allow_none=True, **default_fields(None), **data_key_fields("i")),
        ),
        (
            uuid.UUID | None,
            mr.metadata(name="i"),
            m.fields.UUID(allow_none=True, **default_fields(None), **data_key_fields("i")),
        ),
        # simple types: decimal
        (decimal.Decimal, {}, m.fields.Decimal(required=True, places=2, as_string=True)),
        (
            Optional[decimal.Decimal],
            {},
            m.fields.Decimal(allow_none=True, **default_fields(None), places=2, as_string=True),
        ),
        (
            decimal.Decimal | None,
            {},
            m.fields.Decimal(allow_none=True, **default_fields(None), places=2, as_string=True),
        ),
        (
            decimal.Decimal,
            mr.decimal_metadata(name="i", places=4, as_string=False),
            m.fields.Decimal(required=True, **data_key_fields("i"), places=4, as_string=False),
        ),
        (
            Optional[decimal.Decimal],
            mr.decimal_metadata(name="i", places=4, as_string=False),
            m.fields.Decimal(
                allow_none=True, **default_fields(None), places=4, as_string=False, **data_key_fields("i")
            ),
        ),
        (
            decimal.Decimal | None,
            mr.decimal_metadata(name="i", places=4, as_string=False),
            m.fields.Decimal(
                allow_none=True, **default_fields(None), places=4, as_string=False, **data_key_fields("i")
            ),
        ),
        # simple types: datetime
        (datetime.datetime, {}, mr.fields.DateTimeField(required=True)),
        (
            Optional[datetime.datetime],
            {},
            mr.fields.DateTimeField(allow_none=True, **default_fields(None)),
        ),
        (
            datetime.datetime | None,
            {},
            mr.fields.DateTimeField(allow_none=True, **default_fields(None)),
        ),
        (
            datetime.datetime,
            mr.metadata(name="i"),
            mr.fields.DateTimeField(required=True, **data_key_fields("i")),
        ),
        (
            Optional[datetime.datetime],
            mr.metadata(name="i"),
            mr.fields.DateTimeField(allow_none=True, **default_fields(None), **data_key_fields("i")),
        ),
        (
            datetime.datetime | None,
            mr.metadata(name="i"),
            mr.fields.DateTimeField(allow_none=True, **default_fields(None), **data_key_fields("i")),
        ),
        # simple types: date
        (datetime.date, {}, m.fields.Date(required=True)),
        (
            Optional[datetime.date],
            {},
            m.fields.Date(allow_none=True, **default_fields(None)),
        ),
        (
            datetime.date | None,
            {},
            m.fields.Date(allow_none=True, **default_fields(None)),
        ),
        (
            datetime.date,
            mr.metadata(name="i"),
            m.fields.Date(required=True, **data_key_fields("i")),
        ),
        (
            Optional[datetime.date],
            mr.metadata(name="i"),
            m.fields.Date(allow_none=True, **default_fields(None), **data_key_fields("i")),
        ),
        (
            datetime.date | None,
            mr.metadata(name="i"),
            m.fields.Date(allow_none=True, **default_fields(None), **data_key_fields("i")),
        ),
        # enum
        (Enum, {}, mr.fields.EnumField(enum_type=Enum, required=True)),
        (Optional[Enum], {}, mr.fields.EnumField(enum_type=Enum, allow_none=True, **default_fields(None))),
        (Enum | None, {}, mr.fields.EnumField(enum_type=Enum, allow_none=True, **default_fields(None))),
        (Enum, mr.metadata(name="i"), mr.fields.EnumField(enum_type=Enum, required=True, **data_key_fields("i"))),
        (
            Optional[Enum],
            mr.metadata(name="i"),
            mr.fields.EnumField(enum_type=Enum, allow_none=True, **default_fields(None), **data_key_fields("i")),
        ),
        (
            Enum | None,
            mr.metadata(name="i"),
            mr.fields.EnumField(enum_type=Enum, allow_none=True, **default_fields(None), **data_key_fields("i")),
        ),
        # dataclass
        (EmptyDataclass, {}, m.fields.Nested(EMPTY_SCHEMA, required=True)),
        (Optional[EmptyDataclass], {}, m.fields.Nested(EMPTY_SCHEMA, allow_none=True, **default_fields(None))),
        (EmptyDataclass | None, {}, m.fields.Nested(EMPTY_SCHEMA, allow_none=True, **default_fields(None))),
        (
            EmptyDataclass,
            mr.metadata(name="i"),
            m.fields.Nested(EMPTY_SCHEMA, required=True, **data_key_fields("i")),
        ),
        (
            Optional[EmptyDataclass],
            mr.metadata(name="i"),
            m.fields.Nested(EMPTY_SCHEMA, allow_none=True, **default_fields(None), **data_key_fields("i")),
        ),
        (
            EmptyDataclass | None,
            mr.metadata(name="i"),
            m.fields.Nested(EMPTY_SCHEMA, allow_none=True, **default_fields(None), **data_key_fields("i")),
        ),
        # containers: list[T]
        (list[bool], {}, m.fields.List(m.fields.Bool(required=True), required=True)),
        (
            list[Optional[bool]],
            {},
            m.fields.List(m.fields.Bool(allow_none=True, **default_fields(None)), required=True),
        ),
        (
            list[bool | None],
            {},
            m.fields.List(m.fields.Bool(allow_none=True, **default_fields(None)), required=True),
        ),
        (
            Optional[list[bool]],
            {},
            m.fields.List(m.fields.Bool(required=True), allow_none=True, **default_fields(None)),
        ),
        (
            Optional[list[Optional[bool]]],
            {},
            m.fields.List(
                m.fields.Bool(allow_none=True, **default_fields(None)), allow_none=True, **default_fields(None)
            ),
        ),
        (
            list[bool | None] | None,
            {},
            m.fields.List(
                m.fields.Bool(allow_none=True, **default_fields(None)), allow_none=True, **default_fields(None)
            ),
        ),
        # containers: list[T] where T: dataclass
        (list[EmptyDataclass], {}, m.fields.List(m.fields.Nested(EMPTY_SCHEMA, required=True), required=True)),
        (
            list[Optional[EmptyDataclass]],
            {},
            m.fields.List(m.fields.Nested(EMPTY_SCHEMA, allow_none=True, **default_fields(None)), required=True),
        ),
        (
            list[EmptyDataclass | None],
            {},
            m.fields.List(m.fields.Nested(EMPTY_SCHEMA, allow_none=True, **default_fields(None)), required=True),
        ),
        (
            Optional[list[EmptyDataclass]],
            {},
            m.fields.List(m.fields.Nested(EMPTY_SCHEMA, required=True), allow_none=True, **default_fields(None)),
        ),
        (
            Optional[list[Optional[EmptyDataclass]]],
            {},
            m.fields.List(
                m.fields.Nested(EMPTY_SCHEMA, allow_none=True, **default_fields(None)),
                allow_none=True,
                **default_fields(None),
            ),
        ),
        (
            list[EmptyDataclass | None] | None,
            {},
            m.fields.List(
                m.fields.Nested(EMPTY_SCHEMA, allow_none=True, **default_fields(None)),
                allow_none=True,
                **default_fields(None),
            ),
        ),
        # containers: Dict[str, Any]
        (dict[str, Any], {}, m.fields.Dict(required=True)),
        (
            dict[str, Any],
            mr.metadata(name="i"),
            m.fields.Dict(required=True, **data_key_fields("i")),
        ),
        (Optional[dict[str, Any]], {}, m.fields.Dict(allow_none=True, **default_fields(None))),
        (
            Optional[dict[str, Any]],
            mr.metadata(name="i"),
            m.fields.Dict(allow_none=True, **default_fields(None), **data_key_fields("i")),
        ),
        (dict[str, Any] | None, {}, m.fields.Dict(allow_none=True, **default_fields(None))),
        (
            dict[str, Any] | None,
            mr.metadata(name="i"),
            m.fields.Dict(allow_none=True, **default_fields(None), **data_key_fields("i")),
        ),
        (Dict[str, Any], {}, m.fields.Dict(required=True)),
        (
            Dict[str, Any],
            mr.metadata(name="i"),
            m.fields.Dict(required=True, **data_key_fields("i")),
        ),
        (Optional[Dict[str, Any]], {}, m.fields.Dict(allow_none=True, **default_fields(None))),
        (
            Optional[Dict[str, Any]],
            mr.metadata(name="i"),
            m.fields.Dict(allow_none=True, **default_fields(None), **data_key_fields("i")),
        ),
        (Dict[str, Any] | None, {}, m.fields.Dict(allow_none=True, **default_fields(None))),
        (
            Dict[str, Any] | None,
            mr.metadata(name="i"),
            m.fields.Dict(allow_none=True, **default_fields(None), **data_key_fields("i")),
        ),
    ],
)
def test_get_field_for(type: type, metadata: dict[str, Any], field: m.fields.Field) -> None:
    with unittest.mock.patch("marshmallow_recipe.bake.bake_schema") as bake_schema:
        bake_schema.return_value = EMPTY_SCHEMA
        assert_fields_equal(mr.get_field_for(type, metadata, naming_case=mr.DEFAULT_CASE), field)
