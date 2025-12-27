from typing import Any

from tests.test_parity.conftest import WithUnion


def test_union_int_dump(impl: Any) -> None:
    obj = WithUnion(value=42, optional_value=None)
    result = impl.dump(WithUnion, obj)
    assert result == '{"value": 42}'


def test_union_str_dump(impl: Any) -> None:
    obj = WithUnion(value="hello", optional_value=None)
    result = impl.dump(WithUnion, obj)
    assert result == '{"value": "hello"}'


def test_union_int_load(impl: Any) -> None:
    data = b'{"value": 100}'
    result = impl.load(WithUnion, data)
    assert result == WithUnion(value=100, optional_value=None)


def test_union_str_load(impl: Any) -> None:
    data = b'{"value": "test"}'
    result = impl.load(WithUnion, data)
    assert result == WithUnion(value="test", optional_value=None)


def test_optional_union_with_int(impl: Any) -> None:
    data = b'{"value": "x", "optional_value": 999}'
    result = impl.load(WithUnion, data)
    assert result.optional_value == 999


def test_optional_union_with_str(impl: Any) -> None:
    data = b'{"value": 1, "optional_value": "optional"}'
    result = impl.load(WithUnion, data)
    assert result.optional_value == "optional"
