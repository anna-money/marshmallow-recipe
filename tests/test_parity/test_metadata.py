from typing import Any

from tests.test_parity.conftest import WithCustomName, WithStripWhitespace


def test_strip_whitespaces_dump(impl: Any) -> None:
    obj = WithStripWhitespace(name="  John  ", email="  test@example.com  ")
    result = impl.dump(WithStripWhitespace, obj)
    assert result == '{"email": "test@example.com", "name": "John"}'


def test_strip_whitespaces_load(impl: Any) -> None:
    data = b'{"name": "  Alice  ", "email": "  alice@example.com  "}'
    result = impl.load(WithStripWhitespace, data)
    assert result == WithStripWhitespace(name="Alice", email="alice@example.com")


def test_strip_whitespaces_already_clean(impl: Any) -> None:
    obj = WithStripWhitespace(name="Bob", email="bob@example.com")
    result = impl.dump(WithStripWhitespace, obj)
    assert result == '{"email": "bob@example.com", "name": "Bob"}'


def test_custom_field_name_dump(impl: Any) -> None:
    obj = WithCustomName(internal_id=123, user_email="test@example.com")
    result = impl.dump(WithCustomName, obj)
    assert result == '{"email": "test@example.com", "id": 123}'


def test_custom_field_name_load(impl: Any) -> None:
    data = b'{"id": 456, "email": "user@example.com"}'
    result = impl.load(WithCustomName, data)
    assert result == WithCustomName(internal_id=456, user_email="user@example.com")


def test_custom_name_roundtrip(impl: Any) -> None:
    obj = WithCustomName(internal_id=789, user_email="round@example.com")
    dumped = impl.dump(WithCustomName, obj)
    loaded = impl.load(WithCustomName, dumped.encode() if isinstance(dumped, str) else dumped)
    assert loaded == obj
