from typing import Any

from tests.test_parity.conftest import WithOptional


def test_none_handling_ignore_default(impl: Any) -> None:
    obj = WithOptional(required="test", optional_int=None, optional_str=None)
    result = impl.dump(WithOptional, obj)
    assert result == '{"required": "test"}'


def test_none_handling_ignore_explicit(impl: Any) -> None:
    obj = WithOptional(required="test", optional_int=None, optional_str="value")
    result = impl.dump(WithOptional, obj, none_value_handling="ignore")
    assert result == '{"optional_str": "value", "required": "test"}'


def test_none_handling_include(impl: Any) -> None:
    obj = WithOptional(required="test", optional_int=None, optional_str=None)
    result = impl.dump(WithOptional, obj, none_value_handling="include")
    expected = '{"optional_int": null, "optional_str": null, "required": "test"}'
    assert result == expected


def test_none_handling_include_mixed(impl: Any) -> None:
    obj = WithOptional(required="test", optional_int=42, optional_str=None)
    result = impl.dump(WithOptional, obj, none_value_handling="include")
    expected = '{"optional_int": 42, "optional_str": null, "required": "test"}'
    assert result == expected
