import inspect
import unittest.mock
from typing import Any, Optional, Type

import marshmallow
import pytest

import marshmallow_recipe


def assert_fields_equal(a: marshmallow.fields.Field, b: marshmallow.fields.Field) -> None:
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
        marshmallow_recipe.get_field_for("bool", bool, marshmallow_recipe.MISSING, {}, naming_case=naming_case),
        marshmallow.fields.Bool(
            required=True,
            load_from="bool",
            dump_to="bool",
        ),
    )
    naming_case.assert_called_once_with("bool")


@pytest.mark.parametrize(
    "field_type, field_default, marshmallow_default",
    [
        (bool | None, marshmallow_recipe.MISSING, None),
        (bool | None, None, None),
        (bool | None, "42", "42"),
        (Optional[bool], marshmallow_recipe.MISSING, None),
        (Optional[bool], None, None),
        (Optional[bool], "42", "42"),
    ],
)
def test_get_field_for_optional_bool(
    field_type: Type[bool], field_default: str | None | marshmallow_recipe.MissingType, marshmallow_default: str | None
) -> None:
    naming_case = unittest.mock.Mock(return_value="bool")
    assert_fields_equal(
        marshmallow_recipe.get_field_for("bool", field_type, field_default, {}, naming_case=naming_case),
        marshmallow.fields.Bool(
            allow_none=True, load_from="bool", dump_to="bool", missing=marshmallow_default, default=marshmallow_default
        ),
    )
    naming_case.assert_called_once_with("bool")


def test_get_field_for_required_str() -> None:
    name = "str"
    naming_case = unittest.mock.Mock(return_value=name)
    assert_fields_equal(
        marshmallow_recipe.get_field_for(name, str, marshmallow_recipe.MISSING, {}, naming_case=naming_case),
        marshmallow.fields.Str(
            required=True,
            load_from=name,
            dump_to=name,
        ),
    )
    naming_case.assert_called_once_with(name)


@pytest.mark.parametrize(
    "field_type, field_default, marshmallow_default",
    [
        (str | None, marshmallow_recipe.MISSING, None),
        (str | None, None, None),
        (str | None, "42", "42"),
        (Optional[str], marshmallow_recipe.MISSING, None),
        (Optional[str], None, None),
        (Optional[str], "42", "42"),
    ],
)
def test_get_field_for_optional_str(
    field_type: Type[str], field_default: str | None | marshmallow_recipe.MissingType, marshmallow_default: str | None
) -> None:
    name = "str"
    naming_case = unittest.mock.Mock(return_value=name)
    assert_fields_equal(
        marshmallow_recipe.get_field_for(name, field_type, field_default, {}, naming_case=naming_case),
        marshmallow.fields.Str(
            allow_none=True, load_from=name, dump_to=name, missing=marshmallow_default, default=marshmallow_default
        ),
    )
    naming_case.assert_called_once_with(name)
