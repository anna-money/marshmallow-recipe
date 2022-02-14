import dataclasses
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
        (bool | None, "42", "42"),
        (Optional[bool], mr.MISSING, None),
        (Optional[bool], None, None),
        (Optional[bool], "42", "42"),
    ],
)
def test_get_field_for_optional_bool(
    field_type: Type[bool], field_default: str | None | mr.MissingType, marshmallow_default: str | None
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
    field_type: Type[str], field_default: str | None | mr.MissingType, marshmallow_default: str | None
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

        name = "str"
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
    field_type: Type[str], field_default: str | None | mr.MissingType, marshmallow_default: str | None
) -> None:
    with unittest.mock.patch("marshmallow_recipe.bake.bake_schema") as bake_schema:
        bake_schema.return_value = EMPTY_SCHEMA

        name = "str"
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
