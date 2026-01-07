import datetime

import marshmallow
import pytest

import marshmallow_recipe as mr

from .conftest import (
    OptionalValueOf,
    Serializer,
    ValueOf,
    WithDateInvalidError,
    WithDateMissing,
    WithDateNoneError,
    WithDateRequiredError,
    WithDateTwoValidators,
    WithDateValidation,
)


class TestDateDump:
    def test_value(self, impl: Serializer) -> None:
        obj = ValueOf[datetime.date](value=datetime.date(2025, 12, 26))
        result = impl.dump(ValueOf[datetime.date], obj)
        assert result == b'{"value":"2025-12-26"}'

    def test_datetime_value(self, impl: Serializer) -> None:
        # datetime.datetime inherits from datetime.date, so you can pass a datetime object as a date
        obj = ValueOf[datetime.date](value=datetime.datetime(2025, 12, 26, 10, 30, 45))
        result = impl.dump(ValueOf[datetime.date], obj)
        assert result == b'{"value":"2025-12-26"}'

    def test_optional_none(self, impl: Serializer) -> None:
        obj = OptionalValueOf[datetime.date](value=None)
        result = impl.dump(OptionalValueOf[datetime.date], obj)
        assert result == b"{}"

    def test_optional_value(self, impl: Serializer) -> None:
        obj = OptionalValueOf[datetime.date](value=datetime.date(2025, 12, 26))
        result = impl.dump(OptionalValueOf[datetime.date], obj)
        assert result == b'{"value":"2025-12-26"}'

    def test_none_handling_ignore_default(self, impl: Serializer) -> None:
        obj = OptionalValueOf[datetime.date](value=None)
        result = impl.dump(OptionalValueOf[datetime.date], obj)
        assert result == b"{}"

    def test_none_handling_ignore_explicit(self, impl: Serializer) -> None:
        obj = OptionalValueOf[datetime.date](value=None)
        result = impl.dump(OptionalValueOf[datetime.date], obj, none_value_handling=mr.NoneValueHandling.IGNORE)
        assert result == b"{}"

    def test_none_handling_include(self, impl: Serializer) -> None:
        obj = OptionalValueOf[datetime.date](value=None)
        result = impl.dump(OptionalValueOf[datetime.date], obj, none_value_handling=mr.NoneValueHandling.INCLUDE)
        assert result == b'{"value":null}'

    def test_none_handling_include_with_value(self, impl: Serializer) -> None:
        obj = OptionalValueOf[datetime.date](value=datetime.date(2025, 12, 26))
        result = impl.dump(OptionalValueOf[datetime.date], obj, none_value_handling=mr.NoneValueHandling.INCLUDE)
        assert result == b'{"value":"2025-12-26"}'

    def test_missing(self, impl: Serializer) -> None:
        obj = WithDateMissing()
        result = impl.dump(WithDateMissing, obj)
        assert result == b"{}"

    def test_missing_with_value(self, impl: Serializer) -> None:
        obj = WithDateMissing(value=datetime.date(2025, 12, 26))
        result = impl.dump(WithDateMissing, obj)
        assert result == b'{"value":"2025-12-26"}'


class TestDateLoad:
    def test_value(self, impl: Serializer) -> None:
        data = b'{"value":"2025-12-26"}'
        result = impl.load(ValueOf[datetime.date], data)
        assert result == ValueOf[datetime.date](value=datetime.date(2025, 12, 26))

    def test_optional_none(self, impl: Serializer) -> None:
        data = b'{"value":null}'
        result = impl.load(OptionalValueOf[datetime.date], data)
        assert result == OptionalValueOf[datetime.date](value=None)

    def test_optional_missing(self, impl: Serializer) -> None:
        data = b"{}"
        result = impl.load(OptionalValueOf[datetime.date], data)
        assert result == OptionalValueOf[datetime.date](value=None)

    def test_optional_value(self, impl: Serializer) -> None:
        data = b'{"value":"2025-12-26"}'
        result = impl.load(OptionalValueOf[datetime.date], data)
        assert result == OptionalValueOf[datetime.date](value=datetime.date(2025, 12, 26))

    def test_validation_pass(self, impl: Serializer) -> None:
        data = b'{"value":"2020-06-15"}'
        result = impl.load(WithDateValidation, data)
        assert result == WithDateValidation(value=datetime.date(2020, 6, 15))

    def test_validation_fail(self, impl: Serializer) -> None:
        data = b'{"value":"1999-12-31"}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithDateValidation, data)
        assert exc.value.messages == {"value": ["Invalid value."]}

    def test_two_validators_pass(self, impl: Serializer) -> None:
        data = b'{"value":"2050-06-15"}'
        result = impl.load(WithDateTwoValidators, data)
        assert result == WithDateTwoValidators(value=datetime.date(2050, 6, 15))

    def test_two_validators_first_fails(self, impl: Serializer) -> None:
        data = b'{"value":"1999-12-31"}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithDateTwoValidators, data)
        assert exc.value.messages == {"value": ["Invalid value."]}

    def test_two_validators_second_fails(self, impl: Serializer) -> None:
        data = b'{"value":"2150-06-15"}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithDateTwoValidators, data)
        assert exc.value.messages == {"value": ["Invalid value."]}

    def test_custom_required_error(self, impl: Serializer) -> None:
        data = b"{}"
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithDateRequiredError, data)
        assert exc.value.messages == {"value": ["Custom required message"]}

    def test_custom_none_error(self, impl: Serializer) -> None:
        data = b'{"value":null}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithDateNoneError, data)
        assert exc.value.messages == {"value": ["Custom none message"]}

    def test_custom_invalid_error(self, impl: Serializer) -> None:
        data = b'{"value":"not-a-date"}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithDateInvalidError, data)
        assert exc.value.messages == {"value": ["Custom invalid message"]}

    def test_invalid_format(self, impl: Serializer) -> None:
        data = b'{"value":"not-a-date"}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[datetime.date], data)
        assert exc.value.messages == {"value": ["Not a valid date."]}

    def test_wrong_type_int(self, impl: Serializer) -> None:
        data = b'{"value":12345}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[datetime.date], data)
        assert exc.value.messages == {"value": ["Not a valid date."]}

    def test_wrong_type_list(self, impl: Serializer) -> None:
        data = b'{"value":["2025-12-26"]}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[datetime.date], data)
        assert exc.value.messages == {"value": ["Not a valid date."]}

    def test_missing_required(self, impl: Serializer) -> None:
        data = b"{}"
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[datetime.date], data)
        assert exc.value.messages == {"value": ["Missing data for required field."]}

    def test_missing(self, impl: Serializer) -> None:
        data = b"{}"
        result = impl.load(WithDateMissing, data)
        assert result == WithDateMissing()

    def test_missing_with_value(self, impl: Serializer) -> None:
        data = b'{"value":"2025-12-26"}'
        result = impl.load(WithDateMissing, data)
        assert result == WithDateMissing(value=datetime.date(2025, 12, 26))


class TestDateDumpInvalidType:
    """Test that invalid types in date fields raise ValidationError on dump."""

    def test_string(self, impl: Serializer) -> None:
        obj = ValueOf[datetime.date](**{"value": "2024-01-01"})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(ValueOf[datetime.date], obj)

    def test_int(self, impl: Serializer) -> None:
        obj = ValueOf[datetime.date](**{"value": 123})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(ValueOf[datetime.date], obj)
