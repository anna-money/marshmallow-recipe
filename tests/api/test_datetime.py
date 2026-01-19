import datetime

import marshmallow
import pytest

import marshmallow_recipe as mr

from .conftest import (
    OptionalValueOf,
    Serializer,
    ValueOf,
    WithDateTimeCustomFormat,
    WithDateTimeCustomFormatFull,
    WithDateTimeCustomFormatTimezone,
    WithDateTimeFormatDateOnly,
    WithDateTimeFormatHumanReadable,
    WithDateTimeFormatIsoMicroseconds,
    WithDateTimeFormatIsoMicrosecondsZ,
    WithDateTimeFormatIsoNoTz,
    WithDateTimeFormatIsoZ,
    WithDatetimeInvalidError,
    WithDatetimeMissing,
    WithDatetimeNoneError,
    WithDatetimeRequiredError,
    WithDatetimeTwoValidators,
    WithDatetimeValidation,
)


class TestDatetimeDump:
    def test_value(self, impl: Serializer) -> None:
        obj = ValueOf[datetime.datetime](value=datetime.datetime(2025, 12, 26, 10, 30, 45, 123456, datetime.UTC))
        result = impl.dump(ValueOf[datetime.datetime], obj)
        assert result == b'{"value":"2025-12-26T10:30:45.123456+00:00"}'

    def test_microseconds_trailing_zeros(self, impl: Serializer) -> None:
        obj = ValueOf[datetime.datetime](value=datetime.datetime(2025, 12, 26, 10, 30, 45, 100000, datetime.UTC))
        result = impl.dump(ValueOf[datetime.datetime], obj)
        assert result == b'{"value":"2025-12-26T10:30:45.100000+00:00"}'

    def test_format_date_only(self, impl: Serializer) -> None:
        obj = WithDateTimeCustomFormat(scheduled_at=datetime.datetime(2024, 12, 25, 14, 30, 0, tzinfo=datetime.UTC))
        result = impl.dump(WithDateTimeCustomFormat, obj)
        assert result == b'{"scheduled_at":"2024/12/25"}'

    def test_format_full(self, impl: Serializer) -> None:
        obj = WithDateTimeCustomFormatFull(created_at=datetime.datetime(2024, 6, 15, 14, 30, 45, tzinfo=datetime.UTC))
        result = impl.dump(WithDateTimeCustomFormatFull, obj)
        assert result == b'{"created_at":"2024-06-15 14:30:45"}'

    def test_format_with_timezone(self, impl: Serializer) -> None:
        tz = datetime.timezone(datetime.timedelta(hours=3))
        obj = WithDateTimeCustomFormatTimezone(created_at=datetime.datetime(2024, 6, 15, 14, 30, 45, tzinfo=tz))
        result = impl.dump(WithDateTimeCustomFormatTimezone, obj)
        assert result == b'{"created_at":"2024-06-15T14:30:45+0300"}'

    def test_optional_none(self, impl: Serializer) -> None:
        obj = OptionalValueOf[datetime.datetime](value=None)
        result = impl.dump(OptionalValueOf[datetime.datetime], obj)
        assert result == b"{}"

    def test_optional_value(self, impl: Serializer) -> None:
        dt = datetime.datetime(2025, 12, 26, 10, 30, 45, tzinfo=datetime.UTC)
        obj = OptionalValueOf[datetime.datetime](value=dt)
        result = impl.dump(OptionalValueOf[datetime.datetime], obj)
        assert result == b'{"value":"2025-12-26T10:30:45+00:00"}'

    def test_none_handling_ignore_default(self, impl: Serializer) -> None:
        obj = OptionalValueOf[datetime.datetime](value=None)
        result = impl.dump(OptionalValueOf[datetime.datetime], obj)
        assert result == b"{}"

    def test_none_handling_ignore_explicit(self, impl: Serializer) -> None:
        obj = OptionalValueOf[datetime.datetime](value=None)
        result = impl.dump(OptionalValueOf[datetime.datetime], obj, none_value_handling=mr.NoneValueHandling.IGNORE)
        assert result == b"{}"

    def test_none_handling_include(self, impl: Serializer) -> None:
        obj = OptionalValueOf[datetime.datetime](value=None)
        result = impl.dump(OptionalValueOf[datetime.datetime], obj, none_value_handling=mr.NoneValueHandling.INCLUDE)
        assert result == b'{"value":null}'

    def test_none_handling_include_with_value(self, impl: Serializer) -> None:
        dt = datetime.datetime(2025, 12, 26, 10, 30, 45, tzinfo=datetime.UTC)
        obj = OptionalValueOf[datetime.datetime](value=dt)
        result = impl.dump(OptionalValueOf[datetime.datetime], obj, none_value_handling=mr.NoneValueHandling.INCLUDE)
        assert result == b'{"value":"2025-12-26T10:30:45+00:00"}'

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
        "iso_string,expected",
        [
            ("2024-12-26T10:30:45Z", datetime.datetime(2024, 12, 26, 10, 30, 45, tzinfo=datetime.UTC)),
            ("2024-12-26T10:30:45+00:00", datetime.datetime(2024, 12, 26, 10, 30, 45, tzinfo=datetime.UTC)),
            (
                "2024-12-26T10:30:45+03:00",
                datetime.datetime(2024, 12, 26, 10, 30, 45, tzinfo=datetime.timezone(datetime.timedelta(hours=3))),
            ),
            (
                "2024-12-26T10:30:45-05:00",
                datetime.datetime(2024, 12, 26, 10, 30, 45, tzinfo=datetime.timezone(datetime.timedelta(hours=-5))),
            ),
            (
                "2024-12-26T10:30:45+05:30",
                datetime.datetime(
                    2024, 12, 26, 10, 30, 45, tzinfo=datetime.timezone(datetime.timedelta(hours=5, minutes=30))
                ),
            ),
            ("2024-12-26T10:30:45.1Z", datetime.datetime(2024, 12, 26, 10, 30, 45, 100000, datetime.UTC)),
            ("2024-12-26T10:30:45.12Z", datetime.datetime(2024, 12, 26, 10, 30, 45, 120000, datetime.UTC)),
            ("2024-12-26T10:30:45.123Z", datetime.datetime(2024, 12, 26, 10, 30, 45, 123000, datetime.UTC)),
            ("2024-12-26T10:30:45.1234Z", datetime.datetime(2024, 12, 26, 10, 30, 45, 123400, datetime.UTC)),
            ("2024-12-26T10:30:45.12345Z", datetime.datetime(2024, 12, 26, 10, 30, 45, 123450, datetime.UTC)),
            ("2024-12-26T10:30:45.123456Z", datetime.datetime(2024, 12, 26, 10, 30, 45, 123456, datetime.UTC)),
            ("2024-12-26T10:30:45.100000Z", datetime.datetime(2024, 12, 26, 10, 30, 45, 100000, datetime.UTC)),
        ],
    )
    def test_value(self, impl: Serializer, iso_string: str, expected: datetime.datetime) -> None:
        data = f'{{"value":"{iso_string}"}}'.encode()
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

    def test_format_with_timezone(self, impl: Serializer) -> None:
        data = b'{"created_at":"2024-06-15T14:30:45+0300"}'
        result = impl.load(WithDateTimeCustomFormatTimezone, data)
        assert result == WithDateTimeCustomFormatTimezone(
            created_at=datetime.datetime(2024, 6, 15, 14, 30, 45, tzinfo=datetime.timezone(datetime.timedelta(hours=3)))
        )

    def test_optional_none(self, impl: Serializer) -> None:
        data = b'{"value":null}'
        result = impl.load(OptionalValueOf[datetime.datetime], data)
        assert result == OptionalValueOf[datetime.datetime](value=None)

    def test_optional_missing(self, impl: Serializer) -> None:
        data = b"{}"
        result = impl.load(OptionalValueOf[datetime.datetime], data)
        assert result == OptionalValueOf[datetime.datetime](value=None)

    def test_optional_value(self, impl: Serializer) -> None:
        data = b'{"value":"2025-12-26T10:30:45+00:00"}'
        result = impl.load(OptionalValueOf[datetime.datetime], data)
        assert result == OptionalValueOf[datetime.datetime](
            value=datetime.datetime(2025, 12, 26, 10, 30, 45, tzinfo=datetime.UTC)
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

    def test_two_validators_first_fails(self, impl: Serializer) -> None:
        data = b'{"value":"1999-12-31T23:59:59+00:00"}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithDatetimeTwoValidators, data)
        assert exc.value.messages == {"value": ["Invalid value."]}

    def test_two_validators_second_fails(self, impl: Serializer) -> None:
        data = b'{"value":"2150-06-15T10:30:45+00:00"}'
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

    def test_invalid_format(self, impl: Serializer) -> None:
        data = b'{"value":"not-a-datetime"}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[datetime.datetime], data)
        assert exc.value.messages == {"value": ["Not a valid datetime."]}

    def test_wrong_type_int(self, impl: Serializer) -> None:
        data = b'{"value":12345}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[datetime.datetime], data)
        assert exc.value.messages == {"value": ["Not a valid datetime."]}

    def test_wrong_type_list(self, impl: Serializer) -> None:
        data = b'{"value":["2025-12-26T10:30:45+00:00"]}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[datetime.datetime], data)
        assert exc.value.messages == {"value": ["Not a valid datetime."]}

    def test_missing_required(self, impl: Serializer) -> None:
        data = b"{}"
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[datetime.datetime], data)
        assert exc.value.messages == {"value": ["Missing data for required field."]}

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

    def test_string(self, impl: Serializer) -> None:
        obj = ValueOf[datetime.datetime](**{"value": "2024-01-01T12:00:00"})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(ValueOf[datetime.datetime], obj)

    def test_int(self, impl: Serializer) -> None:
        obj = ValueOf[datetime.datetime](**{"value": 123})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(ValueOf[datetime.datetime], obj)


class TestDatetimeCustomFormatIsoZ:
    @pytest.mark.parametrize(
        "dt,expected",
        [
            (datetime.datetime(2024, 6, 15, 14, 30, 45, tzinfo=datetime.UTC), b'{"created_at":"2024-06-15T14:30:45Z"}'),
            (datetime.datetime(2024, 6, 15, 14, 30, 45), b'{"created_at":"2024-06-15T14:30:45Z"}'),
            (
                datetime.datetime(2024, 6, 15, 14, 30, 45, tzinfo=datetime.timezone(datetime.timedelta(hours=3))),
                b'{"created_at":"2024-06-15T14:30:45Z"}',
            ),
        ],
    )
    def test_dump(self, impl: Serializer, dt: datetime.datetime, expected: bytes) -> None:
        obj = WithDateTimeFormatIsoZ(created_at=dt)
        result = impl.dump(WithDateTimeFormatIsoZ, obj)
        assert result == expected

    def test_load(self, impl: Serializer) -> None:
        data = b'{"created_at":"2024-06-15T14:30:45Z"}'
        result = impl.load(WithDateTimeFormatIsoZ, data)
        assert result == WithDateTimeFormatIsoZ(
            created_at=datetime.datetime(2024, 6, 15, 14, 30, 45, tzinfo=datetime.UTC)
        )


class TestDatetimeCustomFormatIsoMicroseconds:
    @pytest.mark.parametrize(
        "dt,expected",
        [
            (
                datetime.datetime(2024, 6, 15, 14, 30, 45, 123456, tzinfo=datetime.UTC),
                b'{"created_at":"2024-06-15T14:30:45.123456"}',
            ),
            (datetime.datetime(2024, 6, 15, 14, 30, 45, 123456), b'{"created_at":"2024-06-15T14:30:45.123456"}'),
            (
                datetime.datetime(
                    2024, 6, 15, 14, 30, 45, 123456, tzinfo=datetime.timezone(datetime.timedelta(hours=3))
                ),
                b'{"created_at":"2024-06-15T14:30:45.123456"}',
            ),
        ],
    )
    def test_dump(self, impl: Serializer, dt: datetime.datetime, expected: bytes) -> None:
        obj = WithDateTimeFormatIsoMicroseconds(created_at=dt)
        result = impl.dump(WithDateTimeFormatIsoMicroseconds, obj)
        assert result == expected

    def test_load(self, impl: Serializer) -> None:
        data = b'{"created_at":"2024-06-15T14:30:45.123456"}'
        result = impl.load(WithDateTimeFormatIsoMicroseconds, data)
        assert result == WithDateTimeFormatIsoMicroseconds(
            created_at=datetime.datetime(2024, 6, 15, 14, 30, 45, 123456, tzinfo=datetime.UTC)
        )

    def test_load_trailing_zeros(self, impl: Serializer) -> None:
        data = b'{"created_at":"2024-06-15T14:30:45.100000"}'
        result = impl.load(WithDateTimeFormatIsoMicroseconds, data)
        assert result == WithDateTimeFormatIsoMicroseconds(
            created_at=datetime.datetime(2024, 6, 15, 14, 30, 45, 100000, tzinfo=datetime.UTC)
        )


class TestDatetimeCustomFormatIsoMicrosecondsZ:
    @pytest.mark.parametrize(
        "dt,expected",
        [
            (
                datetime.datetime(2024, 6, 15, 14, 30, 45, 123456, tzinfo=datetime.UTC),
                b'{"created_at":"2024-06-15T14:30:45.123456Z"}',
            ),
            (datetime.datetime(2024, 6, 15, 14, 30, 45, 123456), b'{"created_at":"2024-06-15T14:30:45.123456Z"}'),
            (
                datetime.datetime(
                    2024, 6, 15, 14, 30, 45, 123456, tzinfo=datetime.timezone(datetime.timedelta(hours=3))
                ),
                b'{"created_at":"2024-06-15T14:30:45.123456Z"}',
            ),
        ],
    )
    def test_dump(self, impl: Serializer, dt: datetime.datetime, expected: bytes) -> None:
        obj = WithDateTimeFormatIsoMicrosecondsZ(created_at=dt)
        result = impl.dump(WithDateTimeFormatIsoMicrosecondsZ, obj)
        assert result == expected

    def test_load(self, impl: Serializer) -> None:
        data = b'{"created_at":"2024-06-15T14:30:45.123456Z"}'
        result = impl.load(WithDateTimeFormatIsoMicrosecondsZ, data)
        assert result == WithDateTimeFormatIsoMicrosecondsZ(
            created_at=datetime.datetime(2024, 6, 15, 14, 30, 45, 123456, tzinfo=datetime.UTC)
        )


class TestDatetimeCustomFormatIsoNoTz:
    @pytest.mark.parametrize(
        "dt,expected",
        [
            (datetime.datetime(2024, 6, 15, 14, 30, 45, tzinfo=datetime.UTC), b'{"created_at":"2024-06-15T14:30:45"}'),
            (datetime.datetime(2024, 6, 15, 14, 30, 45), b'{"created_at":"2024-06-15T14:30:45"}'),
            (
                datetime.datetime(2024, 6, 15, 14, 30, 45, tzinfo=datetime.timezone(datetime.timedelta(hours=3))),
                b'{"created_at":"2024-06-15T14:30:45"}',
            ),
        ],
    )
    def test_dump(self, impl: Serializer, dt: datetime.datetime, expected: bytes) -> None:
        obj = WithDateTimeFormatIsoNoTz(created_at=dt)
        result = impl.dump(WithDateTimeFormatIsoNoTz, obj)
        assert result == expected

    def test_load(self, impl: Serializer) -> None:
        data = b'{"created_at":"2024-06-15T14:30:45"}'
        result = impl.load(WithDateTimeFormatIsoNoTz, data)
        assert result == WithDateTimeFormatIsoNoTz(
            created_at=datetime.datetime(2024, 6, 15, 14, 30, 45, tzinfo=datetime.UTC)
        )


class TestDatetimeCustomFormatHumanReadable:
    @pytest.mark.parametrize(
        "dt,expected",
        [
            (datetime.datetime(2024, 1, 15, 14, 30, 45, tzinfo=datetime.UTC), b'{"created_at":"15 January 2024"}'),
            (datetime.datetime(2024, 1, 15, 14, 30, 45), b'{"created_at":"15 January 2024"}'),
            (
                datetime.datetime(2024, 1, 15, 14, 30, 45, tzinfo=datetime.timezone(datetime.timedelta(hours=3))),
                b'{"created_at":"15 January 2024"}',
            ),
        ],
    )
    def test_dump(self, impl: Serializer, dt: datetime.datetime, expected: bytes) -> None:
        obj = WithDateTimeFormatHumanReadable(created_at=dt)
        result = impl.dump(WithDateTimeFormatHumanReadable, obj)
        assert result == expected

    def test_load(self, impl: Serializer) -> None:
        data = b'{"created_at":"15 January 2024"}'
        result = impl.load(WithDateTimeFormatHumanReadable, data)
        assert result == WithDateTimeFormatHumanReadable(
            created_at=datetime.datetime(2024, 1, 15, 0, 0, 0, tzinfo=datetime.UTC)
        )


class TestDatetimeCustomFormatDateOnly:
    @pytest.mark.parametrize(
        "dt,expected",
        [
            (datetime.datetime(2024, 1, 15, 14, 30, 45, tzinfo=datetime.UTC), b'{"created_at":"2024-01-15"}'),
            (datetime.datetime(2024, 1, 15, 14, 30, 45), b'{"created_at":"2024-01-15"}'),
            (
                datetime.datetime(2024, 1, 15, 14, 30, 45, tzinfo=datetime.timezone(datetime.timedelta(hours=3))),
                b'{"created_at":"2024-01-15"}',
            ),
        ],
    )
    def test_dump(self, impl: Serializer, dt: datetime.datetime, expected: bytes) -> None:
        obj = WithDateTimeFormatDateOnly(created_at=dt)
        result = impl.dump(WithDateTimeFormatDateOnly, obj)
        assert result == expected

    def test_load(self, impl: Serializer) -> None:
        data = b'{"created_at":"2024-01-15"}'
        result = impl.load(WithDateTimeFormatDateOnly, data)
        assert result == WithDateTimeFormatDateOnly(
            created_at=datetime.datetime(2024, 1, 15, 0, 0, 0, tzinfo=datetime.UTC)
        )
