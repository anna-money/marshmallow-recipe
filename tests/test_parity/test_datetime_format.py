import datetime
from typing import Any

from tests.test_parity.conftest import WithDateTimeCustomFormat, WithDateTimeCustomFormatFull


def test_datetime_format_date_only_dump(impl: Any) -> None:
    obj = WithDateTimeCustomFormat(scheduled_at=datetime.datetime(2024, 12, 25, 14, 30, 0, tzinfo=datetime.UTC))
    result = impl.dump(WithDateTimeCustomFormat, obj)
    assert result == '{"scheduled_at": "2024/12/25"}'


def test_datetime_format_date_only_load(impl: Any) -> None:
    data = b'{"scheduled_at": "2024/12/25"}'
    result = impl.load(WithDateTimeCustomFormat, data)
    assert result == WithDateTimeCustomFormat(
        scheduled_at=datetime.datetime(2024, 12, 25, 0, 0, 0, tzinfo=datetime.UTC)
    )


def test_datetime_format_date_only_roundtrip(impl: Any) -> None:
    obj = WithDateTimeCustomFormat(scheduled_at=datetime.datetime(2025, 1, 15, 10, 30, 45, tzinfo=datetime.UTC))
    dumped = impl.dump(WithDateTimeCustomFormat, obj)
    loaded = impl.load(WithDateTimeCustomFormat, dumped.encode() if isinstance(dumped, str) else dumped)
    expected = WithDateTimeCustomFormat(scheduled_at=datetime.datetime(2025, 1, 15, 0, 0, 0, tzinfo=datetime.UTC))
    assert loaded == expected


def test_datetime_format_full_dump(impl: Any) -> None:
    obj = WithDateTimeCustomFormatFull(created_at=datetime.datetime(2024, 6, 15, 14, 30, 45, tzinfo=datetime.UTC))
    result = impl.dump(WithDateTimeCustomFormatFull, obj)
    assert result == '{"created_at": "2024-06-15 14:30:45"}'


def test_datetime_format_full_load(impl: Any) -> None:
    data = b'{"created_at": "2024-06-15 14:30:45"}'
    result = impl.load(WithDateTimeCustomFormatFull, data)
    assert result == WithDateTimeCustomFormatFull(
        created_at=datetime.datetime(2024, 6, 15, 14, 30, 45, tzinfo=datetime.UTC)
    )


def test_datetime_format_full_roundtrip(impl: Any) -> None:
    obj = WithDateTimeCustomFormatFull(created_at=datetime.datetime(2025, 12, 27, 23, 59, 59, tzinfo=datetime.UTC))
    dumped = impl.dump(WithDateTimeCustomFormatFull, obj)
    loaded = impl.load(WithDateTimeCustomFormatFull, dumped.encode() if isinstance(dumped, str) else dumped)
    assert loaded == obj
