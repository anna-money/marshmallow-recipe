import datetime

import marshmallow
import pytest

import marshmallow_recipe as mr

from .conftest import (
    OptionalValueOf,
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
    def test_value(self, impl: Serializer) -> None:
        obj = ValueOf[datetime.time](value=datetime.time(10, 30, 45, 123456))
        result = impl.dump(ValueOf[datetime.time], obj)
        assert result == b'{"value":"10:30:45.123456"}'

    def test_value_no_microseconds(self, impl: Serializer) -> None:
        obj = ValueOf[datetime.time](value=datetime.time(15, 45, 30))
        result = impl.dump(ValueOf[datetime.time], obj)
        assert result == b'{"value":"15:45:30"}'

    def test_optional_none(self, impl: Serializer) -> None:
        obj = OptionalValueOf[datetime.time](value=None)
        result = impl.dump(OptionalValueOf[datetime.time], obj)
        assert result == b"{}"

    def test_optional_value(self, impl: Serializer) -> None:
        obj = OptionalValueOf[datetime.time](value=datetime.time(10, 30, 45))
        result = impl.dump(OptionalValueOf[datetime.time], obj)
        assert result == b'{"value":"10:30:45"}'

    def test_none_handling_ignore_default(self, impl: Serializer) -> None:
        obj = OptionalValueOf[datetime.time](value=None)
        result = impl.dump(OptionalValueOf[datetime.time], obj)
        assert result == b"{}"

    def test_none_handling_ignore_explicit(self, impl: Serializer) -> None:
        obj = OptionalValueOf[datetime.time](value=None)
        result = impl.dump(OptionalValueOf[datetime.time], obj, none_value_handling=mr.NoneValueHandling.IGNORE)
        assert result == b"{}"

    def test_none_handling_include(self, impl: Serializer) -> None:
        obj = OptionalValueOf[datetime.time](value=None)
        result = impl.dump(OptionalValueOf[datetime.time], obj, none_value_handling=mr.NoneValueHandling.INCLUDE)
        assert result == b'{"value":null}'

    def test_none_handling_include_with_value(self, impl: Serializer) -> None:
        obj = OptionalValueOf[datetime.time](value=datetime.time(10, 30, 45))
        result = impl.dump(OptionalValueOf[datetime.time], obj, none_value_handling=mr.NoneValueHandling.INCLUDE)
        assert result == b'{"value":"10:30:45"}'

    def test_missing(self, impl: Serializer) -> None:
        obj = WithTimeMissing()
        result = impl.dump(WithTimeMissing, obj)
        assert result == b"{}"

    def test_missing_with_value(self, impl: Serializer) -> None:
        obj = WithTimeMissing(value=datetime.time(10, 30, 45))
        result = impl.dump(WithTimeMissing, obj)
        assert result == b'{"value":"10:30:45"}'


class TestTimeLoad:
    def test_value(self, impl: Serializer) -> None:
        data = b'{"value":"10:30:45.123456"}'
        result = impl.load(ValueOf[datetime.time], data)
        assert result == ValueOf[datetime.time](value=datetime.time(10, 30, 45, 123456))

    def test_value_no_microseconds(self, impl: Serializer) -> None:
        data = b'{"value":"15:45:30"}'
        result = impl.load(ValueOf[datetime.time], data)
        assert result == ValueOf[datetime.time](value=datetime.time(15, 45, 30))

    def test_optional_none(self, impl: Serializer) -> None:
        data = b'{"value":null}'
        result = impl.load(OptionalValueOf[datetime.time], data)
        assert result == OptionalValueOf[datetime.time](value=None)

    def test_optional_missing(self, impl: Serializer) -> None:
        data = b"{}"
        result = impl.load(OptionalValueOf[datetime.time], data)
        assert result == OptionalValueOf[datetime.time](value=None)

    def test_optional_value(self, impl: Serializer) -> None:
        data = b'{"value":"10:30:45"}'
        result = impl.load(OptionalValueOf[datetime.time], data)
        assert result == OptionalValueOf[datetime.time](value=datetime.time(10, 30, 45))

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

    def test_two_validators_first_fails(self, impl: Serializer) -> None:
        data = b'{"value":"08:00:00"}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithTimeTwoValidators, data)
        assert exc.value.messages == {"value": ["Invalid value."]}

    def test_two_validators_second_fails(self, impl: Serializer) -> None:
        data = b'{"value":"19:00:00"}'
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

    def test_invalid_format(self, impl: Serializer) -> None:
        data = b'{"value":"not-a-time"}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[datetime.time], data)
        assert exc.value.messages == {"value": ["Not a valid time."]}

    def test_wrong_type_int(self, impl: Serializer) -> None:
        data = b'{"value":12345}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[datetime.time], data)
        assert exc.value.messages == {"value": ["Not a valid time."]}

    def test_wrong_type_list(self, impl: Serializer) -> None:
        data = b'{"value":["10:30:45"]}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[datetime.time], data)
        assert exc.value.messages == {"value": ["Not a valid time."]}

    def test_missing_required(self, impl: Serializer) -> None:
        data = b"{}"
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[datetime.time], data)
        assert exc.value.messages == {"value": ["Missing data for required field."]}

    def test_missing(self, impl: Serializer) -> None:
        data = b"{}"
        result = impl.load(WithTimeMissing, data)
        assert result == WithTimeMissing()

    def test_missing_with_value(self, impl: Serializer) -> None:
        data = b'{"value":"10:30:45"}'
        result = impl.load(WithTimeMissing, data)
        assert result == WithTimeMissing(value=datetime.time(10, 30, 45))
