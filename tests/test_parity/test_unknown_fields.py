from typing import Any

from tests.test_parity.conftest import SimpleTypes, WithCustomName


def test_unknown_fields_ignored_in_load(impl: Any) -> None:
    data = b'{"name": "test", "age": 30, "extra_field": "should_be_ignored"}'
    result = impl.load(SimpleTypes, data)
    assert result == SimpleTypes(name="test", age=30)


def test_multiple_unknown_fields_ignored(impl: Any) -> None:
    data = b'{"name": "Alice", "age": 25, "email": "ignored", "phone": "ignored", "address": "ignored"}'
    result = impl.load(SimpleTypes, data)
    assert result == SimpleTypes(name="Alice", age=25)


def test_dump_only_defined_fields(impl: Any) -> None:
    obj = SimpleTypes(name="Bob", age=35)
    result = impl.dump(SimpleTypes, obj)
    assert result == '{"age": 35, "name": "Bob"}'
    assert "extra" not in result


def test_custom_name_with_extra_fields(impl: Any) -> None:
    data = b'{"id": 123, "email": "test@example.com", "extra": "ignored"}'
    result = impl.load(WithCustomName, data)
    assert result == WithCustomName(internal_id=123, user_email="test@example.com")
