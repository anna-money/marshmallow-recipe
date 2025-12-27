import datetime
import decimal
import uuid
from typing import Any

from tests.test_parity.conftest import AllPrimitives, WithDecimal


def test_all_primitives_dump(impl: Any) -> None:
    obj = AllPrimitives(
        str_field="hello",
        int_field=42,
        float_field=3.14,
        bool_field=True,
        decimal_field=decimal.Decimal("99.99"),
        uuid_field=uuid.UUID("12345678-1234-5678-1234-567812345678"),
        datetime_field=datetime.datetime(2025, 12, 26, 10, 30, 45, 123456, datetime.UTC),
        date_field=datetime.date(2025, 12, 26),
        time_field=datetime.time(10, 30, 45, 123456),
    )
    result = impl.dump(AllPrimitives, obj)
    expected = (
        '{"bool_field": true, "date_field": "2025-12-26", '
        '"datetime_field": "2025-12-26T10:30:45.123456+00:00", '
        '"decimal_field": "99.99", "float_field": 3.14, "int_field": 42, '
        '"str_field": "hello", "time_field": "10:30:45.123456", '
        '"uuid_field": "12345678-1234-5678-1234-567812345678"}'
    )
    assert result == expected


def test_all_primitives_load(impl: Any) -> None:
    data = (
        b'{"str_field": "hello", "int_field": 42, "float_field": 3.14, '
        b'"bool_field": true, "decimal_field": "99.99", '
        b'"uuid_field": "12345678-1234-5678-1234-567812345678", '
        b'"datetime_field": "2025-12-26T10:30:45.123456+00:00", '
        b'"date_field": "2025-12-26", "time_field": "10:30:45.123456"}'
    )
    result = impl.load(AllPrimitives, data)
    assert result == AllPrimitives(
        str_field="hello",
        int_field=42,
        float_field=3.14,
        bool_field=True,
        decimal_field=decimal.Decimal("99.99"),
        uuid_field=uuid.UUID("12345678-1234-5678-1234-567812345678"),
        datetime_field=datetime.datetime(2025, 12, 26, 10, 30, 45, 123456, datetime.UTC),
        date_field=datetime.date(2025, 12, 26),
        time_field=datetime.time(10, 30, 45, 123456),
    )


def test_decimal_places_0(impl: Any) -> None:
    obj = WithDecimal(value=decimal.Decimal("123.456"))
    result = impl.dump(WithDecimal, obj, decimal_places=0)
    assert result == '{"value": "123"}'


def test_decimal_places_5(impl: Any) -> None:
    obj = WithDecimal(value=decimal.Decimal("123.456"))
    result = impl.dump(WithDecimal, obj, decimal_places=5)
    assert result == '{"value": "123.45600"}'


def test_decimal_negative(impl: Any) -> None:
    obj = WithDecimal(value=decimal.Decimal("-999.99"))
    result = impl.dump(WithDecimal, obj)
    assert result == '{"value": "-999.99"}'


def test_decimal_very_large(impl: Any) -> None:
    obj = WithDecimal(value=decimal.Decimal("999999999999999.99"))
    result = impl.dump(WithDecimal, obj)
    assert result == '{"value": "999999999999999.99"}'


def test_decimal_very_small(impl: Any) -> None:
    obj = WithDecimal(value=decimal.Decimal("0.01"))
    result = impl.dump(WithDecimal, obj)
    assert result == '{"value": "0.01"}'


def test_decimal_zero(impl: Any) -> None:
    obj = WithDecimal(value=decimal.Decimal("0"))
    result = impl.dump(WithDecimal, obj)
    assert result == '{"value": "0.00"}'


def test_bool_true(impl: Any) -> None:
    obj = AllPrimitives(
        str_field="",
        int_field=0,
        float_field=0.0,
        bool_field=True,
        decimal_field=decimal.Decimal("0"),
        uuid_field=uuid.UUID("00000000-0000-0000-0000-000000000000"),
        datetime_field=datetime.datetime(2000, 1, 1, tzinfo=datetime.UTC),
        date_field=datetime.date(2000, 1, 1),
        time_field=datetime.time(0, 0, 0),
    )
    result = impl.dump(AllPrimitives, obj)
    expected = (
        '{"bool_field": true, "date_field": "2000-01-01", '
        '"datetime_field": "2000-01-01T00:00:00+00:00", "decimal_field": "0.00", '
        '"float_field": 0.0, "int_field": 0, "str_field": "", "time_field": "00:00:00", '
        '"uuid_field": "00000000-0000-0000-0000-000000000000"}'
    )
    assert result == expected


def test_bool_false(impl: Any) -> None:
    obj = AllPrimitives(
        str_field="",
        int_field=0,
        float_field=0.0,
        bool_field=False,
        decimal_field=decimal.Decimal("0"),
        uuid_field=uuid.UUID("00000000-0000-0000-0000-000000000000"),
        datetime_field=datetime.datetime(2000, 1, 1, tzinfo=datetime.UTC),
        date_field=datetime.date(2000, 1, 1),
        time_field=datetime.time(0, 0, 0),
    )
    result = impl.dump(AllPrimitives, obj)
    expected = (
        '{"bool_field": false, "date_field": "2000-01-01", '
        '"datetime_field": "2000-01-01T00:00:00+00:00", "decimal_field": "0.00", '
        '"float_field": 0.0, "int_field": 0, "str_field": "", "time_field": "00:00:00", '
        '"uuid_field": "00000000-0000-0000-0000-000000000000"}'
    )
    assert result == expected


def test_float_precision(impl: Any) -> None:
    obj = AllPrimitives(
        str_field="",
        int_field=0,
        float_field=3.141592653589793,
        bool_field=True,
        decimal_field=decimal.Decimal("0"),
        uuid_field=uuid.UUID("00000000-0000-0000-0000-000000000000"),
        datetime_field=datetime.datetime(2000, 1, 1, tzinfo=datetime.UTC),
        date_field=datetime.date(2000, 1, 1),
        time_field=datetime.time(0, 0, 0),
    )
    result = impl.dump(AllPrimitives, obj)
    expected = (
        '{"bool_field": true, "date_field": "2000-01-01", '
        '"datetime_field": "2000-01-01T00:00:00+00:00", "decimal_field": "0.00", '
        '"float_field": 3.141592653589793, "int_field": 0, "str_field": "", "time_field": "00:00:00", '
        '"uuid_field": "00000000-0000-0000-0000-000000000000"}'
    )
    assert result == expected
