import datetime

import marshmallow
import pytest

from .conftest import (
    Serializer,
    ValueOf,
    WithDateTimeCustomFormat,
    WithDateTimeCustomFormatFull,
    WithDatetimeInvalidError,
    WithDatetimeMissing,
    WithDatetimeNoneError,
    WithDatetimeRequiredError,
    WithDatetimeTwoValidators,
    WithDatetimeValidation,
)


class TestDatetimeDump:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (
                datetime.datetime(2025, 12, 26, 10, 30, 45, 123456, datetime.UTC),
                b'{"value":"2025-12-26T10:30:45.123456+00:00"}',
            ),
            (datetime.datetime(2025, 1, 1, 0, 0, 0, tzinfo=datetime.UTC), b'{"value":"2025-01-01T00:00:00+00:00"}'),
            (
                datetime.datetime(2025, 12, 31, 23, 59, 59, tzinfo=datetime.UTC),
                b'{"value":"2025-12-31T23:59:59+00:00"}',
            ),
            (datetime.datetime(2024, 2, 29, 12, 0, 0, tzinfo=datetime.UTC), b'{"value":"2024-02-29T12:00:00+00:00"}'),
        ],
    )
    def test_value(self, impl: Serializer, value: datetime.datetime, expected: bytes) -> None:
        obj = ValueOf[datetime.datetime](value=value)
        result = impl.dump(ValueOf[datetime.datetime], obj)
        assert result == expected

    def test_format_date_only(self, impl: Serializer) -> None:
        obj = WithDateTimeCustomFormat(scheduled_at=datetime.datetime(2024, 12, 25, 14, 30, 0, tzinfo=datetime.UTC))
        result = impl.dump(WithDateTimeCustomFormat, obj)
        assert result == b'{"scheduled_at":"2024/12/25"}'

    def test_format_full(self, impl: Serializer) -> None:
        obj = WithDateTimeCustomFormatFull(created_at=datetime.datetime(2024, 6, 15, 14, 30, 45, tzinfo=datetime.UTC))
        result = impl.dump(WithDateTimeCustomFormatFull, obj)
        assert result == b'{"created_at":"2024-06-15 14:30:45"}'

    def test_missing(self, impl: Serializer) -> None:
        obj = WithDatetimeMissing()
        result = impl.dump(WithDatetimeMissing, obj)
        assert result == b"{}"

    def test_missing_with_value(self, impl: Serializer) -> None:
        obj = WithDatetimeMissing(value=datetime.datetime(2025, 12, 26, 10, 30, 45, tzinfo=datetime.UTC))
        result = impl.dump(WithDatetimeMissing, obj)
        assert result == b'{"value":"2025-12-26T10:30:45+00:00"}'


class TestDatetimeLoad:
    @pytest.mark.parametrize(
        ("data", "expected"),
        [
            # ISO 8601 formats with timezone
            pytest.param(
                b'{"value":"2025-12-26T10:30:45.123456+00:00"}',
                datetime.datetime(2025, 12, 26, 10, 30, 45, 123456, datetime.UTC),
                id="iso_with_microseconds",
            ),
            pytest.param(
                b'{"value":"2025-12-26T10:30:45+00:00"}',
                datetime.datetime(2025, 12, 26, 10, 30, 45, tzinfo=datetime.UTC),
                id="iso_with_offset",
            ),
            pytest.param(
                b'{"value":"2025-12-26T10:30:45Z"}',
                datetime.datetime(2025, 12, 26, 10, 30, 45, tzinfo=datetime.UTC),
                id="iso_with_z",
            ),
            # Without timezone (assumes UTC)
            pytest.param(
                b'{"value":"2025-12-26T10:30:45"}',
                datetime.datetime(2025, 12, 26, 10, 30, 45, tzinfo=datetime.UTC),
                id="iso_no_tz",
            ),
            pytest.param(
                b'{"value":"2025-12-26 10:30:45"}',
                datetime.datetime(2025, 12, 26, 10, 30, 45, tzinfo=datetime.UTC),
                id="space_separator",
            ),
            # Edge cases: midnight, end of day
            pytest.param(
                b'{"value":"2025-01-01T00:00:00Z"}',
                datetime.datetime(2025, 1, 1, 0, 0, 0, tzinfo=datetime.UTC),
                id="midnight",
            ),
            pytest.param(
                b'{"value":"2025-12-31T23:59:59Z"}',
                datetime.datetime(2025, 12, 31, 23, 59, 59, tzinfo=datetime.UTC),
                id="end_of_day",
            ),
            pytest.param(
                b'{"value":"2025-12-31T23:59:59.999999Z"}',
                datetime.datetime(2025, 12, 31, 23, 59, 59, 999999, datetime.UTC),
                id="end_of_day_microseconds",
            ),
            # With milliseconds
            pytest.param(
                b'{"value":"2025-06-15T12:30:45.123Z"}',
                datetime.datetime(2025, 6, 15, 12, 30, 45, 123000, datetime.UTC),
                id="with_milliseconds",
            ),
            # Leap year dates
            pytest.param(
                b'{"value":"2024-02-29T12:00:00Z"}',
                datetime.datetime(2024, 2, 29, 12, 0, 0, tzinfo=datetime.UTC),
                id="leap_year",
            ),
            pytest.param(
                b'{"value":"2000-02-29T00:00:00Z"}',
                datetime.datetime(2000, 2, 29, 0, 0, 0, tzinfo=datetime.UTC),
                id="leap_year_2000",
            ),
            # Different timezone offsets
            pytest.param(
                b'{"value":"2025-06-15T12:00:00+05:30"}',
                datetime.datetime(2025, 6, 15, 6, 30, 0, tzinfo=datetime.UTC),
                id="positive_offset",
            ),
            pytest.param(
                b'{"value":"2025-06-15T12:00:00-08:00"}',
                datetime.datetime(2025, 6, 15, 20, 0, 0, tzinfo=datetime.UTC),
                id="negative_offset",
            ),
            # Month boundaries
            pytest.param(
                b'{"value":"2025-01-31T23:59:59Z"}',
                datetime.datetime(2025, 1, 31, 23, 59, 59, tzinfo=datetime.UTC),
                id="jan_31",
            ),
            pytest.param(
                b'{"value":"2025-04-30T12:00:00Z"}',
                datetime.datetime(2025, 4, 30, 12, 0, 0, tzinfo=datetime.UTC),
                id="apr_30",
            ),
            # Unix epoch
            pytest.param(
                b'{"value":"1970-01-01T00:00:00Z"}',
                datetime.datetime(1970, 1, 1, 0, 0, 0, tzinfo=datetime.UTC),
                id="unix_epoch",
            ),
            # Y2K
            pytest.param(
                b'{"value":"2000-01-01T00:00:00Z"}',
                datetime.datetime(2000, 1, 1, 0, 0, 0, tzinfo=datetime.UTC),
                id="y2k",
            ),
            # Various sub-second precision
            pytest.param(
                b'{"value":"2025-06-15T12:30:45.1Z"}',
                datetime.datetime(2025, 6, 15, 12, 30, 45, 100000, datetime.UTC),
                id="1_decimal",
            ),
            pytest.param(
                b'{"value":"2025-06-15T12:30:45.12Z"}',
                datetime.datetime(2025, 6, 15, 12, 30, 45, 120000, datetime.UTC),
                id="2_decimals",
            ),
            # Far future date
            pytest.param(
                b'{"value":"2999-12-31T23:59:59Z"}',
                datetime.datetime(2999, 12, 31, 23, 59, 59, tzinfo=datetime.UTC),
                id="far_future",
            ),
            # Offset with minutes only
            pytest.param(
                b'{"value":"2025-06-15T12:00:00+00:30"}',
                datetime.datetime(2025, 6, 15, 11, 30, 0, tzinfo=datetime.UTC),
                id="offset_30min",
            ),
        ],
    )
    def test_value(self, impl: Serializer, data: bytes, expected: datetime.datetime) -> None:
        result = impl.load(ValueOf[datetime.datetime], data)
        assert result == ValueOf[datetime.datetime](value=expected)

    def test_format_date_only(self, impl: Serializer) -> None:
        data = b'{"scheduled_at":"2024/12/25"}'
        result = impl.load(WithDateTimeCustomFormat, data)
        assert result == WithDateTimeCustomFormat(
            scheduled_at=datetime.datetime(2024, 12, 25, 0, 0, 0, tzinfo=datetime.UTC)
        )

    def test_format_full(self, impl: Serializer) -> None:
        data = b'{"created_at":"2024-06-15 14:30:45"}'
        result = impl.load(WithDateTimeCustomFormatFull, data)
        assert result == WithDateTimeCustomFormatFull(
            created_at=datetime.datetime(2024, 6, 15, 14, 30, 45, tzinfo=datetime.UTC)
        )

    def test_validation_pass(self, impl: Serializer) -> None:
        data = b'{"value":"2020-06-15T10:30:45+00:00"}'
        result = impl.load(WithDatetimeValidation, data)
        assert result == WithDatetimeValidation(value=datetime.datetime(2020, 6, 15, 10, 30, 45, tzinfo=datetime.UTC))

    def test_validation_fail(self, impl: Serializer) -> None:
        data = b'{"value":"1999-12-31T23:59:59+00:00"}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithDatetimeValidation, data)
        assert exc.value.messages == {"value": ["Invalid value."]}

    def test_two_validators_pass(self, impl: Serializer) -> None:
        data = b'{"value":"2050-06-15T10:30:45+00:00"}'
        result = impl.load(WithDatetimeTwoValidators, data)
        assert result == WithDatetimeTwoValidators(
            value=datetime.datetime(2050, 6, 15, 10, 30, 45, tzinfo=datetime.UTC)
        )

    @pytest.mark.parametrize(
        "data", [b'{"value":"1999-12-31T23:59:59+00:00"}', b'{"value":"2150-06-15T10:30:45+00:00"}']
    )
    def test_two_validators_fail(self, impl: Serializer, data: bytes) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithDatetimeTwoValidators, data)
        assert exc.value.messages == {"value": ["Invalid value."]}

    def test_custom_required_error(self, impl: Serializer) -> None:
        data = b"{}"
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithDatetimeRequiredError, data)
        assert exc.value.messages == {"value": ["Custom required message"]}

    def test_custom_none_error(self, impl: Serializer) -> None:
        data = b'{"value":null}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithDatetimeNoneError, data)
        assert exc.value.messages == {"value": ["Custom none message"]}

    def test_custom_invalid_error(self, impl: Serializer) -> None:
        data = b'{"value":"not-a-datetime"}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithDatetimeInvalidError, data)
        assert exc.value.messages == {"value": ["Custom invalid message"]}

    @pytest.mark.parametrize(
        "data", [b'{"value":"not-a-datetime"}', b'{"value":12345}', b'{"value":["2025-12-26T10:30:45+00:00"]}']
    )
    def test_invalid_format(self, impl: Serializer, data: bytes) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[datetime.datetime], data)
        assert exc.value.messages == {"value": ["Not a valid datetime."]}

    @pytest.mark.parametrize(
        "data",
        [
            pytest.param(b'{"value":"2025-02-29T12:00:00Z"}', id="feb_29_non_leap"),
            pytest.param(b'{"value":"2025-04-31T12:00:00Z"}', id="apr_31"),
            pytest.param(b'{"value":"2025-06-31T12:00:00Z"}', id="jun_31"),
            pytest.param(b'{"value":"2025-00-15T12:00:00Z"}', id="month_zero"),
            pytest.param(b'{"value":"2025-13-15T12:00:00Z"}', id="month_13"),
            pytest.param(b'{"value":"2025-01-00T12:00:00Z"}', id="day_zero"),
            pytest.param(b'{"value":"2025-01-32T12:00:00Z"}', id="day_32"),
            pytest.param(b'{"value":"2025-01-15T25:00:00Z"}', id="hour_25"),
            pytest.param(b'{"value":"2025-01-15T12:60:00Z"}', id="minute_60"),
            pytest.param(b'{"value":"2025-01-15T12:00:60Z"}', id="second_60"),
        ],
    )
    def test_invalid_datetime_values(self, impl: Serializer, data: bytes) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[datetime.datetime], data)
        assert exc.value.messages == {"value": ["Not a valid datetime."]}

    def test_missing(self, impl: Serializer) -> None:
        data = b"{}"
        result = impl.load(WithDatetimeMissing, data)
        assert result == WithDatetimeMissing()

    def test_missing_with_value(self, impl: Serializer) -> None:
        data = b'{"value":"2025-12-26T10:30:45+00:00"}'
        result = impl.load(WithDatetimeMissing, data)
        assert result == WithDatetimeMissing(value=datetime.datetime(2025, 12, 26, 10, 30, 45, tzinfo=datetime.UTC))


class TestDatetimeDumpInvalidType:
    """Test that invalid types in datetime fields raise ValidationError on dump."""

    @pytest.mark.parametrize("value", ["2024-01-01T12:00:00", 123])
    def test_invalid_type(self, impl: Serializer, value: object) -> None:
        obj = ValueOf[datetime.datetime](**{"value": value})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(ValueOf[datetime.datetime], obj)


class TestDatetimeEdgeCases:
    """Test datetime edge cases with extreme timezones, nanoseconds, and boundary values."""

    @pytest.mark.parametrize(
        ("data", "expected"),
        [
            # Extreme positive timezone offset (UTC+14, Kiribati)
            pytest.param(
                b'{"value":"2025-06-15T12:00:00+14:00"}',
                datetime.datetime(2025, 6, 14, 22, 0, 0, tzinfo=datetime.UTC),
                id="utc_plus_14",
            ),
            # Extreme negative timezone offset (UTC-12)
            pytest.param(
                b'{"value":"2025-06-15T12:00:00-12:00"}',
                datetime.datetime(2025, 6, 16, 0, 0, 0, tzinfo=datetime.UTC),
                id="utc_minus_12",
            ),
            # Unusual timezone offset (Nepal UTC+05:45)
            pytest.param(
                b'{"value":"2025-06-15T12:00:00+05:45"}',
                datetime.datetime(2025, 6, 15, 6, 15, 0, tzinfo=datetime.UTC),
                id="utc_plus_5_45",
            ),
            # Chatham Islands (UTC+12:45)
            pytest.param(
                b'{"value":"2025-06-15T12:00:00+12:45"}',
                datetime.datetime(2025, 6, 14, 23, 15, 0, tzinfo=datetime.UTC),
                id="utc_plus_12_45",
            ),
        ],
    )
    def test_extreme_timezone_offsets(self, impl: Serializer, data: bytes, expected: datetime.datetime) -> None:
        result = impl.load(ValueOf[datetime.datetime], data)
        assert result == ValueOf[datetime.datetime](value=expected)

    @pytest.mark.parametrize(
        ("data", "expected_microseconds"),
        [
            pytest.param(b'{"value":"2025-06-15T12:30:45.000001Z"}', 1, id="1_microsecond"),
            pytest.param(b'{"value":"2025-06-15T12:30:45.000010Z"}', 10, id="10_microseconds"),
            pytest.param(b'{"value":"2025-06-15T12:30:45.000100Z"}', 100, id="100_microseconds"),
            pytest.param(b'{"value":"2025-06-15T12:30:45.001000Z"}', 1000, id="1_millisecond"),
            pytest.param(b'{"value":"2025-06-15T12:30:45.999999Z"}', 999999, id="max_microseconds"),
        ],
    )
    def test_microsecond_precision(self, impl: Serializer, data: bytes, expected_microseconds: int) -> None:
        result = impl.load(ValueOf[datetime.datetime], data)
        assert result.value.microsecond == expected_microseconds

    def test_roundtrip_preserves_microseconds(self, impl: Serializer) -> None:
        obj = ValueOf[datetime.datetime](value=datetime.datetime(2025, 6, 15, 12, 30, 45, 123456, datetime.UTC))
        result = impl.dump(ValueOf[datetime.datetime], obj)
        loaded = impl.load(ValueOf[datetime.datetime], result)
        assert loaded == obj
        assert loaded.value.microsecond == 123456

    @pytest.mark.parametrize(
        ("value", "id_"),
        [
            pytest.param(datetime.datetime(1, 1, 1, 0, 0, 0, tzinfo=datetime.UTC), "min_year", id="min_datetime"),
            pytest.param(
                datetime.datetime(9999, 12, 31, 23, 59, 59, 999999, datetime.UTC), "max_year", id="max_datetime"
            ),
        ],
    )
    def test_extreme_dates_roundtrip(self, impl: Serializer, value: datetime.datetime, id_: str) -> None:
        obj = ValueOf[datetime.datetime](value=value)
        result = impl.dump(ValueOf[datetime.datetime], obj)
        loaded = impl.load(ValueOf[datetime.datetime], result)
        assert loaded == obj

    def test_century_boundaries(self, impl: Serializer) -> None:
        # Year 2100 (not a leap year, but 2000 was)
        obj = ValueOf[datetime.datetime](value=datetime.datetime(2100, 2, 28, 23, 59, 59, tzinfo=datetime.UTC))
        result = impl.dump(ValueOf[datetime.datetime], obj)
        loaded = impl.load(ValueOf[datetime.datetime], result)
        assert loaded == obj

    def test_year_400_divisible(self, impl: Serializer) -> None:
        # Year 2000 is a leap year (divisible by 400)
        obj = ValueOf[datetime.datetime](value=datetime.datetime(2000, 2, 29, 12, 0, 0, tzinfo=datetime.UTC))
        result = impl.dump(ValueOf[datetime.datetime], obj)
        loaded = impl.load(ValueOf[datetime.datetime], result)
        assert loaded == obj

    def test_daylight_saving_boundary_date(self, impl: Serializer) -> None:
        # March 10, 2024 - typical DST transition date in US
        obj = ValueOf[datetime.datetime](value=datetime.datetime(2024, 3, 10, 2, 30, 0, tzinfo=datetime.UTC))
        result = impl.dump(ValueOf[datetime.datetime], obj)
        loaded = impl.load(ValueOf[datetime.datetime], result)
        assert loaded == obj

    def test_new_year_boundary(self, impl: Serializer) -> None:
        obj = ValueOf[datetime.datetime](value=datetime.datetime(2024, 12, 31, 23, 59, 59, 999999, datetime.UTC))
        result = impl.dump(ValueOf[datetime.datetime], obj)
        loaded = impl.load(ValueOf[datetime.datetime], result)
        assert loaded == obj
