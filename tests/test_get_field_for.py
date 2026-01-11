import collections.abc
import dataclasses
import datetime
import decimal
import enum
import importlib.metadata
import inspect
import unittest.mock
import uuid
from typing import Annotated, Any, NewType, Optional

import marshmallow as m
import marshmallow_recipe as mr
import pytest

_MARSHMALLOW_VERSION_MAJOR = int(importlib.metadata.version("marshmallow").split(".")[0])


if _MARSHMALLOW_VERSION_MAJOR >= 3:

    def data_key_fields(name: str | None) -> dict[str, Any]:
        if name is None:
            return {}
        return {"data_key": name}

    def default_fields(value: Any) -> dict[str, Any]:
        return {"dump_default": value, "load_default": value}

    def description_fields(description: str | None) -> dict[str, Any]:
        if description is None:
            return {}
        return {"metadata": {"description": description}}

else:

    def data_key_fields(name: str | None) -> dict[str, Any]:
        if name is None:
            return {}
        return {"dump_to": name, "load_from": name}

    def default_fields(value: Any) -> dict[str, Any]:
        return {"missing": value, "default": value}

    def description_fields(description: str | None) -> dict[str, Any]:
        if description is None:
            return {}
        return {"description": description}


def assert_fields_equal(a: m.fields.Field, b: m.fields.Field) -> None:
    assert a.__class__ == b.__class__, "field class"

    def attrs(x: Any) -> dict[str, str]:
        return {
            k: f"{v!r} ({v.__mro__!r})" if inspect.isclass(v) else repr(v)
            for k, v in x.__dict__.items()
            if not k.startswith("_")
        }

    assert attrs(a) == attrs(b)


NewInt = NewType("NewInt", int)


@dataclasses.dataclass
class EmptyDataclass:
    pass


NewDataclass = NewType("NewDataclass", EmptyDataclass)


class Enum(str, enum.Enum):
    pass


EMPTY_SCHEMA = m.Schema()


@pytest.mark.parametrize(
    "type, metadata, field",
    [
        # Any
        (Any, {}, mr.JsonRawField(allow_none=True, **default_fields(None))),
        (Any, mr.meta(name="i"), mr.JsonRawField(allow_none=True, **default_fields(None), **data_key_fields("i"))),
        # Annotated[Any]
        (Annotated[Any, "$"], {}, mr.JsonRawField(allow_none=True, **default_fields(None))),
        (
            Annotated[Any, "$"],
            mr.meta(name="i"),
            mr.JsonRawField(allow_none=True, **default_fields(None), **data_key_fields("i")),
        ),
        (
            Annotated[Any, mr.meta(name="i")],
            {},
            mr.JsonRawField(allow_none=True, **default_fields(None), **data_key_fields("i")),
        ),
        # simple types: bool
        (bool, {}, m.fields.Bool(required=True)),
        (Optional[bool], {}, m.fields.Bool(allow_none=True, **default_fields(None))),
        (bool | None, {}, m.fields.Bool(allow_none=True, **default_fields(None))),
        (bool, mr.meta(name="i"), m.fields.Bool(required=True, **data_key_fields("i"))),
        (
            Optional[bool],
            mr.meta(name="i"),
            m.fields.Bool(allow_none=True, **default_fields(None), **data_key_fields("i")),
        ),
        (
            bool | None,
            mr.meta(name="i"),
            m.fields.Bool(allow_none=True, **default_fields(None), **data_key_fields("i")),
        ),
        # simple types: str
        (str, {}, mr.StrField(required=True)),
        (Optional[str], {}, mr.StrField(allow_none=True, **default_fields(None))),
        (str | None, {}, mr.StrField(allow_none=True, **default_fields(None))),
        (
            str,
            mr.str_meta(name="i", strip_whitespaces=True),
            mr.StrField(required=True, strip_whitespaces=True, **data_key_fields("i")),
        ),
        (
            Optional[str],
            mr.str_meta(name="i", strip_whitespaces=True),
            mr.StrField(allow_none=True, strip_whitespaces=True, **default_fields(None), **data_key_fields("i")),
        ),
        (
            str | None,
            mr.str_meta(name="i", strip_whitespaces=True),
            mr.StrField(allow_none=True, strip_whitespaces=True, **default_fields(None), **data_key_fields("i")),
        ),
        # simple types: int
        (int, {}, m.fields.Int(required=True)),
        (Optional[int], {}, m.fields.Int(allow_none=True, **default_fields(None))),
        (int | None, {}, m.fields.Int(allow_none=True, **default_fields(None))),
        (int, mr.meta(name="i"), m.fields.Int(required=True, **data_key_fields("i"))),
        (
            Optional[int],
            mr.meta(name="i"),
            m.fields.Int(allow_none=True, **default_fields(None), **data_key_fields("i")),
        ),
        (int | None, mr.meta(name="i"), m.fields.Int(allow_none=True, **default_fields(None), **data_key_fields("i"))),
        # simple types: NewType(..., int)
        (NewInt, {}, m.fields.Int(required=True)),
        (Optional[NewInt], {}, m.fields.Int(allow_none=True, **default_fields(None))),
        (NewInt | None, {}, m.fields.Int(allow_none=True, **default_fields(None))),
        (NewInt, mr.meta(name="i"), m.fields.Int(required=True, **data_key_fields("i"))),
        (
            Optional[NewInt],
            mr.meta(name="i"),
            m.fields.Int(allow_none=True, **default_fields(None), **data_key_fields("i")),
        ),
        (
            NewInt | None,
            mr.meta(name="i"),
            m.fields.Int(allow_none=True, **default_fields(None), **data_key_fields("i")),
        ),
        # simple types: float
        (float, {}, mr.FloatField(required=True)),
        (Optional[float], {}, mr.FloatField(allow_none=True, **default_fields(None))),
        (float | None, {}, mr.FloatField(allow_none=True, **default_fields(None))),
        (float, mr.meta(name="i"), mr.FloatField(required=True, **data_key_fields("i"))),
        (
            Optional[float],
            mr.meta(name="i"),
            mr.FloatField(allow_none=True, **default_fields(None), **data_key_fields("i")),
        ),
        (
            float | None,
            mr.meta(name="i"),
            mr.FloatField(allow_none=True, **default_fields(None), **data_key_fields("i")),
        ),
        # simple types: uuid
        (uuid.UUID, {}, m.fields.UUID(required=True)),
        (Optional[uuid.UUID], {}, m.fields.UUID(allow_none=True, **default_fields(None))),
        (uuid.UUID | None, {}, m.fields.UUID(allow_none=True, **default_fields(None))),
        (uuid.UUID, mr.meta(name="i"), m.fields.UUID(required=True, **data_key_fields("i"))),
        (
            Optional[uuid.UUID],
            mr.meta(name="i"),
            m.fields.UUID(allow_none=True, **default_fields(None), **data_key_fields("i")),
        ),
        (
            uuid.UUID | None,
            mr.meta(name="i"),
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
            mr.decimal_meta(name="i", places=4),
            m.fields.Decimal(required=True, **data_key_fields("i"), places=4, as_string=True),
        ),
        (
            decimal.Decimal,
            mr.decimal_meta(name="i", places=4, rounding=decimal.ROUND_DOWN),
            m.fields.Decimal(
                required=True, **data_key_fields("i"), places=4, as_string=True, rounding=decimal.ROUND_DOWN
            ),
        ),
        (
            Optional[decimal.Decimal],
            mr.decimal_meta(name="i", places=4),
            m.fields.Decimal(allow_none=True, **default_fields(None), places=4, as_string=True, **data_key_fields("i")),
        ),
        (
            decimal.Decimal | None,
            mr.decimal_meta(name="i", places=4),
            m.fields.Decimal(allow_none=True, **default_fields(None), places=4, as_string=True, **data_key_fields("i")),
        ),
        # simple types: datetime
        (datetime.datetime, {}, mr.DateTimeField(required=True)),
        (Optional[datetime.datetime], {}, mr.DateTimeField(allow_none=True, **default_fields(None))),
        (datetime.datetime | None, {}, mr.DateTimeField(allow_none=True, **default_fields(None))),
        (
            datetime.datetime,
            mr.datetime_meta(name="i", format="%Y-%m-%dT%H:%M:%SZ"),
            mr.DateTimeField(required=True, **data_key_fields("i"), format="%Y-%m-%dT%H:%M:%SZ"),
        ),
        (
            Optional[datetime.datetime],
            mr.datetime_meta(name="i", format="%Y-%m-%dT%H:%M:%SZ"),
            mr.DateTimeField(
                allow_none=True, **default_fields(None), **data_key_fields("i"), format="%Y-%m-%dT%H:%M:%SZ"
            ),
        ),
        (
            datetime.datetime | None,
            mr.datetime_meta(name="i", format="%Y-%m-%dT%H:%M:%SZ"),
            mr.DateTimeField(
                allow_none=True, **default_fields(None), **data_key_fields("i"), format="%Y-%m-%dT%H:%M:%SZ"
            ),
        ),
        # simple types: time
        (datetime.time, {}, m.fields.Time(required=True)),
        (Optional[datetime.time], {}, m.fields.Time(allow_none=True, **default_fields(None))),
        (datetime.time | None, {}, m.fields.Time(allow_none=True, **default_fields(None))),
        (datetime.time, mr.datetime_meta(name="i"), m.fields.Time(required=True, **data_key_fields("i"))),
        (
            Optional[datetime.time],
            mr.datetime_meta(name="i"),
            m.fields.Time(allow_none=True, **default_fields(None), **data_key_fields("i")),
        ),
        (
            datetime.time | None,
            mr.time_metadata(name="i"),
            m.fields.Time(allow_none=True, **default_fields(None), **data_key_fields("i")),
        ),
        # simple types: date
        (datetime.date, {}, mr.DateField(required=True)),
        (Optional[datetime.date], {}, mr.DateField(allow_none=True, **default_fields(None))),
        (datetime.date | None, {}, mr.DateField(allow_none=True, **default_fields(None))),
        (datetime.date, mr.meta(name="i"), mr.DateField(required=True, **data_key_fields("i"))),
        (
            Optional[datetime.date],
            mr.meta(name="i"),
            mr.DateField(allow_none=True, **default_fields(None), **data_key_fields("i")),
        ),
        (
            datetime.date | None,
            mr.meta(name="i"),
            mr.DateField(allow_none=True, **default_fields(None), **data_key_fields("i")),
        ),
        # enum
        (Enum, {}, mr.EnumField(enum_type=Enum, required=True)),
        (Optional[Enum], {}, mr.EnumField(enum_type=Enum, allow_none=True, **default_fields(None))),
        (Enum | None, {}, mr.EnumField(enum_type=Enum, allow_none=True, **default_fields(None))),
        (Enum, mr.meta(name="i"), mr.EnumField(enum_type=Enum, required=True, **data_key_fields("i"))),
        (
            Optional[Enum],
            mr.meta(name="i"),
            mr.EnumField(enum_type=Enum, allow_none=True, **default_fields(None), **data_key_fields("i")),
        ),
        (
            Enum | None,
            mr.meta(name="i"),
            mr.EnumField(enum_type=Enum, allow_none=True, **default_fields(None), **data_key_fields("i")),
        ),
        # dataclass
        (EmptyDataclass, {}, mr.NestedField(EMPTY_SCHEMA, required=True)),
        (Optional[EmptyDataclass], {}, mr.NestedField(EMPTY_SCHEMA, allow_none=True, **default_fields(None))),
        (EmptyDataclass | None, {}, mr.NestedField(EMPTY_SCHEMA, allow_none=True, **default_fields(None))),
        (EmptyDataclass, mr.meta(name="i"), mr.NestedField(EMPTY_SCHEMA, required=True, **data_key_fields("i"))),
        (
            Optional[EmptyDataclass],
            mr.meta(name="i"),
            mr.NestedField(EMPTY_SCHEMA, allow_none=True, **default_fields(None), **data_key_fields("i")),
        ),
        (
            EmptyDataclass | None,
            mr.meta(name="i"),
            mr.NestedField(EMPTY_SCHEMA, allow_none=True, **default_fields(None), **data_key_fields("i")),
        ),
        # dataclass NewType(..., EmptyDataclass)
        (NewDataclass, {}, mr.NestedField(EMPTY_SCHEMA, required=True)),
        (Optional[NewDataclass], {}, mr.NestedField(EMPTY_SCHEMA, allow_none=True, **default_fields(None))),
        (NewDataclass | None, {}, mr.NestedField(EMPTY_SCHEMA, allow_none=True, **default_fields(None))),
        (NewDataclass, mr.meta(name="i"), mr.NestedField(EMPTY_SCHEMA, required=True, **data_key_fields("i"))),
        (
            Optional[NewDataclass],
            mr.meta(name="i"),
            mr.NestedField(EMPTY_SCHEMA, allow_none=True, **default_fields(None), **data_key_fields("i")),
        ),
        (
            NewDataclass | None,
            mr.meta(name="i"),
            mr.NestedField(EMPTY_SCHEMA, allow_none=True, **default_fields(None), **data_key_fields("i")),
        ),
        # containers: list[T]
        (list[bool], {}, m.fields.List(m.fields.Bool(required=True), required=True)),
        (
            list[Optional[bool]],
            {},
            m.fields.List(m.fields.Bool(allow_none=True, **default_fields(None)), required=True),
        ),
        (list[bool | None], {}, m.fields.List(m.fields.Bool(allow_none=True, **default_fields(None)), required=True)),
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
        (list[EmptyDataclass], {}, m.fields.List(mr.NestedField(EMPTY_SCHEMA, required=True), required=True)),
        (
            list[Optional[EmptyDataclass]],
            {},
            m.fields.List(mr.NestedField(EMPTY_SCHEMA, allow_none=True, **default_fields(None)), required=True),
        ),
        (
            list[EmptyDataclass | None],
            {},
            m.fields.List(mr.NestedField(EMPTY_SCHEMA, allow_none=True, **default_fields(None)), required=True),
        ),
        (
            Optional[list[EmptyDataclass]],
            {},
            m.fields.List(mr.NestedField(EMPTY_SCHEMA, required=True), allow_none=True, **default_fields(None)),
        ),
        (
            Optional[list[Optional[EmptyDataclass]]],
            {},
            m.fields.List(
                mr.NestedField(EMPTY_SCHEMA, allow_none=True, **default_fields(None)),
                allow_none=True,
                **default_fields(None),
            ),
        ),
        (
            list[EmptyDataclass | None] | None,
            {},
            m.fields.List(
                mr.NestedField(EMPTY_SCHEMA, allow_none=True, **default_fields(None)),
                allow_none=True,
                **default_fields(None),
            ),
        ),
        # containers: collections.abc.Sequence[T]
        (collections.abc.Sequence[bool], {}, m.fields.List(m.fields.Bool(required=True), required=True)),
        (
            collections.abc.Sequence[Optional[bool]],
            {},
            m.fields.List(m.fields.Bool(allow_none=True, **default_fields(None)), required=True),
        ),
        (
            collections.abc.Sequence[bool | None],
            {},
            m.fields.List(m.fields.Bool(allow_none=True, **default_fields(None)), required=True),
        ),
        (
            Optional[collections.abc.Sequence[bool]],
            {},
            m.fields.List(m.fields.Bool(required=True), allow_none=True, **default_fields(None)),
        ),
        (
            Optional[collections.abc.Sequence[Optional[bool]]],
            {},
            m.fields.List(
                m.fields.Bool(allow_none=True, **default_fields(None)), allow_none=True, **default_fields(None)
            ),
        ),
        (
            collections.abc.Sequence[bool | None] | None,
            {},
            m.fields.List(
                m.fields.Bool(allow_none=True, **default_fields(None)), allow_none=True, **default_fields(None)
            ),
        ),
        # containers: collections.abc.Sequence[T] where T: dataclass
        (
            collections.abc.Sequence[EmptyDataclass],
            {},
            m.fields.List(mr.NestedField(EMPTY_SCHEMA, required=True), required=True),
        ),
        (
            collections.abc.Sequence[Optional[EmptyDataclass]],
            {},
            m.fields.List(mr.NestedField(EMPTY_SCHEMA, allow_none=True, **default_fields(None)), required=True),
        ),
        (
            collections.abc.Sequence[EmptyDataclass | None],
            {},
            m.fields.List(mr.NestedField(EMPTY_SCHEMA, allow_none=True, **default_fields(None)), required=True),
        ),
        (
            Optional[collections.abc.Sequence[EmptyDataclass]],
            {},
            m.fields.List(mr.NestedField(EMPTY_SCHEMA, required=True), allow_none=True, **default_fields(None)),
        ),
        (
            Optional[collections.abc.Sequence[Optional[EmptyDataclass]]],
            {},
            m.fields.List(
                mr.NestedField(EMPTY_SCHEMA, allow_none=True, **default_fields(None)),
                allow_none=True,
                **default_fields(None),
            ),
        ),
        (
            collections.abc.Sequence[EmptyDataclass | None] | None,
            {},
            m.fields.List(
                mr.NestedField(EMPTY_SCHEMA, allow_none=True, **default_fields(None)),
                allow_none=True,
                **default_fields(None),
            ),
        ),
        # containers: frozenset[T]
        (frozenset[bool], {}, mr.FrozenSetField(m.fields.Bool(required=True), required=True)),
        (
            frozenset[Optional[bool]],
            {},
            mr.FrozenSetField(m.fields.Bool(allow_none=True, **default_fields(None)), required=True),
        ),
        (
            frozenset[bool | None],
            {},
            mr.FrozenSetField(m.fields.Bool(allow_none=True, **default_fields(None)), required=True),
        ),
        (
            Optional[frozenset[bool]],
            {},
            mr.FrozenSetField(m.fields.Bool(required=True), allow_none=True, **default_fields(None)),
        ),
        (
            Optional[frozenset[Optional[bool]]],
            {},
            mr.FrozenSetField(
                m.fields.Bool(allow_none=True, **default_fields(None)), allow_none=True, **default_fields(None)
            ),
        ),
        (
            frozenset[bool | None] | None,
            {},
            mr.FrozenSetField(
                m.fields.Bool(allow_none=True, **default_fields(None)), allow_none=True, **default_fields(None)
            ),
        ),
        # containers: frozenset[T] where T: dataclass
        (frozenset[EmptyDataclass], {}, mr.FrozenSetField(mr.NestedField(EMPTY_SCHEMA, required=True), required=True)),
        (
            frozenset[Optional[EmptyDataclass]],
            {},
            mr.FrozenSetField(mr.NestedField(EMPTY_SCHEMA, allow_none=True, **default_fields(None)), required=True),
        ),
        (
            frozenset[EmptyDataclass | None],
            {},
            mr.FrozenSetField(mr.NestedField(EMPTY_SCHEMA, allow_none=True, **default_fields(None)), required=True),
        ),
        (
            Optional[frozenset[EmptyDataclass]],
            {},
            mr.FrozenSetField(mr.NestedField(EMPTY_SCHEMA, required=True), allow_none=True, **default_fields(None)),
        ),
        (
            Optional[frozenset[Optional[EmptyDataclass]]],
            {},
            mr.FrozenSetField(
                mr.NestedField(EMPTY_SCHEMA, allow_none=True, **default_fields(None)),
                allow_none=True,
                **default_fields(None),
            ),
        ),
        (
            frozenset[EmptyDataclass | None] | None,
            {},
            mr.FrozenSetField(
                mr.NestedField(EMPTY_SCHEMA, allow_none=True, **default_fields(None)),
                allow_none=True,
                **default_fields(None),
            ),
        ),
        # containers: set[T]
        (set[bool], {}, mr.SetField(m.fields.Bool(required=True), required=True)),
        (set[Optional[bool]], {}, mr.SetField(m.fields.Bool(allow_none=True, **default_fields(None)), required=True)),
        (set[bool | None], {}, mr.SetField(m.fields.Bool(allow_none=True, **default_fields(None)), required=True)),
        (Optional[set[bool]], {}, mr.SetField(m.fields.Bool(required=True), allow_none=True, **default_fields(None))),
        (
            Optional[set[Optional[bool]]],
            {},
            mr.SetField(
                m.fields.Bool(allow_none=True, **default_fields(None)), allow_none=True, **default_fields(None)
            ),
        ),
        (
            set[bool | None] | None,
            {},
            mr.SetField(
                m.fields.Bool(allow_none=True, **default_fields(None)), allow_none=True, **default_fields(None)
            ),
        ),
        # containers: set[T] where T: dataclass
        (set[EmptyDataclass], {}, mr.SetField(mr.NestedField(EMPTY_SCHEMA, required=True), required=True)),
        (
            set[Optional[EmptyDataclass]],
            {},
            mr.SetField(mr.NestedField(EMPTY_SCHEMA, allow_none=True, **default_fields(None)), required=True),
        ),
        (
            set[EmptyDataclass | None],
            {},
            mr.SetField(mr.NestedField(EMPTY_SCHEMA, allow_none=True, **default_fields(None)), required=True),
        ),
        (
            Optional[set[EmptyDataclass]],
            {},
            mr.SetField(mr.NestedField(EMPTY_SCHEMA, required=True), allow_none=True, **default_fields(None)),
        ),
        (
            Optional[set[Optional[EmptyDataclass]]],
            {},
            mr.SetField(
                mr.NestedField(EMPTY_SCHEMA, allow_none=True, **default_fields(None)),
                allow_none=True,
                **default_fields(None),
            ),
        ),
        (
            set[EmptyDataclass | None] | None,
            {},
            mr.SetField(
                mr.NestedField(EMPTY_SCHEMA, allow_none=True, **default_fields(None)),
                allow_none=True,
                **default_fields(None),
            ),
        ),
        # containers: collections.abc.Set[T]
        (collections.abc.Set[bool], {}, mr.SetField(m.fields.Bool(required=True), required=True)),
        (
            collections.abc.Set[Optional[bool]],
            {},
            mr.SetField(m.fields.Bool(allow_none=True, **default_fields(None)), required=True),
        ),
        (
            collections.abc.Set[bool | None],
            {},
            mr.SetField(m.fields.Bool(allow_none=True, **default_fields(None)), required=True),
        ),
        (
            Optional[collections.abc.Set[bool]],
            {},
            mr.SetField(m.fields.Bool(required=True), allow_none=True, **default_fields(None)),
        ),
        (
            Optional[collections.abc.Set[Optional[bool]]],
            {},
            mr.SetField(
                m.fields.Bool(allow_none=True, **default_fields(None)), allow_none=True, **default_fields(None)
            ),
        ),
        (
            collections.abc.Set[bool | None] | None,
            {},
            mr.SetField(
                m.fields.Bool(allow_none=True, **default_fields(None)), allow_none=True, **default_fields(None)
            ),
        ),
        # containers: collections.abc.Set[T] where T: dataclass
        (
            collections.abc.Set[EmptyDataclass],
            {},
            mr.SetField(mr.NestedField(EMPTY_SCHEMA, required=True), required=True),
        ),
        (
            collections.abc.Set[Optional[EmptyDataclass]],
            {},
            mr.SetField(mr.NestedField(EMPTY_SCHEMA, allow_none=True, **default_fields(None)), required=True),
        ),
        (
            collections.abc.Set[EmptyDataclass | None],
            {},
            mr.SetField(mr.NestedField(EMPTY_SCHEMA, allow_none=True, **default_fields(None)), required=True),
        ),
        (
            Optional[collections.abc.Set[EmptyDataclass]],
            {},
            mr.SetField(mr.NestedField(EMPTY_SCHEMA, required=True), allow_none=True, **default_fields(None)),
        ),
        (
            Optional[collections.abc.Set[Optional[EmptyDataclass]]],
            {},
            mr.SetField(
                mr.NestedField(EMPTY_SCHEMA, allow_none=True, **default_fields(None)),
                allow_none=True,
                **default_fields(None),
            ),
        ),
        (
            collections.abc.Set[EmptyDataclass | None] | None,
            {},
            mr.SetField(
                mr.NestedField(EMPTY_SCHEMA, allow_none=True, **default_fields(None)),
                allow_none=True,
                **default_fields(None),
            ),
        ),
        # containers: tuple[T, ...]
        (tuple[bool, ...], {}, mr.TupleField(m.fields.Bool(required=True), required=True)),
        (
            tuple[Optional[bool], ...],
            {},
            mr.TupleField(m.fields.Bool(allow_none=True, **default_fields(None)), required=True),
        ),
        (
            tuple[bool | None, ...],
            {},
            mr.TupleField(m.fields.Bool(allow_none=True, **default_fields(None)), required=True),
        ),
        (
            Optional[tuple[bool, ...]],
            {},
            mr.TupleField(m.fields.Bool(required=True), allow_none=True, **default_fields(None)),
        ),
        (
            Optional[tuple[Optional[bool], ...]],
            {},
            mr.TupleField(
                m.fields.Bool(allow_none=True, **default_fields(None)), allow_none=True, **default_fields(None)
            ),
        ),
        (
            tuple[bool | None, ...] | None,
            {},
            mr.TupleField(
                m.fields.Bool(allow_none=True, **default_fields(None)), allow_none=True, **default_fields(None)
            ),
        ),
        # containers: tuple[T, ...] where T: dataclass
        (tuple[EmptyDataclass, ...], {}, mr.TupleField(mr.NestedField(EMPTY_SCHEMA, required=True), required=True)),
        (
            tuple[Optional[EmptyDataclass], ...],
            {},
            mr.TupleField(mr.NestedField(EMPTY_SCHEMA, allow_none=True, **default_fields(None)), required=True),
        ),
        (
            tuple[EmptyDataclass | None, ...],
            {},
            mr.TupleField(mr.NestedField(EMPTY_SCHEMA, allow_none=True, **default_fields(None)), required=True),
        ),
        (
            Optional[tuple[EmptyDataclass, ...]],
            {},
            mr.TupleField(mr.NestedField(EMPTY_SCHEMA, required=True), allow_none=True, **default_fields(None)),
        ),
        (
            Optional[tuple[Optional[EmptyDataclass], ...]],
            {},
            mr.TupleField(
                mr.NestedField(EMPTY_SCHEMA, allow_none=True, **default_fields(None)),
                allow_none=True,
                **default_fields(None),
            ),
        ),
        (
            tuple[EmptyDataclass | None, ...] | None,
            {},
            mr.TupleField(
                mr.NestedField(EMPTY_SCHEMA, allow_none=True, **default_fields(None)),
                allow_none=True,
                **default_fields(None),
            ),
        ),
        # containers: dict[str, Any]
        (dict[str, Any], {}, mr.DictField(required=True)),
        (dict[str, Any], mr.meta(name="i"), mr.DictField(required=True, **data_key_fields("i"))),
        (Optional[dict[str, Any]], {}, mr.DictField(allow_none=True, **default_fields(None))),
        (
            Optional[dict[str, Any]],
            mr.meta(name="i"),
            mr.DictField(allow_none=True, **default_fields(None), **data_key_fields("i")),
        ),
        (dict[str, Any] | None, {}, mr.DictField(allow_none=True, **default_fields(None))),
        (
            dict[str, Any] | None,
            mr.meta(name="i"),
            mr.DictField(allow_none=True, **default_fields(None), **data_key_fields("i")),
        ),
        # containers: dict[datetime.date, int]
        (
            dict[datetime.date, int],
            {},
            mr.DictField(keys=mr.DateField(required=True), values=m.fields.Int(required=True), required=True),
        ),
        (
            dict[datetime.date, int],
            mr.meta(name="i"),
            mr.DictField(
                keys=mr.DateField(required=True),
                values=m.fields.Int(required=True),
                required=True,
                **data_key_fields("i"),
            ),
        ),
        (
            Optional[dict[datetime.date, int]],
            {},
            mr.DictField(
                keys=mr.DateField(required=True),
                values=m.fields.Int(required=True),
                allow_none=True,
                **default_fields(None),
            ),
        ),
        (
            Optional[dict[datetime.date, int]],
            mr.meta(name="i"),
            mr.DictField(
                keys=mr.DateField(required=True),
                values=m.fields.Int(required=True),
                allow_none=True,
                **default_fields(None),
                **data_key_fields("i"),
            ),
        ),
        (
            dict[datetime.date, int] | None,
            {},
            mr.DictField(
                keys=mr.DateField(required=True),
                values=m.fields.Int(required=True),
                allow_none=True,
                **default_fields(None),
            ),
        ),
        (
            dict[datetime.date, int] | None,
            mr.meta(name="i"),
            mr.DictField(
                keys=mr.DateField(required=True),
                values=m.fields.Int(required=True),
                allow_none=True,
                **default_fields(None),
                **data_key_fields("i"),
            ),
        ),
        # containers: collections.abc.Mapping[str, Any]
        (collections.abc.Mapping[str, Any], {}, mr.DictField(required=True)),
        (collections.abc.Mapping[str, Any], mr.meta(name="i"), mr.DictField(required=True, **data_key_fields("i"))),
        (Optional[collections.abc.Mapping[str, Any]], {}, mr.DictField(allow_none=True, **default_fields(None))),
        (
            Optional[collections.abc.Mapping[str, Any]],
            mr.meta(name="i"),
            mr.DictField(allow_none=True, **default_fields(None), **data_key_fields("i")),
        ),
        (collections.abc.Mapping[str, Any] | None, {}, mr.DictField(allow_none=True, **default_fields(None))),
        (
            collections.abc.Mapping[str, Any] | None,
            mr.meta(name="i"),
            mr.DictField(allow_none=True, **default_fields(None), **data_key_fields("i")),
        ),
        # containers: collections.abc.Mapping[datetime.date, int]
        (
            collections.abc.Mapping[datetime.date, int],
            {},
            mr.DictField(keys=mr.DateField(required=True), values=m.fields.Int(required=True), required=True),
        ),
        (
            collections.abc.Mapping[datetime.date, int],
            mr.meta(name="i"),
            mr.DictField(
                keys=mr.DateField(required=True),
                values=m.fields.Int(required=True),
                required=True,
                **data_key_fields("i"),
            ),
        ),
        (
            Optional[collections.abc.Mapping[datetime.date, int]],
            {},
            mr.DictField(
                keys=mr.DateField(required=True),
                values=m.fields.Int(required=True),
                allow_none=True,
                **default_fields(None),
            ),
        ),
        (
            Optional[collections.abc.Mapping[datetime.date, int]],
            mr.meta(name="i"),
            mr.DictField(
                keys=mr.DateField(required=True),
                values=m.fields.Int(required=True),
                allow_none=True,
                **default_fields(None),
                **data_key_fields("i"),
            ),
        ),
        (
            collections.abc.Mapping[datetime.date, int] | None,
            {},
            mr.DictField(
                keys=mr.DateField(required=True),
                values=m.fields.Int(required=True),
                allow_none=True,
                **default_fields(None),
            ),
        ),
        (
            collections.abc.Mapping[datetime.date, int] | None,
            mr.meta(name="i"),
            mr.DictField(
                keys=mr.DateField(required=True),
                values=m.fields.Int(required=True),
                allow_none=True,
                **default_fields(None),
                **data_key_fields("i"),
            ),
        ),
        # unions...
        (int | str, {}, mr.UnionField(fields=[m.fields.Int(required=True), mr.StrField(required=True)], required=True)),
        (
            int | str,
            mr.meta(name="i"),
            mr.UnionField(
                fields=[m.fields.Int(required=True), mr.StrField(required=True)], required=True, **data_key_fields("i")
            ),
        ),
        (
            int | str | None,
            {},
            mr.UnionField(
                fields=[m.fields.Int(required=True), mr.StrField(required=True)],
                allow_none=True,
                **default_fields(None),
            ),
        ),
        (
            int | str | None,
            mr.meta(name="i"),
            mr.UnionField(
                fields=[m.fields.Int(required=True), mr.StrField(required=True)],
                allow_none=True,
                **default_fields(None),
                **data_key_fields("i"),
            ),
        ),
        # description
        (
            str,
            mr.str_meta(description="String field"),
            mr.StrField(required=True, **description_fields("String field")),
        ),
        (int, mr.meta(description="Int field"), m.fields.Int(required=True, **description_fields("Int field"))),
        (
            decimal.Decimal,
            mr.decimal_meta(description="Decimal field"),
            m.fields.Decimal(required=True, as_string=True, places=2, **description_fields("Decimal field")),
        ),
        (
            datetime.datetime,
            mr.datetime_meta(description="DateTime field"),
            mr.DateTimeField(required=True, **description_fields("DateTime field")),
        ),
        (
            list[int],
            mr.list_meta(description="List field"),
            m.fields.List(m.fields.Int(required=True), required=True, **description_fields("List field")),
        ),
        (
            str,
            mr.str_meta(name="custom", description="Field with name and description"),
            mr.StrField(
                required=True, **data_key_fields("custom"), **description_fields("Field with name and description")
            ),
        ),
        (
            Optional[str],
            mr.str_meta(description="Optional field"),
            mr.StrField(allow_none=True, **default_fields(None), **description_fields("Optional field")),
        ),
    ],
)
def test_get_field_for(type: type, metadata: dict[str, Any], field: m.fields.Field) -> None:
    with unittest.mock.patch("marshmallow_recipe.bake._bake_schema") as bake_schema:
        bake_schema.return_value = EMPTY_SCHEMA
        assert_fields_equal(mr.get_field_for(type, mr.Metadata(metadata), None, None), field)


def test_get_field_for_with_global_decimal_places() -> None:
    with unittest.mock.patch("marshmallow_recipe.bake.bake_schema") as bake_schema:
        bake_schema.return_value = EMPTY_SCHEMA

        field = mr.get_field_for(decimal.Decimal, mr.Metadata({}), None, None, decimal_places=5)
        expected = m.fields.Decimal(required=True, places=5, as_string=True)
        assert_fields_equal(field, expected)


def test_get_field_for_metadata_overrides_global_decimal_places() -> None:
    with unittest.mock.patch("marshmallow_recipe.bake.bake_schema") as bake_schema:
        bake_schema.return_value = EMPTY_SCHEMA

        field = mr.get_field_for(decimal.Decimal, mr.decimal_meta(places=3), None, None, decimal_places=5)
        expected = m.fields.Decimal(required=True, places=3, as_string=True)
        assert_fields_equal(field, expected)


def test_get_field_for_global_decimal_places_ignored_for_non_decimal() -> None:
    with unittest.mock.patch("marshmallow_recipe.bake.bake_schema") as bake_schema:
        bake_schema.return_value = EMPTY_SCHEMA

        field = mr.get_field_for(int, mr.Metadata({}), None, None, decimal_places=5)
        expected = m.fields.Int(required=True)
        assert_fields_equal(field, expected)
