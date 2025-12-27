from typing import Any

from tests.test_parity.conftest import Priority, Status, WithEnums


def test_str_enum_dump(impl: Any) -> None:
    obj = WithEnums(status=Status.ACTIVE, priority=Priority.HIGH, optional_status=None)
    result = impl.dump(WithEnums, obj)
    assert result == '{"priority": 3, "status": "active"}'


def test_str_enum_load(impl: Any) -> None:
    data = b'{"status": "inactive", "priority": 2}'
    result = impl.load(WithEnums, data)
    assert result.status == Status.INACTIVE
    assert result.priority == Priority.MEDIUM
    assert result.optional_status is None


def test_int_enum_dump(impl: Any) -> None:
    obj = WithEnums(status=Status.PENDING, priority=Priority.LOW, optional_status=None)
    result = impl.dump(WithEnums, obj)
    assert result == '{"priority": 1, "status": "pending"}'


def test_int_enum_load(impl: Any) -> None:
    data = b'{"status": "active", "priority": 3}'
    result = impl.load(WithEnums, data)
    assert result.priority == Priority.HIGH


def test_optional_enum_none(impl: Any) -> None:
    obj = WithEnums(status=Status.ACTIVE, priority=Priority.MEDIUM, optional_status=None)
    result = impl.dump(WithEnums, obj)
    assert result == '{"priority": 2, "status": "active"}'


def test_optional_enum_value(impl: Any) -> None:
    obj = WithEnums(status=Status.ACTIVE, priority=Priority.MEDIUM, optional_status=Status.PENDING)
    result = impl.dump(WithEnums, obj)
    assert result == '{"optional_status": "pending", "priority": 2, "status": "active"}'
