from typing import Any

import marshmallow
import pytest

from tests.test_parity.conftest import AllPrimitives, Person, SimpleTypes, WithCollections


def test_error_missing_required_field(impl: Any) -> None:
    data = b'{"name": "test"}'
    with pytest.raises(marshmallow.ValidationError) as exc:
        impl.load(SimpleTypes, data)
    assert exc.value.messages == {"age": ["Missing data for required field."]}


def test_error_wrong_type_int(impl: Any) -> None:
    data = b'{"name": "test", "age": "not_an_int"}'
    with pytest.raises(marshmallow.ValidationError) as exc:
        impl.load(SimpleTypes, data)
    assert "age" in exc.value.messages


def test_error_wrong_type_bool(impl: Any) -> None:
    data = (
        b'{"str_field": "x", "int_field": 1, "float_field": 1.0, "bool_field": "not_bool", '
        b'"decimal_field": "1.00", "uuid_field": "12345678-1234-5678-1234-567812345678", '
        b'"datetime_field": "2000-01-01T00:00:00+00:00", "date_field": "2000-01-01", '
        b'"time_field": "00:00:00"}'
    )
    with pytest.raises(marshmallow.ValidationError) as exc:
        impl.load(AllPrimitives, data)
    assert "bool_field" in exc.value.messages


def test_error_invalid_uuid(impl: Any) -> None:
    data = (
        b'{"str_field": "x", "int_field": 1, "float_field": 1.0, "bool_field": true, '
        b'"decimal_field": "1.00", "uuid_field": "not-a-uuid", '
        b'"datetime_field": "2000-01-01T00:00:00+00:00", "date_field": "2000-01-01", '
        b'"time_field": "00:00:00"}'
    )
    with pytest.raises(marshmallow.ValidationError) as exc:
        impl.load(AllPrimitives, data)
    assert "uuid_field" in exc.value.messages


def test_error_invalid_datetime(impl: Any) -> None:
    data = (
        b'{"str_field": "x", "int_field": 1, "float_field": 1.0, "bool_field": true, '
        b'"decimal_field": "1.00", "uuid_field": "12345678-1234-5678-1234-567812345678", '
        b'"datetime_field": "not-a-datetime", "date_field": "2000-01-01", "time_field": "00:00:00"}'
    )
    with pytest.raises(marshmallow.ValidationError) as exc:
        impl.load(AllPrimitives, data)
    assert "datetime_field" in exc.value.messages


def test_error_invalid_decimal(impl: Any) -> None:
    data = (
        b'{"str_field": "x", "int_field": 1, "float_field": 1.0, "bool_field": true, '
        b'"decimal_field": "not-a-decimal", "uuid_field": "12345678-1234-5678-1234-567812345678", '
        b'"datetime_field": "2000-01-01T00:00:00+00:00", "date_field": "2000-01-01", '
        b'"time_field": "00:00:00"}'
    )
    with pytest.raises(marshmallow.ValidationError) as exc:
        impl.load(AllPrimitives, data)
    assert "decimal_field" in exc.value.messages


def test_error_nested_field(impl: Any) -> None:
    data = b'{"name": "John", "age": 30, "address": {"street": "Main", "city": "NYC"}}'
    with pytest.raises(marshmallow.ValidationError) as exc:
        impl.load(Person, data)
    assert "address" in exc.value.messages


def test_error_list_item_wrong_type(impl: Any) -> None:
    data = b'{"list_int": [1, "not_int", 3], "list_str": [], "dict_str_int": {}, "set_str": [], "frozenset_int": [], "tuple_str": []}'
    with pytest.raises(marshmallow.ValidationError) as exc:
        impl.load(WithCollections, data)
    assert "list_int" in exc.value.messages
