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
    WithDateTimeFormatIso,
    WithDateTimeFormatIsoMicroseconds,
    WithDateTimeFormatIsoMicrosecondsZ,
    WithDateTimeFormatIsoNoTz,
    WithDateTimeFormatIsoZ,
    WithDateTimeFormatTimestamp,
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

    def test_microseconds_millis_only(self, impl: Serializer) -> None:
        obj = ValueOf[datetime.datetime](value=datetime.datetime(2025, 12, 26, 10, 30, 45, 100000, datetime.UTC))
        result = impl.dump(ValueOf[datetime.datetime], obj)
        assert result in (b'{"value":"2025-12-26T10:30:45.100+00:00"}', b'{"value":"2025-12-26T10:30:45.100000+00:00"}')

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

    def test_invalid_type_string(self, impl: Serializer) -> None:
        obj = ValueOf[datetime.datetime](**{"value": "2024-01-01T12:00:00"})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.dump(ValueOf[datetime.datetime], obj)
        if impl.supports_proper_validation_errors_on_dump:
            assert exc.value.messages == {"value": ["Not a valid datetime."]}

    def test_invalid_type_int(self, impl: Serializer) -> None:
        obj = ValueOf[datetime.datetime](**{"value": 123})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.dump(ValueOf[datetime.datetime], obj)
        if impl.supports_proper_validation_errors_on_dump:
            assert exc.value.messages == {"value": ["Not a valid datetime."]}

    def test_custom_invalid_error(self, impl: Serializer) -> None:
        obj = WithDatetimeInvalidError(**{"value": "2024-01-01"})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.dump(WithDatetimeInvalidError, obj)
        if impl.supports_proper_validation_errors_on_dump:
            assert exc.value.messages == {"value": ["Custom invalid message"]}

    @pytest.mark.parametrize(
        ("obj", "expected"),
        [
            (
                WithDateTimeFormatIsoZ(created_at=datetime.datetime(2024, 6, 15, 14, 30, 45, tzinfo=datetime.UTC)),
                b'{"created_at":"2024-06-15T14:30:45Z"}',
            ),
            (
                WithDateTimeFormatIsoZ(created_at=datetime.datetime(2024, 6, 15, 14, 30, 45)),
                b'{"created_at":"2024-06-15T14:30:45Z"}',
            ),
            pytest.param(
                WithDateTimeFormatIsoZ(
                    created_at=datetime.datetime(
                        2024, 6, 15, 14, 30, 45, tzinfo=datetime.timezone(datetime.timedelta(hours=3))
                    )
                ),
                b'{"created_at":"2024-06-15T14:30:45Z"}',
                id="timezone_offset",
            ),
        ],
    )
    def test_format_iso_z(self, impl: Serializer, obj: WithDateTimeFormatIsoZ, expected: bytes) -> None:
        result = impl.dump(WithDateTimeFormatIsoZ, obj)
        assert result == expected

    @pytest.mark.parametrize(
        ("obj", "expected"),
        [
            (
                WithDateTimeFormatIsoMicroseconds(
                    created_at=datetime.datetime(2024, 6, 15, 14, 30, 45, 123456, tzinfo=datetime.UTC)
                ),
                b'{"created_at":"2024-06-15T14:30:45.123456"}',
            ),
            (
                WithDateTimeFormatIsoMicroseconds(created_at=datetime.datetime(2024, 6, 15, 14, 30, 45, 123456)),
                b'{"created_at":"2024-06-15T14:30:45.123456"}',
            ),
            pytest.param(
                WithDateTimeFormatIsoMicroseconds(
                    created_at=datetime.datetime(
                        2024, 6, 15, 14, 30, 45, 123456, tzinfo=datetime.timezone(datetime.timedelta(hours=3))
                    )
                ),
                b'{"created_at":"2024-06-15T14:30:45.123456"}',
                id="timezone_offset",
            ),
        ],
    )
    def test_format_iso_microseconds(
        self, impl: Serializer, obj: WithDateTimeFormatIsoMicroseconds, expected: bytes
    ) -> None:
        result = impl.dump(WithDateTimeFormatIsoMicroseconds, obj)
        assert result == expected

    @pytest.mark.parametrize(
        ("obj", "expected"),
        [
            (
                WithDateTimeFormatIsoMicrosecondsZ(
                    created_at=datetime.datetime(2024, 6, 15, 14, 30, 45, 123456, tzinfo=datetime.UTC)
                ),
                b'{"created_at":"2024-06-15T14:30:45.123456Z"}',
            ),
            (
                WithDateTimeFormatIsoMicrosecondsZ(created_at=datetime.datetime(2024, 6, 15, 14, 30, 45, 123456)),
                b'{"created_at":"2024-06-15T14:30:45.123456Z"}',
            ),
            pytest.param(
                WithDateTimeFormatIsoMicrosecondsZ(
                    created_at=datetime.datetime(
                        2024, 6, 15, 14, 30, 45, 123456, tzinfo=datetime.timezone(datetime.timedelta(hours=3))
                    )
                ),
                b'{"created_at":"2024-06-15T14:30:45.123456Z"}',
                id="timezone_offset",
            ),
        ],
    )
    def test_format_iso_microseconds_z(
        self, impl: Serializer, obj: WithDateTimeFormatIsoMicrosecondsZ, expected: bytes
    ) -> None:
        result = impl.dump(WithDateTimeFormatIsoMicrosecondsZ, obj)
        assert result == expected

    @pytest.mark.parametrize(
        ("obj", "expected"),
        [
            (
                WithDateTimeFormatIsoNoTz(created_at=datetime.datetime(2024, 6, 15, 14, 30, 45, tzinfo=datetime.UTC)),
                b'{"created_at":"2024-06-15T14:30:45"}',
            ),
            (
                WithDateTimeFormatIsoNoTz(created_at=datetime.datetime(2024, 6, 15, 14, 30, 45)),
                b'{"created_at":"2024-06-15T14:30:45"}',
            ),
            pytest.param(
                WithDateTimeFormatIsoNoTz(
                    created_at=datetime.datetime(
                        2024, 6, 15, 14, 30, 45, tzinfo=datetime.timezone(datetime.timedelta(hours=3))
                    )
                ),
                b'{"created_at":"2024-06-15T14:30:45"}',
                id="timezone_offset",
            ),
        ],
    )
    def test_format_iso_no_tz(self, impl: Serializer, obj: WithDateTimeFormatIsoNoTz, expected: bytes) -> None:
        result = impl.dump(WithDateTimeFormatIsoNoTz, obj)
        assert result == expected

    @pytest.mark.parametrize(
        ("obj", "expected"),
        [
            (
                WithDateTimeFormatHumanReadable(
                    created_at=datetime.datetime(2024, 1, 15, 14, 30, 45, tzinfo=datetime.UTC)
                ),
                b'{"created_at":"15 January 2024"}',
            ),
            (
                WithDateTimeFormatHumanReadable(created_at=datetime.datetime(2024, 1, 15, 14, 30, 45)),
                b'{"created_at":"15 January 2024"}',
            ),
            pytest.param(
                WithDateTimeFormatHumanReadable(
                    created_at=datetime.datetime(
                        2024, 1, 15, 14, 30, 45, tzinfo=datetime.timezone(datetime.timedelta(hours=3))
                    )
                ),
                b'{"created_at":"15 January 2024"}',
                id="timezone_offset",
            ),
        ],
    )
    def test_format_human_readable(
        self, impl: Serializer, obj: WithDateTimeFormatHumanReadable, expected: bytes
    ) -> None:
        result = impl.dump(WithDateTimeFormatHumanReadable, obj)
        assert result == expected

    @pytest.mark.parametrize(
        ("obj", "expected"),
        [
            (
                WithDateTimeFormatDateOnly(created_at=datetime.datetime(2024, 1, 15, 14, 30, 45, tzinfo=datetime.UTC)),
                b'{"created_at":"2024-01-15"}',
            ),
            (
                WithDateTimeFormatDateOnly(created_at=datetime.datetime(2024, 1, 15, 14, 30, 45)),
                b'{"created_at":"2024-01-15"}',
            ),
            pytest.param(
                WithDateTimeFormatDateOnly(
                    created_at=datetime.datetime(
                        2024, 1, 15, 14, 30, 45, tzinfo=datetime.timezone(datetime.timedelta(hours=3))
                    )
                ),
                b'{"created_at":"2024-01-15"}',
                id="timezone_offset",
            ),
        ],
    )
    def test_format_date_only_custom(self, impl: Serializer, obj: WithDateTimeFormatDateOnly, expected: bytes) -> None:
        result = impl.dump(WithDateTimeFormatDateOnly, obj)
        assert result == expected

    def test_format_iso_microsecond_precision(self, impl: Serializer) -> None:
        obj = WithDateTimeFormatIso(created_at=datetime.datetime(2024, 6, 15, 14, 30, 45, 100000, tzinfo=datetime.UTC))
        result = impl.dump(WithDateTimeFormatIso, obj)
        assert result in (
            b'{"created_at":"2024-06-15T14:30:45.100000+00:00"}',
            b'{"created_at":"2024-06-15T14:30:45.100+00:00"}',
            b'{"created_at":"2024-06-15T14:30:45.1+00:00"}',
        )

    @pytest.mark.parametrize(
        ("obj", "expected"),
        [
            (
                WithDateTimeFormatIso(created_at=datetime.datetime(2024, 6, 15, 14, 30, 45, tzinfo=datetime.UTC)),
                b'{"created_at":"2024-06-15T14:30:45+00:00"}',
            ),
            (
                WithDateTimeFormatIso(
                    created_at=datetime.datetime(2024, 6, 15, 14, 30, 45, 123456, tzinfo=datetime.UTC)
                ),
                b'{"created_at":"2024-06-15T14:30:45.123456+00:00"}',
            ),
            pytest.param(
                WithDateTimeFormatIso(
                    created_at=datetime.datetime(
                        2024, 6, 15, 14, 30, 45, tzinfo=datetime.timezone(datetime.timedelta(hours=3))
                    )
                ),
                b'{"created_at":"2024-06-15T14:30:45+03:00"}',
                id="timezone_offset",
            ),
        ],
    )
    def test_format_iso(self, impl: Serializer, obj: WithDateTimeFormatIso, expected: bytes) -> None:
        result = impl.dump(WithDateTimeFormatIso, obj)
        assert result == expected

    @pytest.mark.parametrize(
        ("obj", "expected"),
        [
            (
                WithDateTimeFormatTimestamp(created_at=datetime.datetime(2024, 6, 15, 14, 30, 45, tzinfo=datetime.UTC)),
                b'{"created_at":1718461845.0}',
            ),
            (
                WithDateTimeFormatTimestamp(created_at=datetime.datetime(1970, 1, 1, 0, 0, 0, tzinfo=datetime.UTC)),
                b'{"created_at":0.0}',
            ),
            pytest.param(
                WithDateTimeFormatTimestamp(
                    created_at=datetime.datetime(
                        2024, 6, 15, 14, 30, 45, tzinfo=datetime.timezone(datetime.timedelta(hours=3))
                    )
                ),
                b'{"created_at":1718451045.0}',
                id="timezone_offset",
            ),
            pytest.param(
                WithDateTimeFormatTimestamp(
                    created_at=datetime.datetime(2024, 6, 15, 14, 30, 45, 123456, tzinfo=datetime.UTC)
                ),
                b'{"created_at":1718461845.123456}',
                id="with_microseconds",
            ),
        ],
    )
    def test_format_timestamp(self, impl: Serializer, obj: WithDateTimeFormatTimestamp, expected: bytes) -> None:
        result = impl.dump(WithDateTimeFormatTimestamp, obj)
        assert result == expected

    @pytest.mark.parametrize(
        "dt",
        [
            datetime.datetime(1969, 12, 31, 23, 59, 59, tzinfo=datetime.UTC),
            datetime.datetime(1969, 12, 31, 23, 59, 59, 500000, tzinfo=datetime.UTC),
            datetime.datetime(1960, 1, 1, 0, 0, 0, tzinfo=datetime.UTC),
        ],
    )
    def test_format_timestamp_negative_rejected(self, impl: Serializer, dt: datetime.datetime) -> None:
        obj = WithDateTimeFormatTimestamp(created_at=dt)
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.dump(WithDateTimeFormatTimestamp, obj)
        assert exc.value.messages == {"created_at": ["Not a valid datetime."]}


class TestDatetimeLoad:
    @pytest.mark.parametrize(
        ("data", "expected"),
        [
            (
                b'{"value":"2024-12-26T10:30:45Z"}',
                ValueOf[datetime.datetime](value=datetime.datetime(2024, 12, 26, 10, 30, 45, tzinfo=datetime.UTC)),
            ),
            (
                b'{"value":"2024-12-26T10:30:45+00:00"}',
                ValueOf[datetime.datetime](value=datetime.datetime(2024, 12, 26, 10, 30, 45, tzinfo=datetime.UTC)),
            ),
            pytest.param(
                b'{"value":"2024-12-26T10:30:45+03:00"}',
                ValueOf[datetime.datetime](
                    value=datetime.datetime(
                        2024, 12, 26, 10, 30, 45, tzinfo=datetime.timezone(datetime.timedelta(hours=3))
                    )
                ),
                id="positive_timezone",
            ),
            pytest.param(
                b'{"value":"2024-12-26T10:30:45-05:00"}',
                ValueOf[datetime.datetime](
                    value=datetime.datetime(
                        2024, 12, 26, 10, 30, 45, tzinfo=datetime.timezone(datetime.timedelta(hours=-5))
                    )
                ),
                id="negative_timezone",
            ),
            pytest.param(
                b'{"value":"2024-12-26T10:30:45+05:30"}',
                ValueOf[datetime.datetime](
                    value=datetime.datetime(
                        2024, 12, 26, 10, 30, 45, tzinfo=datetime.timezone(datetime.timedelta(hours=5, minutes=30))
                    )
                ),
                id="timezone_with_minutes",
            ),
            (
                b'{"value":"2024-12-26T10:30:45.1Z"}',
                ValueOf[datetime.datetime](value=datetime.datetime(2024, 12, 26, 10, 30, 45, 100000, datetime.UTC)),
            ),
            (
                b'{"value":"2024-12-26T10:30:45.12Z"}',
                ValueOf[datetime.datetime](value=datetime.datetime(2024, 12, 26, 10, 30, 45, 120000, datetime.UTC)),
            ),
            (
                b'{"value":"2024-12-26T10:30:45.123Z"}',
                ValueOf[datetime.datetime](value=datetime.datetime(2024, 12, 26, 10, 30, 45, 123000, datetime.UTC)),
            ),
            (
                b'{"value":"2024-12-26T10:30:45.1234Z"}',
                ValueOf[datetime.datetime](value=datetime.datetime(2024, 12, 26, 10, 30, 45, 123400, datetime.UTC)),
            ),
            (
                b'{"value":"2024-12-26T10:30:45.12345Z"}',
                ValueOf[datetime.datetime](value=datetime.datetime(2024, 12, 26, 10, 30, 45, 123450, datetime.UTC)),
            ),
            (
                b'{"value":"2024-12-26T10:30:45.123456Z"}',
                ValueOf[datetime.datetime](value=datetime.datetime(2024, 12, 26, 10, 30, 45, 123456, datetime.UTC)),
            ),
            (
                b'{"value":"2024-12-26T10:30:45.100000Z"}',
                ValueOf[datetime.datetime](value=datetime.datetime(2024, 12, 26, 10, 30, 45, 100000, datetime.UTC)),
            ),
        ],
    )
    def test_value(self, impl: Serializer, data: bytes, expected: ValueOf[datetime.datetime]) -> None:
        result = impl.load(ValueOf[datetime.datetime], data)
        assert result == expected

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

    def test_format_iso_z(self, impl: Serializer) -> None:
        data = b'{"created_at":"2024-06-15T14:30:45Z"}'
        result = impl.load(WithDateTimeFormatIsoZ, data)
        assert result == WithDateTimeFormatIsoZ(
            created_at=datetime.datetime(2024, 6, 15, 14, 30, 45, tzinfo=datetime.UTC)
        )

    def test_format_iso_microseconds(self, impl: Serializer) -> None:
        data = b'{"created_at":"2024-06-15T14:30:45.123456"}'
        result = impl.load(WithDateTimeFormatIsoMicroseconds, data)
        assert result == WithDateTimeFormatIsoMicroseconds(
            created_at=datetime.datetime(2024, 6, 15, 14, 30, 45, 123456, tzinfo=datetime.UTC)
        )

    def test_format_iso_microseconds_trailing_zeros(self, impl: Serializer) -> None:
        data = b'{"created_at":"2024-06-15T14:30:45.100000"}'
        result = impl.load(WithDateTimeFormatIsoMicroseconds, data)
        assert result == WithDateTimeFormatIsoMicroseconds(
            created_at=datetime.datetime(2024, 6, 15, 14, 30, 45, 100000, tzinfo=datetime.UTC)
        )

    def test_format_iso_microseconds_z(self, impl: Serializer) -> None:
        data = b'{"created_at":"2024-06-15T14:30:45.123456Z"}'
        result = impl.load(WithDateTimeFormatIsoMicrosecondsZ, data)
        assert result == WithDateTimeFormatIsoMicrosecondsZ(
            created_at=datetime.datetime(2024, 6, 15, 14, 30, 45, 123456, tzinfo=datetime.UTC)
        )

    def test_format_iso_no_tz(self, impl: Serializer) -> None:
        data = b'{"created_at":"2024-06-15T14:30:45"}'
        result = impl.load(WithDateTimeFormatIsoNoTz, data)
        assert result == WithDateTimeFormatIsoNoTz(
            created_at=datetime.datetime(2024, 6, 15, 14, 30, 45, tzinfo=datetime.UTC)
        )

    def test_format_human_readable(self, impl: Serializer) -> None:
        data = b'{"created_at":"15 January 2024"}'
        result = impl.load(WithDateTimeFormatHumanReadable, data)
        assert result == WithDateTimeFormatHumanReadable(
            created_at=datetime.datetime(2024, 1, 15, 0, 0, 0, tzinfo=datetime.UTC)
        )

    def test_format_date_only_custom(self, impl: Serializer) -> None:
        data = b'{"created_at":"2024-01-15"}'
        result = impl.load(WithDateTimeFormatDateOnly, data)
        assert result == WithDateTimeFormatDateOnly(
            created_at=datetime.datetime(2024, 1, 15, 0, 0, 0, tzinfo=datetime.UTC)
        )

    @pytest.mark.parametrize(
        ("data", "expected"),
        [
            (
                b'{"created_at":"2024-06-15T14:30:45+00:00"}',
                WithDateTimeFormatIso(created_at=datetime.datetime(2024, 6, 15, 14, 30, 45, tzinfo=datetime.UTC)),
            ),
            (
                b'{"created_at":"2024-06-15T14:30:45.123456+00:00"}',
                WithDateTimeFormatIso(
                    created_at=datetime.datetime(2024, 6, 15, 14, 30, 45, 123456, tzinfo=datetime.UTC)
                ),
            ),
            pytest.param(
                b'{"created_at":"2024-06-15T14:30:45+03:00"}',
                WithDateTimeFormatIso(
                    created_at=datetime.datetime(
                        2024, 6, 15, 14, 30, 45, tzinfo=datetime.timezone(datetime.timedelta(hours=3))
                    )
                ),
                id="timezone_offset",
            ),
            pytest.param(
                b'{"created_at":"2024-01-15T10:30:00"}',
                WithDateTimeFormatIso(created_at=datetime.datetime(2024, 1, 15, 10, 30, 0, tzinfo=datetime.UTC)),
                id="without_timezone",
            ),
            pytest.param(
                b'{"created_at":"2024-01-15T10:30:00.123456"}',
                WithDateTimeFormatIso(
                    created_at=datetime.datetime(2024, 1, 15, 10, 30, 0, 123456, tzinfo=datetime.UTC)
                ),
                id="without_timezone_microseconds",
            ),
        ],
    )
    def test_format_iso(self, impl: Serializer, data: bytes, expected: WithDateTimeFormatIso) -> None:
        result = impl.load(WithDateTimeFormatIso, data)
        assert result == expected

    @pytest.mark.parametrize(
        ("data", "expected"),
        [
            (
                b'{"created_at":1718461845}',
                WithDateTimeFormatTimestamp(created_at=datetime.datetime(2024, 6, 15, 14, 30, 45, tzinfo=datetime.UTC)),
            ),
            (
                b'{"created_at":1718461845.0}',
                WithDateTimeFormatTimestamp(created_at=datetime.datetime(2024, 6, 15, 14, 30, 45, tzinfo=datetime.UTC)),
            ),
            (
                b'{"created_at":0}',
                WithDateTimeFormatTimestamp(created_at=datetime.datetime(1970, 1, 1, 0, 0, 0, tzinfo=datetime.UTC)),
            ),
            pytest.param(
                b'{"created_at":1718461845.123456}',
                WithDateTimeFormatTimestamp(
                    created_at=datetime.datetime(2024, 6, 15, 14, 30, 45, 123456, tzinfo=datetime.UTC)
                ),
                id="with_microseconds",
            ),
        ],
    )
    def test_format_timestamp(self, impl: Serializer, data: bytes, expected: WithDateTimeFormatTimestamp) -> None:
        result = impl.load(WithDateTimeFormatTimestamp, data)
        assert result == expected

    @pytest.mark.parametrize("value", ["true", "false"])
    def test_format_timestamp_bool_rejected(self, impl: Serializer, value: str) -> None:
        data = f'{{"created_at":{value}}}'.encode()
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithDateTimeFormatTimestamp, data)
        assert exc.value.messages == {"created_at": ["Not a valid datetime."]}

    @pytest.mark.parametrize("timestamp", [-1, -0.5, -1000000])
    def test_format_timestamp_negative_rejected(self, impl: Serializer, timestamp: float) -> None:
        data = f'{{"created_at":{timestamp}}}'.encode()
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithDateTimeFormatTimestamp, data)
        assert exc.value.messages == {"created_at": ["Not a valid datetime."]}


class TestDatetimeFormatValidation:
    @pytest.mark.parametrize(
        "format", [None, "iso", "timestamp", "%Y-%m-%d", "%Y/%m/%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"]
    )
    def test_valid_formats(self, format: str | None) -> None:
        mr.datetime_meta(format=format)

    @pytest.mark.parametrize("format", ["invalid", "ISO", "Timestamp", "unix", "rfc"])
    def test_invalid_formats(self, format: str) -> None:
        with pytest.raises(ValueError, match="Invalid datetime format"):
            mr.datetime_meta(format=format)
