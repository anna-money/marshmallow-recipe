import dataclasses
import decimal
import inspect
import unittest.mock
import uuid
from typing import Any, Dict, Optional

import marshmallow as m
import pytest

import marshmallow_recipe as mr


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


EMPTY = EmptyDataclass()
EMPTY_SCHEMA = m.Schema()


@pytest.mark.parametrize(
    "type, metadata, field",
    [
        # simple types
        (bool, {}, m.fields.Bool(required=True)),
        (Optional[bool], {}, m.fields.Bool(allow_none=True, missing=None, default=None)),
        (bool | None, {}, m.fields.Bool(allow_none=True, missing=None, default=None)),
        (bool, mr.metadata(name="i"), m.fields.Bool(required=True, load_from="i", dump_to="i")),
        (
            Optional[bool],
            mr.metadata(name="i"),
            m.fields.Bool(allow_none=True, missing=None, default=None, load_from="i", dump_to="i"),
        ),
        (
            bool | None,
            mr.metadata(name="i"),
            m.fields.Bool(allow_none=True, missing=None, default=None, load_from="i", dump_to="i"),
        ),
        (str, {}, m.fields.Str(required=True)),
        (Optional[str], {}, m.fields.Str(allow_none=True, missing=None, default=None)),
        (str | None, {}, m.fields.Str(allow_none=True, missing=None, default=None)),
        (str, mr.metadata(name="i"), m.fields.Str(required=True, load_from="i", dump_to="i")),
        (
            Optional[str],
            mr.metadata(name="i"),
            m.fields.Str(allow_none=True, missing=None, default=None, load_from="i", dump_to="i"),
        ),
        (
            str | None,
            mr.metadata(name="i"),
            m.fields.Str(allow_none=True, missing=None, default=None, load_from="i", dump_to="i"),
        ),
        (int, {}, m.fields.Int(required=True)),
        (Optional[int], {}, m.fields.Int(allow_none=True, missing=None, default=None)),
        (int | None, {}, m.fields.Int(allow_none=True, missing=None, default=None)),
        (int, mr.metadata(name="i"), m.fields.Int(required=True, load_from="i", dump_to="i")),
        (
            Optional[int],
            mr.metadata(name="i"),
            m.fields.Int(allow_none=True, missing=None, default=None, load_from="i", dump_to="i"),
        ),
        (
            int | None,
            mr.metadata(name="i"),
            m.fields.Int(allow_none=True, missing=None, default=None, load_from="i", dump_to="i"),
        ),
        (float, {}, m.fields.Float(required=True)),
        (Optional[float], {}, m.fields.Float(allow_none=True, missing=None, default=None)),
        (float | None, {}, m.fields.Float(allow_none=True, missing=None, default=None)),
        (float, mr.metadata(name="i"), m.fields.Float(required=True, load_from="i", dump_to="i")),
        (
            Optional[float],
            mr.metadata(name="i"),
            m.fields.Float(allow_none=True, missing=None, default=None, load_from="i", dump_to="i"),
        ),
        (
            float | None,
            mr.metadata(name="i"),
            m.fields.Float(allow_none=True, missing=None, default=None, load_from="i", dump_to="i"),
        ),
        (uuid.UUID, {}, m.fields.UUID(required=True)),
        (Optional[uuid.UUID], {}, m.fields.UUID(allow_none=True, missing=None, default=None)),
        (uuid.UUID | None, {}, m.fields.UUID(allow_none=True, missing=None, default=None)),
        (uuid.UUID, mr.metadata(name="i"), m.fields.UUID(required=True, load_from="i", dump_to="i")),
        (
            Optional[uuid.UUID],
            mr.metadata(name="i"),
            m.fields.UUID(allow_none=True, missing=None, default=None, load_from="i", dump_to="i"),
        ),
        (
            uuid.UUID | None,
            mr.metadata(name="i"),
            m.fields.UUID(allow_none=True, missing=None, default=None, load_from="i", dump_to="i"),
        ),
        (decimal.Decimal, {}, m.fields.Decimal(required=True, places=2, as_string=True)),
        (
            Optional[decimal.Decimal],
            {},
            m.fields.Decimal(allow_none=True, missing=None, default=None, places=2, as_string=True),
        ),
        (
            decimal.Decimal | None,
            {},
            m.fields.Decimal(allow_none=True, missing=None, default=None, places=2, as_string=True),
        ),
        (
            decimal.Decimal,
            mr.decimal_metadata(name="i", places=4, as_string=False),
            m.fields.Decimal(required=True, load_from="i", dump_to="i", places=4, as_string=False),
        ),
        (
            Optional[decimal.Decimal],
            mr.decimal_metadata(name="i", places=4, as_string=False),
            m.fields.Decimal(
                allow_none=True, missing=None, default=None, places=4, as_string=False, load_from="i", dump_to="i"
            ),
        ),
        (
            decimal.Decimal | None,
            mr.decimal_metadata(name="i", places=4, as_string=False),
            m.fields.Decimal(
                allow_none=True, missing=None, default=None, places=4, as_string=False, load_from="i", dump_to="i"
            ),
        ),
        # dataclass
        (EmptyDataclass, {}, m.fields.Nested(EMPTY_SCHEMA, required=True)),
        (Optional[EmptyDataclass], {}, m.fields.Nested(EMPTY_SCHEMA, allow_none=True, missing=None, default=None)),
        (EmptyDataclass | None, {}, m.fields.Nested(EMPTY_SCHEMA, allow_none=True, missing=None, default=None)),
        (
            EmptyDataclass,
            mr.metadata(name="i"),
            m.fields.Nested(EMPTY_SCHEMA, required=True, load_from="i", dump_to="i"),
        ),
        (
            Optional[EmptyDataclass],
            mr.metadata(name="i"),
            m.fields.Nested(EMPTY_SCHEMA, allow_none=True, missing=None, default=None, load_from="i", dump_to="i"),
        ),
        (
            EmptyDataclass | None,
            mr.metadata(name="i"),
            m.fields.Nested(EMPTY_SCHEMA, allow_none=True, missing=None, default=None, load_from="i", dump_to="i"),
        ),
        # containers: list[T]
        (list[bool], {}, m.fields.List(m.fields.Bool(required=True), required=True)),
        (
            list[Optional[bool]],
            {},
            m.fields.List(m.fields.Bool(allow_none=True, missing=None, default=None), required=True),
        ),
        (
            list[bool | None],
            {},
            m.fields.List(m.fields.Bool(allow_none=True, missing=None, default=None), required=True),
        ),
        (
            Optional[list[bool]],
            {},
            m.fields.List(m.fields.Bool(required=True), allow_none=True, missing=None, default=None),
        ),
        (
            Optional[list[Optional[bool]]],
            {},
            m.fields.List(
                m.fields.Bool(allow_none=True, missing=None, default=None), allow_none=True, missing=None, default=None
            ),
        ),
        (
            list[bool | None] | None,
            {},
            m.fields.List(
                m.fields.Bool(allow_none=True, missing=None, default=None), allow_none=True, missing=None, default=None
            ),
        ),
        # containers: list[T] where T: dataclass
        (list[EmptyDataclass], {}, m.fields.List(m.fields.Nested(EMPTY_SCHEMA, required=True), required=True)),
        (
            list[Optional[EmptyDataclass]],
            {},
            m.fields.List(m.fields.Nested(EMPTY_SCHEMA, allow_none=True, missing=None, default=None), required=True),
        ),
        (
            list[EmptyDataclass | None],
            {},
            m.fields.List(m.fields.Nested(EMPTY_SCHEMA, allow_none=True, missing=None, default=None), required=True),
        ),
        (
            Optional[list[EmptyDataclass]],
            {},
            m.fields.List(m.fields.Nested(EMPTY_SCHEMA, required=True), allow_none=True, missing=None, default=None),
        ),
        (
            Optional[list[Optional[EmptyDataclass]]],
            {},
            m.fields.List(
                m.fields.Nested(EMPTY_SCHEMA, allow_none=True, missing=None, default=None),
                allow_none=True,
                missing=None,
                default=None,
            ),
        ),
        (
            list[EmptyDataclass | None] | None,
            {},
            m.fields.List(
                m.fields.Nested(EMPTY_SCHEMA, allow_none=True, missing=None, default=None),
                allow_none=True,
                missing=None,
                default=None,
            ),
        ),
        # containers: Dict[str, Any]
        (dict[str, Any], {}, m.fields.Dict(required=True)),
        (
            dict[str, Any],
            mr.metadata(name="i"),
            m.fields.Dict(required=True, load_from="i", dump_to="i"),
        ),
        (Optional[dict[str, Any]], {}, m.fields.Dict(allow_none=True, missing=None, default=None)),
        (
            Optional[dict[str, Any]],
            mr.metadata(name="i"),
            m.fields.Dict(allow_none=True, missing=None, default=None, load_from="i", dump_to="i"),
        ),
        (dict[str, Any] | None, {}, m.fields.Dict(allow_none=True, missing=None, default=None)),
        (
            dict[str, Any] | None,
            mr.metadata(name="i"),
            m.fields.Dict(allow_none=True, missing=None, default=None, load_from="i", dump_to="i"),
        ),
        (Dict[str, Any], {}, m.fields.Dict(required=True)),
        (
            Dict[str, Any],
            mr.metadata(name="i"),
            m.fields.Dict(required=True, load_from="i", dump_to="i"),
        ),
        (Optional[Dict[str, Any]], {}, m.fields.Dict(allow_none=True, missing=None, default=None)),
        (
            Optional[Dict[str, Any]],
            mr.metadata(name="i"),
            m.fields.Dict(allow_none=True, missing=None, default=None, load_from="i", dump_to="i"),
        ),
        (Dict[str, Any] | None, {}, m.fields.Dict(allow_none=True, missing=None, default=None)),
        (
            Dict[str, Any] | None,
            mr.metadata(name="i"),
            m.fields.Dict(allow_none=True, missing=None, default=None, load_from="i", dump_to="i"),
        ),
    ],
)
def test_get_field_for(type: type, metadata: dict[str, Any], field: m.fields.Field) -> None:
    with unittest.mock.patch("marshmallow_recipe.bake.bake_schema") as bake_schema:
        bake_schema.return_value = EMPTY_SCHEMA
        assert_fields_equal(mr.get_field_for(type, metadata, naming_case=mr.DEFAULT_CASE), field)
