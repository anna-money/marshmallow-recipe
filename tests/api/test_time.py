import datetime

import marshmallow
import pytest

from .conftest import (
    Serializer,
    ValueOf,
    WithTimeInvalidError,
    WithTimeMissing,
    WithTimeNoneError,
    WithTimeRequiredError,
    WithTimeTwoValidators,
    WithTimeValidation,
)


class TestTimeDump:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            pytest.param(datetime.time(10, 30, 45, 123456), b'{"value":"10:30:45.123456"}', id="with_microseconds"),
            pytest.param(datetime.time(15, 45, 30), b'{"value":"15:45:30"}', id="standard"),
            pytest.param(datetime.time(0, 0, 0), b'{"value":"00:00:00"}', id="midnight"),
            pytest.param(datetime.time(23, 59, 59), b'{"value":"23:59:59"}', id="end_of_day"),
            pytest.param(
                datetime.time(23, 59, 59, 999999), b'{"value":"23:59:59.999999"}', id="end_of_day_microseconds"
            ),
            pytest.param(datetime.time(12, 0, 0), b'{"value":"12:00:00"}', id="noon"),
            pytest.param(datetime.time(0, 0, 1), b'{"value":"00:00:01"}', id="one_second"),
            pytest.param(datetime.time(0, 1, 0), b'{"value":"00:01:00"}', id="one_minute"),
            pytest.param(datetime.time(1, 0, 0), b'{"value":"01:00:00"}', id="one_hour"),
        ],
    )
    def test_value(self, impl: Serializer, value: datetime.time, expected: bytes) -> None:
        obj = ValueOf[datetime.time](value=value)
        result = impl.dump(ValueOf[datetime.time], obj)
        assert result == expected

    def test_missing(self, impl: Serializer) -> None:
        obj = WithTimeMissing()
        result = impl.dump(WithTimeMissing, obj)
        assert result == b"{}"

    def test_missing_with_value(self, impl: Serializer) -> None:
        obj = WithTimeMissing(value=datetime.time(10, 30, 45))
        result = impl.dump(WithTimeMissing, obj)
        assert result == b'{"value":"10:30:45"}'


class TestTimeLoad:
    @pytest.mark.parametrize(
        ("data", "expected"),
        [
            # With microseconds
            pytest.param(b'{"value":"10:30:45.123456"}', datetime.time(10, 30, 45, 123456), id="with_microseconds"),
            # Without microseconds
            pytest.param(b'{"value":"15:45:30"}', datetime.time(15, 45, 30), id="standard"),
            # Edge cases: midnight, end of day
            pytest.param(b'{"value":"00:00:00"}', datetime.time(0, 0, 0), id="midnight"),
            pytest.param(b'{"value":"23:59:59"}', datetime.time(23, 59, 59), id="end_of_day"),
            pytest.param(
                b'{"value":"23:59:59.999999"}', datetime.time(23, 59, 59, 999999), id="end_of_day_microseconds"
            ),
            # Noon
            pytest.param(b'{"value":"12:00:00"}', datetime.time(12, 0, 0), id="noon"),
            # With milliseconds
            pytest.param(b'{"value":"14:30:00.123"}', datetime.time(14, 30, 0, 123000), id="with_milliseconds"),
            # Single unit times
            pytest.param(b'{"value":"00:00:01"}', datetime.time(0, 0, 1), id="one_second"),
            pytest.param(b'{"value":"00:01:00"}', datetime.time(0, 1, 0), id="one_minute"),
            pytest.param(b'{"value":"01:00:00"}', datetime.time(1, 0, 0), id="one_hour"),
            # Various precision microseconds
            pytest.param(b'{"value":"12:30:45.1"}', datetime.time(12, 30, 45, 100000), id="1_decimal"),
            pytest.param(b'{"value":"12:30:45.12"}', datetime.time(12, 30, 45, 120000), id="2_decimals"),
            pytest.param(b'{"value":"12:30:45.123"}', datetime.time(12, 30, 45, 123000), id="3_decimals"),
            pytest.param(b'{"value":"12:30:45.1234"}', datetime.time(12, 30, 45, 123400), id="4_decimals"),
            pytest.param(b'{"value":"12:30:45.12345"}', datetime.time(12, 30, 45, 123450), id="5_decimals"),
            pytest.param(b'{"value":"12:30:45.123456"}', datetime.time(12, 30, 45, 123456), id="6_decimals"),
        ],
    )
    def test_value(self, impl: Serializer, data: bytes, expected: datetime.time) -> None:
        result = impl.load(ValueOf[datetime.time], data)
        assert result == ValueOf[datetime.time](value=expected)

    def test_validation_pass(self, impl: Serializer) -> None:
        data = b'{"value":"10:30:00"}'
        result = impl.load(WithTimeValidation, data)
        assert result == WithTimeValidation(value=datetime.time(10, 30, 0))

    def test_validation_fail(self, impl: Serializer) -> None:
        data = b'{"value":"08:00:00"}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithTimeValidation, data)
        assert exc.value.messages == {"value": ["Invalid value."]}

    def test_two_validators_pass(self, impl: Serializer) -> None:
        data = b'{"value":"12:00:00"}'
        result = impl.load(WithTimeTwoValidators, data)
        assert result == WithTimeTwoValidators(value=datetime.time(12, 0, 0))

    @pytest.mark.parametrize("data", [b'{"value":"08:00:00"}', b'{"value":"19:00:00"}'])
    def test_two_validators_fail(self, impl: Serializer, data: bytes) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithTimeTwoValidators, data)
        assert exc.value.messages == {"value": ["Invalid value."]}

    def test_custom_required_error(self, impl: Serializer) -> None:
        data = b"{}"
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithTimeRequiredError, data)
        assert exc.value.messages == {"value": ["Custom required message"]}

    def test_custom_none_error(self, impl: Serializer) -> None:
        data = b'{"value":null}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithTimeNoneError, data)
        assert exc.value.messages == {"value": ["Custom none message"]}

    def test_custom_invalid_error(self, impl: Serializer) -> None:
        data = b'{"value":"not-a-time"}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithTimeInvalidError, data)
        assert exc.value.messages == {"value": ["Custom invalid message"]}

    @pytest.mark.parametrize("data", [b'{"value":"not-a-time"}', b'{"value":12345}', b'{"value":["10:30:45"]}'])
    def test_invalid_format(self, impl: Serializer, data: bytes) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[datetime.time], data)
        assert exc.value.messages == {"value": ["Not a valid time."]}

    @pytest.mark.parametrize(
        "data",
        [
            pytest.param(b'{"value":"25:00:00"}', id="hour_25"),
            pytest.param(b'{"value":"24:00:00"}', id="hour_24"),
            pytest.param(b'{"value":"10:60:00"}', id="minute_60"),
            pytest.param(b'{"value":"10:30:60"}', id="second_60"),
            pytest.param(b'{"value":"-1:00:00"}', id="negative_hour"),
            pytest.param(b'{"value":"10:-1:00"}', id="negative_minute"),
        ],
    )
    def test_invalid_time_values(self, impl: Serializer, data: bytes) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[datetime.time], data)
        assert exc.value.messages == {"value": ["Not a valid time."]}

    def test_missing(self, impl: Serializer) -> None:
        data = b"{}"
        result = impl.load(WithTimeMissing, data)
        assert result == WithTimeMissing()

    def test_missing_with_value(self, impl: Serializer) -> None:
        data = b'{"value":"10:30:45"}'
        result = impl.load(WithTimeMissing, data)
        assert result == WithTimeMissing(value=datetime.time(10, 30, 45))


class TestTimeEdgeCases:
    """Test time edge cases with boundary values and microsecond precision."""

    def test_max_microseconds(self, impl: Serializer) -> None:
        obj = ValueOf[datetime.time](value=datetime.time(23, 59, 59, 999999))
        result = impl.dump(ValueOf[datetime.time], obj)
        loaded = impl.load(ValueOf[datetime.time], result)
        assert loaded == obj
        assert loaded.value.microsecond == 999999

    def test_1_microsecond(self, impl: Serializer) -> None:
        obj = ValueOf[datetime.time](value=datetime.time(12, 30, 45, 1))
        result = impl.dump(ValueOf[datetime.time], obj)
        loaded = impl.load(ValueOf[datetime.time], result)
        assert loaded == obj
        assert loaded.value.microsecond == 1

    @pytest.mark.parametrize(
        ("microseconds", "id_"),
        [
            pytest.param(1, "1us", id="1_microsecond"),
            pytest.param(10, "10us", id="10_microseconds"),
            pytest.param(100, "100us", id="100_microseconds"),
            pytest.param(1000, "1ms", id="1_millisecond"),
            pytest.param(10000, "10ms", id="10_milliseconds"),
            pytest.param(100000, "100ms", id="100_milliseconds"),
            pytest.param(500000, "500ms", id="500_milliseconds"),
            pytest.param(999999, "max", id="max_microseconds"),
        ],
    )
    def test_microsecond_precision_roundtrip(self, impl: Serializer, microseconds: int, id_: str) -> None:
        obj = ValueOf[datetime.time](value=datetime.time(12, 30, 45, microseconds))
        result = impl.dump(ValueOf[datetime.time], obj)
        loaded = impl.load(ValueOf[datetime.time], result)
        assert loaded == obj

    def test_all_zeros(self, impl: Serializer) -> None:
        obj = ValueOf[datetime.time](value=datetime.time(0, 0, 0, 0))
        result = impl.dump(ValueOf[datetime.time], obj)
        loaded = impl.load(ValueOf[datetime.time], result)
        assert loaded == obj

    def test_all_max_values(self, impl: Serializer) -> None:
        obj = ValueOf[datetime.time](value=datetime.time(23, 59, 59, 999999))
        result = impl.dump(ValueOf[datetime.time], obj)
        loaded = impl.load(ValueOf[datetime.time], result)
        assert loaded == obj

    @pytest.mark.parametrize(
        ("hour", "minute", "second"),
        [
            pytest.param(0, 0, 0, id="midnight"),
            pytest.param(12, 0, 0, id="noon"),
            pytest.param(23, 59, 59, id="almost_midnight"),
            pytest.param(6, 0, 0, id="6am"),
            pytest.param(18, 0, 0, id="6pm"),
            pytest.param(3, 0, 0, id="3am"),
            pytest.param(15, 0, 0, id="3pm"),
        ],
    )
    def test_common_times(self, impl: Serializer, hour: int, minute: int, second: int) -> None:
        obj = ValueOf[datetime.time](value=datetime.time(hour, minute, second))
        result = impl.dump(ValueOf[datetime.time], obj)
        loaded = impl.load(ValueOf[datetime.time], result)
        assert loaded == obj

    @pytest.mark.parametrize("hour", list(range(24)))
    def test_all_hours(self, impl: Serializer, hour: int) -> None:
        obj = ValueOf[datetime.time](value=datetime.time(hour, 30, 0))
        result = impl.dump(ValueOf[datetime.time], obj)
        loaded = impl.load(ValueOf[datetime.time], result)
        assert loaded == obj

    def test_single_second(self, impl: Serializer) -> None:
        obj = ValueOf[datetime.time](value=datetime.time(0, 0, 1))
        result = impl.dump(ValueOf[datetime.time], obj)
        loaded = impl.load(ValueOf[datetime.time], result)
        assert loaded == obj

    def test_single_minute(self, impl: Serializer) -> None:
        obj = ValueOf[datetime.time](value=datetime.time(0, 1, 0))
        result = impl.dump(ValueOf[datetime.time], obj)
        loaded = impl.load(ValueOf[datetime.time], result)
        assert loaded == obj

    def test_single_hour(self, impl: Serializer) -> None:
        obj = ValueOf[datetime.time](value=datetime.time(1, 0, 0))
        result = impl.dump(ValueOf[datetime.time], obj)
        loaded = impl.load(ValueOf[datetime.time], result)
        assert loaded == obj
