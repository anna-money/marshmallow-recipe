from typing import Any

from tests.test_parity.conftest import WithDefaults, WithOptional


def test_optional_none_dump(impl: Any) -> None:
    obj = WithOptional(required="test", optional_int=None, optional_str=None)
    result = impl.dump(WithOptional, obj)
    assert result == '{"required": "test"}'


def test_optional_with_value_dump(impl: Any) -> None:
    obj = WithOptional(required="test", optional_int=42, optional_str="hello")
    result = impl.dump(WithOptional, obj)
    expected = '{"optional_int": 42, "optional_str": "hello", "required": "test"}'
    assert result == expected


def test_optional_none_load(impl: Any) -> None:
    data = b'{"required": "test", "optional_int": null, "optional_str": null}'
    result = impl.load(WithOptional, data)
    assert result == WithOptional(required="test", optional_int=None, optional_str=None)


def test_optional_missing_load(impl: Any) -> None:
    data = b'{"required": "test"}'
    result = impl.load(WithOptional, data)
    assert result == WithOptional(required="test", optional_int=None, optional_str=None)


def test_defaults_provided_dump(impl: Any) -> None:
    obj = WithDefaults(name="test", count=100, flag=False, items=["a", "b"], tags={"x", "y"})
    result = impl.dump(WithDefaults, obj)
    result_obj = impl.load(WithDefaults, result.encode() if isinstance(result, str) else result)
    assert result_obj.name == "test"
    assert result_obj.count == 100
    assert result_obj.flag is False
    assert result_obj.items == ["a", "b"]
    assert result_obj.tags == {"x", "y"}


def test_defaults_omitted_load(impl: Any) -> None:
    data = b'{"name": "test"}'
    result = impl.load(WithDefaults, data)
    assert result == WithDefaults(name="test", count=42, flag=True, items=[], tags=set())
