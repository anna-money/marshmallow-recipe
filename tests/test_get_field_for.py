import dataclasses
import decimal
import inspect
import unittest.mock
from typing import Any, Optional, Type

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


def test_get_field_for_required_bool() -> None:
    naming_case = unittest.mock.Mock(return_value="bool")
    assert_fields_equal(
        mr.get_field_for("bool", bool, mr.MISSING, {}, naming_case=naming_case),
        m.fields.Bool(
            required=True,
            load_from="bool",
            dump_to="bool",
        ),
    )
    naming_case.assert_called_once_with("bool")


@pytest.mark.parametrize(
    "field_type, field_default, marshmallow_default",
    [
        (bool | None, mr.MISSING, None),
        (bool | None, None, None),
        (bool | None, True, True),
        (Optional[bool], mr.MISSING, None),
        (Optional[bool], None, None),
        (Optional[bool], True, True),
    ],
)
def test_get_field_for_optional_bool(
    field_type: Type[bool], field_default: bool | None | mr.Missing, marshmallow_default: bool | None
) -> None:
    naming_case = unittest.mock.Mock(return_value="bool")
    assert_fields_equal(
        mr.get_field_for("bool", field_type, field_default, {}, naming_case=naming_case),
        m.fields.Bool(
            allow_none=True, load_from="bool", dump_to="bool", missing=marshmallow_default, default=marshmallow_default
        ),
    )
    naming_case.assert_called_once_with("bool")


def test_get_field_for_required_str() -> None:
    name = "str"
    naming_case = unittest.mock.Mock(return_value=name)
    assert_fields_equal(
        mr.get_field_for(name, str, mr.MISSING, {}, naming_case=naming_case),
        m.fields.Str(
            required=True,
            load_from=name,
            dump_to=name,
        ),
    )
    naming_case.assert_called_once_with(name)


@pytest.mark.parametrize(
    "field_type, field_default, marshmallow_default",
    [
        (str | None, mr.MISSING, None),
        (str | None, None, None),
        (str | None, "42", "42"),
        (Optional[str], mr.MISSING, None),
        (Optional[str], None, None),
        (Optional[str], "42", "42"),
    ],
)
def test_get_field_for_optional_str(
    field_type: Type[str], field_default: str | None | mr.Missing, marshmallow_default: str | None
) -> None:
    name = "str"
    naming_case = unittest.mock.Mock(return_value=name)
    assert_fields_equal(
        mr.get_field_for(name, field_type, field_default, {}, naming_case=naming_case),
        m.fields.Str(
            allow_none=True, load_from=name, dump_to=name, missing=marshmallow_default, default=marshmallow_default
        ),
    )
    naming_case.assert_called_once_with(name)


@dataclasses.dataclass
class EmptyDataclass:
    pass


EMPTY = EmptyDataclass()
EMPTY_SCHEMA = m.Schema()


def test_get_field_for_required_dataclass() -> None:
    with unittest.mock.patch("marshmallow_recipe.bake.bake_schema") as bake_schema:
        bake_schema.return_value = EMPTY_SCHEMA

        name = "nested"
        naming_case = unittest.mock.Mock(return_value=name)
        assert_fields_equal(
            mr.get_field_for(name, EmptyDataclass, mr.MISSING, {}, naming_case=naming_case),
            m.fields.Nested(
                EMPTY_SCHEMA,
                required=True,
                load_from=name,
                dump_to=name,
            ),
        )
        naming_case.assert_called_once_with(name)
        bake_schema.assert_called_once_with(EmptyDataclass, naming_case=naming_case)


@pytest.mark.parametrize(
    "field_type, field_default, marshmallow_default",
    [
        (EmptyDataclass | None, mr.MISSING, None),
        (EmptyDataclass | None, None, None),
        (Optional[EmptyDataclass], mr.MISSING, None),
        (Optional[EmptyDataclass], None, None),
    ],
)
def test_get_field_for_optional_dataclass(
    field_type: Type[EmptyDataclass],
    field_default: EmptyDataclass | None | mr.Missing,
    marshmallow_default: EmptyDataclass | None,
) -> None:
    with unittest.mock.patch("marshmallow_recipe.bake.bake_schema") as bake_schema:
        bake_schema.return_value = EMPTY_SCHEMA

        name = "nested"
        naming_case = unittest.mock.Mock(return_value=name)
        assert_fields_equal(
            mr.get_field_for(name, field_type, field_default, {}, naming_case=naming_case),
            m.fields.Nested(
                EMPTY_SCHEMA,
                allow_none=True,
                load_from=name,
                dump_to=name,
                missing=marshmallow_default,
                default=marshmallow_default,
            ),
        )
        naming_case.assert_called_once_with(name)
        bake_schema.assert_called_once_with(EmptyDataclass, naming_case=naming_case)


def test_get_field_for_required_decimal() -> None:
    name = "decimal"
    naming_case = unittest.mock.Mock(return_value=name)
    assert_fields_equal(
        mr.get_field_for(name, decimal.Decimal, mr.MISSING, {}, naming_case=naming_case),
        m.fields.Decimal(
            places=2,
            as_string=True,
            required=True,
            load_from=name,
            dump_to=name,
        ),
    )
    naming_case.assert_called_once_with(name)


def test_get_field_for_required_decimal_with_metadata() -> None:
    name = "decimal"
    custom_name = "DECIMAL"
    naming_case = unittest.mock.Mock(return_value=name)
    assert_fields_equal(
        mr.get_field_for(
            name,
            decimal.Decimal,
            mr.MISSING,
            mr.decimal_metadata(name=custom_name, places=4, as_string=False),
            naming_case=naming_case,
        ),
        m.fields.Decimal(
            places=4,
            as_string=False,
            required=True,
            load_from=custom_name,
            dump_to=custom_name,
        ),
    )
    naming_case.assert_called_with(name)


@pytest.mark.parametrize(
    "field_type, field_default, marshmallow_default",
    [
        (decimal.Decimal | None, mr.MISSING, None),
        (decimal.Decimal | None, None, None),
        (decimal.Decimal | None, decimal.Decimal("42"), decimal.Decimal("42")),
        (Optional[decimal.Decimal], mr.MISSING, None),
        (Optional[decimal.Decimal], None, None),
        (Optional[decimal.Decimal], decimal.Decimal("42"), decimal.Decimal("42")),
    ],
)
def test_get_field_for_optional_decimal(
    field_type: Type[decimal.Decimal],
    field_default: decimal.Decimal | None | mr.Missing,
    marshmallow_default: decimal.Decimal | None,
) -> None:
    name = "decimal"
    naming_case = unittest.mock.Mock(return_value=name)
    assert_fields_equal(
        mr.get_field_for(name, field_type, field_default, {}, naming_case=naming_case),
        m.fields.Decimal(
            places=2,
            as_string=True,
            allow_none=True,
            load_from=name,
            dump_to=name,
            missing=marshmallow_default,
            default=marshmallow_default,
        ),
    )
    naming_case.assert_called_once_with(name)


def test_get_field_for_required_int() -> None:
    name = "int"
    naming_case = unittest.mock.Mock(return_value=name)
    assert_fields_equal(
        mr.get_field_for(name, int, mr.MISSING, {}, naming_case=naming_case),
        m.fields.Int(
            required=True,
            load_from=name,
            dump_to=name,
        ),
    )
    naming_case.assert_called_once_with(name)


@pytest.mark.parametrize(
    "field_type, field_default, marshmallow_default",
    [
        (int | None, mr.MISSING, None),
        (int | None, None, None),
        (int | None, 42, 42),
        (Optional[int], mr.MISSING, None),
        (Optional[int], None, None),
        (Optional[int], 42, 42),
    ],
)
def test_get_field_for_optional_int(
    field_type: Type[int],
    field_default: int | None | mr.Missing,
    marshmallow_default: int | None,
) -> None:
    name = "int"
    naming_case = unittest.mock.Mock(return_value=name)
    assert_fields_equal(
        mr.get_field_for(name, field_type, field_default, {}, naming_case=naming_case),
        m.fields.Int(
            allow_none=True,
            load_from=name,
            dump_to=name,
            missing=marshmallow_default,
            default=marshmallow_default,
        ),
    )
    naming_case.assert_called_once_with(name)


def test_get_field_for_required_float() -> None:
    name = "float"
    naming_case = unittest.mock.Mock(return_value=name)
    assert_fields_equal(
        mr.get_field_for(name, float, mr.MISSING, {}, naming_case=naming_case),
        m.fields.Float(
            required=True,
            load_from=name,
            dump_to=name,
        ),
    )
    naming_case.assert_called_once_with(name)


@pytest.mark.parametrize(
    "field_type, field_default, marshmallow_default",
    [
        (float | None, mr.MISSING, None),
        (float | None, None, None),
        (float | None, 42.0, 42.0),
        (Optional[float], mr.MISSING, None),
        (Optional[float], None, None),
        (Optional[float], 42.0, 42.0),
    ],
)
def test_get_field_for_optional_float(
    field_type: Type[float],
    field_default: float | None | mr.Missing,
    marshmallow_default: float | None,
) -> None:
    name = "float"
    naming_case = unittest.mock.Mock(return_value=name)
    assert_fields_equal(
        mr.get_field_for(name, field_type, field_default, {}, naming_case=naming_case),
        m.fields.Float(
            allow_none=True,
            load_from=name,
            dump_to=name,
            missing=marshmallow_default,
            default=marshmallow_default,
        ),
    )
    naming_case.assert_called_once_with(name)
