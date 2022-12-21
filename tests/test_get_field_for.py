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
        (Optional[bool], {}, m.fields.Bool(required=True, allow_none=True)),
        (bool | None, {}, m.fields.Bool(required=True, allow_none=True)),
        (bool, mr.metadata(name="i"), m.fields.Bool(required=True, **data_key_fields("i"))),
        (
            Optional[bool],
            mr.metadata(name="i"),
            m.fields.Bool(required=True, allow_none=True, **data_key_fields("i")),
        ),
        (
            bool | None,
            mr.metadata(name="i"),
            m.fields.Bool(required=True, allow_none=True, **data_key_fields("i")),
        ),
        # simple types: str
        (str, {}, m.fields.Str(required=True)),
        (Optional[str], {}, m.fields.Str(required=True, allow_none=True)),
        (str | None, {}, m.fields.Str(required=True, allow_none=True)),
        (str, mr.metadata(name="i"), m.fields.Str(required=True, **data_key_fields("i"))),
        (
            Optional[str],
            mr.metadata(name="i"),
            m.fields.Str(required=True, allow_none=True, **data_key_fields("i")),
        ),
        (
            str | None,
            mr.metadata(name="i"),
            m.fields.Str(required=True, allow_none=True, **data_key_fields("i")),
        ),
        # simple types: int
        (int, {}, m.fields.Int(required=True)),
        (Optional[int], {}, m.fields.Int(required=True, allow_none=True)),
        (int | None, {}, m.fields.Int(required=True, allow_none=True)),
        (int, mr.metadata(name="i"), m.fields.Int(required=True, **data_key_fields("i"))),
        (
            Optional[int],
            mr.metadata(name="i"),
            m.fields.Int(required=True, allow_none=True, **data_key_fields("i")),
        ),
        (
            int | None,
            mr.metadata(name="i"),
            m.fields.Int(required=True, allow_none=True, **data_key_fields("i")),
        ),
        # simple types: float
        (float, {}, m.fields.Float(required=True)),
        (Optional[float], {}, m.fields.Float(required=True, allow_none=True)),
        (float | None, {}, m.fields.Float(required=True, allow_none=True)),
        (float, mr.metadata(name="i"), m.fields.Float(required=True, **data_key_fields("i"))),
        (
            Optional[float],
            mr.metadata(name="i"),
            m.fields.Float(required=True, allow_none=True, **data_key_fields("i")),
        ),
        (
            float | None,
            mr.metadata(name="i"),
            m.fields.Float(required=True, allow_none=True, **data_key_fields("i")),
        ),
        # simple types: uuid
        (uuid.UUID, {}, m.fields.UUID(required=True)),
        (Optional[uuid.UUID], {}, m.fields.UUID(required=True, allow_none=True)),
        (uuid.UUID | None, {}, m.fields.UUID(required=True, allow_none=True)),
        (uuid.UUID, mr.metadata(name="i"), m.fields.UUID(required=True, **data_key_fields("i"))),
        (
            Optional[uuid.UUID],
            mr.metadata(name="i"),
            m.fields.UUID(required=True, allow_none=True, **data_key_fields("i")),
        ),
        (
            uuid.UUID | None,
            mr.metadata(name="i"),
            m.fields.UUID(required=True, allow_none=True, **data_key_fields("i")),
        ),
        # simple types: decimal
        (decimal.Decimal, {}, m.fields.Decimal(required=True, places=2, as_string=True)),
        (
            Optional[decimal.Decimal],
            {},
            m.fields.Decimal(required=True, allow_none=True, places=2, as_string=True),
        ),
        (
            decimal.Decimal | None,
            {},
            m.fields.Decimal(required=True, allow_none=True, places=2, as_string=True),
        ),
        (
            decimal.Decimal,
            mr.decimal_metadata(name="i", places=4, as_string=False),
            m.fields.Decimal(required=True, **data_key_fields("i"), places=4, as_string=False),
        ),
        (
            Optional[decimal.Decimal],
            mr.decimal_metadata(name="i", places=4, as_string=False),
            m.fields.Decimal(required=True, allow_none=True, places=4, as_string=False, **data_key_fields("i")),
        ),
        (
            decimal.Decimal | None,
            mr.decimal_metadata(name="i", places=4, as_string=False),
            m.fields.Decimal(required=True, allow_none=True, places=4, as_string=False, **data_key_fields("i")),
        ),
        # simple types: datetime
        (datetime.datetime, {}, mr.fields.DateTimeField(required=True)),
        (
            Optional[datetime.datetime],
            {},
            mr.fields.DateTimeField(required=True, allow_none=True),
        ),
        (
            datetime.datetime | None,
            {},
            mr.fields.DateTimeField(required=True, allow_none=True),
        ),
        (
            datetime.datetime,
            mr.datetime_metadata(name="i", format="%Y-%m-%dT%H:%M:%SZ"),
            mr.fields.DateTimeField(required=True, **data_key_fields("i"), format="%Y-%m-%dT%H:%M:%SZ"),
        ),
        (
            Optional[datetime.datetime],
            mr.datetime_metadata(name="i", format="%Y-%m-%dT%H:%M:%SZ"),
            mr.fields.DateTimeField(
                required=True, allow_none=True, **data_key_fields("i"), format="%Y-%m-%dT%H:%M:%SZ"
            ),
        ),
        (
            datetime.datetime | None,
            mr.datetime_metadata(name="i", format="%Y-%m-%dT%H:%M:%SZ"),
            mr.fields.DateTimeField(
                required=True, allow_none=True, **data_key_fields("i"), format="%Y-%m-%dT%H:%M:%SZ"
            ),
        ),
        # simple types: date
        (datetime.date, {}, m.fields.Date(required=True)),
        (
            Optional[datetime.date],
            {},
            m.fields.Date(required=True, allow_none=True),
        ),
        (
            datetime.date | None,
            {},
            m.fields.Date(required=True, allow_none=True),
        ),
        (
            datetime.date,
            mr.metadata(name="i"),
            m.fields.Date(required=True, **data_key_fields("i")),
        ),
        (
            Optional[datetime.date],
            mr.metadata(name="i"),
            m.fields.Date(required=True, allow_none=True, **data_key_fields("i")),
        ),
        (
            datetime.date | None,
            mr.metadata(name="i"),
            m.fields.Date(required=True, allow_none=True, **data_key_fields("i")),
        ),
        # enum
        (Enum, {}, mr.fields.EnumField(enum_type=Enum, required=True)),
        (Optional[Enum], {}, mr.fields.EnumField(enum_type=Enum, required=True, allow_none=True)),
        (Enum | None, {}, mr.fields.EnumField(enum_type=Enum, required=True, allow_none=True)),
        (Enum, mr.metadata(name="i"), mr.fields.EnumField(enum_type=Enum, required=True, **data_key_fields("i"))),
        (
            Optional[Enum],
            mr.metadata(name="i"),
            mr.fields.EnumField(enum_type=Enum, required=True, allow_none=True, **data_key_fields("i")),
        ),
        (
            Enum | None,
            mr.metadata(name="i"),
            mr.fields.EnumField(enum_type=Enum, required=True, allow_none=True, **data_key_fields("i")),
        ),
        # dataclass
        (EmptyDataclass, {}, m.fields.Nested(EMPTY_SCHEMA, required=True)),
        (Optional[EmptyDataclass], {}, m.fields.Nested(EMPTY_SCHEMA, required=True, allow_none=True)),
        (EmptyDataclass | None, {}, m.fields.Nested(EMPTY_SCHEMA, required=True, allow_none=True)),
        (
            EmptyDataclass,
            mr.metadata(name="i"),
            m.fields.Nested(EMPTY_SCHEMA, required=True, **data_key_fields("i")),
        ),
        (
            Optional[EmptyDataclass],
            mr.metadata(name="i"),
            m.fields.Nested(EMPTY_SCHEMA, required=True, allow_none=True, **data_key_fields("i")),
        ),
        (
            EmptyDataclass | None,
            mr.metadata(name="i"),
            m.fields.Nested(EMPTY_SCHEMA, required=True, allow_none=True, **data_key_fields("i")),
        ),
        # containers: list[T]
        (list[bool], {}, m.fields.List(m.fields.Bool(required=True), required=True)),
        (
            list[Optional[bool]],
            {},
            m.fields.List(m.fields.Bool(required=True, allow_none=True), required=True),
        ),
        (
            list[bool | None],
            {},
            m.fields.List(m.fields.Bool(required=True, allow_none=True), required=True),
        ),
        (
            Optional[list[bool]],
            {},
            m.fields.List(m.fields.Bool(required=True), required=True, allow_none=True),
        ),
        (
            Optional[list[Optional[bool]]],
            {},
            m.fields.List(m.fields.Bool(required=True, allow_none=True), required=True, allow_none=True),
        ),
        (
            list[bool | None] | None,
            {},
            m.fields.List(m.fields.Bool(required=True, allow_none=True), required=True, allow_none=True),
        ),
        # containers: list[T] where T: dataclass
        (list[EmptyDataclass], {}, m.fields.List(m.fields.Nested(EMPTY_SCHEMA, required=True), required=True)),
        (
            list[Optional[EmptyDataclass]],
            {},
            m.fields.List(m.fields.Nested(EMPTY_SCHEMA, required=True, allow_none=True), required=True),
        ),
        (
            list[EmptyDataclass | None],
            {},
            m.fields.List(m.fields.Nested(EMPTY_SCHEMA, required=True, allow_none=True), required=True),
        ),
        (
            Optional[list[EmptyDataclass]],
            {},
            m.fields.List(m.fields.Nested(EMPTY_SCHEMA, required=True), required=True, allow_none=True),
        ),
        (
            Optional[list[Optional[EmptyDataclass]]],
            {},
            m.fields.List(
                m.fields.Nested(EMPTY_SCHEMA, required=True, allow_none=True),
                required=True,
                allow_none=True,
            ),
        ),
        (
            list[EmptyDataclass | None] | None,
            {},
            m.fields.List(
                m.fields.Nested(EMPTY_SCHEMA, required=True, allow_none=True),
                required=True,
                allow_none=True,
            ),
        ),
        # containers: Dict[str, Any]
        (dict[str, Any], {}, m.fields.Dict(required=True)),
        (
            dict[str, Any],
            mr.metadata(name="i"),
            m.fields.Dict(required=True, **data_key_fields("i")),
        ),
        (Optional[dict[str, Any]], {}, m.fields.Dict(required=True, allow_none=True)),
        (
            Optional[dict[str, Any]],
            mr.metadata(name="i"),
            m.fields.Dict(required=True, allow_none=True, **data_key_fields("i")),
        ),
        (dict[str, Any] | None, {}, m.fields.Dict(required=True, allow_none=True)),
        (
            dict[str, Any] | None,
            mr.metadata(name="i"),
            m.fields.Dict(required=True, allow_none=True, **data_key_fields("i")),
        ),
        (Dict[str, Any], {}, m.fields.Dict(required=True)),
        (
            Dict[str, Any],
            mr.metadata(name="i"),
            m.fields.Dict(required=True, **data_key_fields("i")),
        ),
        (Optional[Dict[str, Any]], {}, m.fields.Dict(required=True, allow_none=True)),
        (
            Optional[Dict[str, Any]],
            mr.metadata(name="i"),
            m.fields.Dict(required=True, allow_none=True, **data_key_fields("i")),
        ),
        (Dict[str, Any] | None, {}, m.fields.Dict(required=True, allow_none=True)),
        (
            Dict[str, Any] | None,
            mr.metadata(name="i"),
            m.fields.Dict(required=True, allow_none=True, **data_key_fields("i")),
        ),
    ],
)
def test_get_field_for(type: type, metadata: dict[str, Any], field: m.fields.Field) -> None:
    with unittest.mock.patch("marshmallow_recipe.bake.bake_schema") as bake_schema:
        bake_schema.return_value = EMPTY_SCHEMA
        assert_fields_equal(mr.get_field_for(type, metadata, naming_case=mr.DEFAULT_CASE), field)
