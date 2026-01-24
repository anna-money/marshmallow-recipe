import datetime

import marshmallow
import marshmallow_recipe as mr
import pytest

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
    @pytest.mark.parametrize(
        ("obj", "expected"),
        [
            (ValueOf[datetime.time](value=datetime.time(10, 30, 45, 123456)), b'{"value":"10:30:45.123456"}'),
            (ValueOf[datetime.time](value=datetime.time(15, 45, 30)), b'{"value":"15:45:30"}'),
        ],
    )
    def test_value(self, impl: Serializer, obj: ValueOf[datetime.time], expected: bytes) -> None:
        result = impl.dump(ValueOf[datetime.time], obj)
        assert result == expected

    def test_optional_none(self, impl: Serializer) -> None:
        obj = OptionalValueOf[datetime.time](value=None)
        result = impl.dump(OptionalValueOf[datetime.time], obj)
        assert result == b"{}"

    def test_optional_value(self, impl: Serializer) -> None:
        obj = OptionalValueOf[datetime.time](value=datetime.time(10, 30, 45))
        result = impl.dump(OptionalValueOf[datetime.time], obj)
        assert result == b'{"value":"10:30:45"}'

    @pytest.mark.parametrize(
        ("none_value_handling", "expected"),
        [(None, b"{}"), (mr.NoneValueHandling.IGNORE, b"{}"), (mr.NoneValueHandling.INCLUDE, b'{"value":null}')],
    )
    def test_none_handling(
        self, impl: Serializer, none_value_handling: mr.NoneValueHandling | None, expected: bytes
    ) -> None:
        obj = OptionalValueOf[datetime.time](value=None)
        if none_value_handling is None:
            result = impl.dump(OptionalValueOf[datetime.time], obj)
        else:
            result = impl.dump(OptionalValueOf[datetime.time], obj, none_value_handling=none_value_handling)
        assert result == expected

    def test_none_handling_include_with_value(self, impl: Serializer) -> None:
        obj = OptionalValueOf[datetime.time](value=datetime.time(10, 30, 45))
        result = impl.dump(OptionalValueOf[datetime.time], obj, none_value_handling=mr.NoneValueHandling.INCLUDE)
        assert result == b'{"value":"10:30:45"}'

    @pytest.mark.parametrize(
        ("obj", "expected"),
        [(WithTimeMissing(), b"{}"), (WithTimeMissing(value=datetime.time(10, 30, 45)), b'{"value":"10:30:45"}')],
    )
    def test_missing(self, impl: Serializer, obj: WithTimeMissing, expected: bytes) -> None:
        result = impl.dump(WithTimeMissing, obj)
        assert result == expected


class TestTimeLoad:
    @pytest.mark.parametrize(
        ("data", "expected"),
        [
            (b'{"value":"10:30:45.123456"}', ValueOf[datetime.time](value=datetime.time(10, 30, 45, 123456))),
            (b'{"value":"15:45:30"}', ValueOf[datetime.time](value=datetime.time(15, 45, 30))),
        ],
    )
    def test_value(self, impl: Serializer, data: bytes, expected: ValueOf[datetime.time]) -> None:
        result = impl.load(ValueOf[datetime.time], data)
        assert result == expected

    @pytest.mark.parametrize(
        ("data", "expected"),
        [
            (b'{"value":null}', OptionalValueOf[datetime.time](value=None)),
            (b"{}", OptionalValueOf[datetime.time](value=None)),
            (b'{"value":"10:30:45"}', OptionalValueOf[datetime.time](value=datetime.time(10, 30, 45))),
        ],
    )
    def test_optional(self, impl: Serializer, data: bytes, expected: OptionalValueOf[datetime.time]) -> None:
        result = impl.load(OptionalValueOf[datetime.time], data)
        assert result == expected

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

    @pytest.mark.parametrize(
        "data",
        [
            pytest.param(b'{"value":"08:00:00"}', id="first_fails"),
            pytest.param(b'{"value":"19:00:00"}', id="second_fails"),
        ],
    )
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

    @pytest.mark.parametrize(
        "data",
        [
            pytest.param(b'{"value":"not-a-time"}', id="invalid_format"),
            pytest.param(b'{"value":12345}', id="wrong_type_int"),
            pytest.param(b'{"value":["10:30:45"]}', id="wrong_type_list"),
        ],
    )
    def test_invalid_value(self, impl: Serializer, data: bytes) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[datetime.time], data)
        assert exc.value.messages == {"value": ["Not a valid time."]}

    def test_missing_required(self, impl: Serializer) -> None:
        data = b"{}"
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[datetime.time], data)
        assert exc.value.messages == {"value": ["Missing data for required field."]}

    @pytest.mark.parametrize(
        ("data", "expected"),
        [(b"{}", WithTimeMissing()), (b'{"value":"10:30:45"}', WithTimeMissing(value=datetime.time(10, 30, 45)))],
    )
    def test_missing(self, impl: Serializer, data: bytes, expected: WithTimeMissing) -> None:
        result = impl.load(WithTimeMissing, data)
        assert result == expected
