import marshmallow
import pytest

from .conftest import (
    OptionalValueOf,
    Priority,
    Serializer,
    Status,
    ValueOf,
    WithIntEnumMissing,
    WithIntEnumTwoValidators,
    WithIntEnumValidation,
    WithStrEnumMissing,
    WithStrEnumTwoValidators,
    WithStrEnumValidation,
)


class TestEnumDump:
    def test_str_enum(self, impl: Serializer) -> None:
        obj = ValueOf[Status](value=Status.ACTIVE)
        result = impl.dump(ValueOf[Status], obj)
        assert result == b'{"value":"active"}'

    def test_int_enum(self, impl: Serializer) -> None:
        obj = ValueOf[Priority](value=Priority.LOW)
        result = impl.dump(ValueOf[Priority], obj)
        assert result == b'{"value":1}'

    def test_optional_str_enum_none(self, impl: Serializer) -> None:
        obj = OptionalValueOf[Status](value=None)
        result = impl.dump(OptionalValueOf[Status], obj)
        assert result == b"{}"

    def test_optional_str_enum_value(self, impl: Serializer) -> None:
        obj = OptionalValueOf[Status](value=Status.PENDING)
        result = impl.dump(OptionalValueOf[Status], obj)
        assert result == b'{"value":"pending"}'

    def test_optional_int_enum_none(self, impl: Serializer) -> None:
        obj = OptionalValueOf[Priority](value=None)
        result = impl.dump(OptionalValueOf[Priority], obj)
        assert result == b"{}"

    def test_optional_int_enum_value(self, impl: Serializer) -> None:
        obj = OptionalValueOf[Priority](value=Priority.HIGH)
        result = impl.dump(OptionalValueOf[Priority], obj)
        assert result == b'{"value":3}'

    def test_str_enum_missing(self, impl: Serializer) -> None:
        obj = WithStrEnumMissing()
        result = impl.dump(WithStrEnumMissing, obj)
        assert result == b"{}"

    def test_str_enum_missing_with_value(self, impl: Serializer) -> None:
        obj = WithStrEnumMissing(status=Status.ACTIVE)
        result = impl.dump(WithStrEnumMissing, obj)
        assert result == b'{"status":"active"}'

    def test_int_enum_missing(self, impl: Serializer) -> None:
        obj = WithIntEnumMissing()
        result = impl.dump(WithIntEnumMissing, obj)
        assert result == b"{}"

    def test_int_enum_missing_with_value(self, impl: Serializer) -> None:
        obj = WithIntEnumMissing(priority=Priority.HIGH)
        result = impl.dump(WithIntEnumMissing, obj)
        assert result == b'{"priority":3}'


class TestEnumLoad:
    def test_str_enum(self, impl: Serializer) -> None:
        data = b'{"value":"inactive"}'
        result = impl.load(ValueOf[Status], data)
        assert result == ValueOf[Status](value=Status.INACTIVE)

    def test_int_enum(self, impl: Serializer) -> None:
        data = b'{"value":3}'
        result = impl.load(ValueOf[Priority], data)
        assert result == ValueOf[Priority](value=Priority.HIGH)

    def test_str_enum_invalid_value(self, impl: Serializer) -> None:
        data = b'{"value":"invalid_status"}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[Status], data)
        assert exc.value.messages == {"value": ["Not a valid enum."]}

    def test_int_enum_invalid_value(self, impl: Serializer) -> None:
        data = b'{"value":999}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[Priority], data)
        assert exc.value.messages == {"value": ["Not a valid enum."]}

    def test_str_enum_wrong_type(self, impl: Serializer) -> None:
        data = b'{"value":123}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[Status], data)
        assert exc.value.messages == {"value": ["Not a valid enum."]}

    def test_int_enum_wrong_type(self, impl: Serializer) -> None:
        data = b'{"value":"not_a_number"}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[Priority], data)
        assert exc.value.messages == {"value": ["Not a valid enum."]}

    def test_str_enum_missing_required(self, impl: Serializer) -> None:
        data = b"{}"
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[Status], data)
        assert exc.value.messages == {"value": ["Missing data for required field."]}

    def test_int_enum_missing_required(self, impl: Serializer) -> None:
        data = b"{}"
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[Priority], data)
        assert exc.value.messages == {"value": ["Missing data for required field."]}

    def test_str_enum_validation_pass(self, impl: Serializer) -> None:
        data = b'{"status":"active"}'
        result = impl.load(WithStrEnumValidation, data)
        assert result == WithStrEnumValidation(status=Status.ACTIVE)

    def test_str_enum_validation_fail(self, impl: Serializer) -> None:
        data = b'{"status":"inactive"}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithStrEnumValidation, data)
        assert exc.value.messages == {"status": ["Invalid value."]}

    def test_str_enum_two_validators_pass(self, impl: Serializer) -> None:
        data = b'{"status":"active"}'
        result = impl.load(WithStrEnumTwoValidators, data)
        assert result == WithStrEnumTwoValidators(status=Status.ACTIVE)

    def test_str_enum_two_validators_first_fails(self, impl: Serializer) -> None:
        data = b'{"status":"inactive"}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithStrEnumTwoValidators, data)
        assert exc.value.messages == {"status": ["Invalid value.", "Invalid value."]}

    def test_str_enum_two_validators_second_fails(self, impl: Serializer) -> None:
        data = b'{"status":"pending"}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithStrEnumTwoValidators, data)
        assert exc.value.messages == {"status": ["Invalid value."]}

    def test_int_enum_validation_pass(self, impl: Serializer) -> None:
        data = b'{"priority":2}'
        result = impl.load(WithIntEnumValidation, data)
        assert result == WithIntEnumValidation(priority=Priority.MEDIUM)

    def test_int_enum_validation_fail(self, impl: Serializer) -> None:
        data = b'{"priority":1}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithIntEnumValidation, data)
        assert exc.value.messages == {"priority": ["Invalid value."]}

    def test_int_enum_two_validators_pass(self, impl: Serializer) -> None:
        data = b'{"priority":2}'
        result = impl.load(WithIntEnumTwoValidators, data)
        assert result == WithIntEnumTwoValidators(priority=Priority.MEDIUM)

    def test_int_enum_two_validators_first_fails(self, impl: Serializer) -> None:
        data = b'{"priority":1}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithIntEnumTwoValidators, data)
        assert exc.value.messages == {"priority": ["Invalid value."]}

    def test_int_enum_two_validators_second_fails(self, impl: Serializer) -> None:
        data = b'{"priority":3}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithIntEnumTwoValidators, data)
        assert exc.value.messages == {"priority": ["Invalid value."]}

    def test_str_enum_missing(self, impl: Serializer) -> None:
        data = b"{}"
        result = impl.load(WithStrEnumMissing, data)
        assert result == WithStrEnumMissing()

    def test_str_enum_missing_with_value(self, impl: Serializer) -> None:
        data = b'{"status":"active"}'
        result = impl.load(WithStrEnumMissing, data)
        assert result == WithStrEnumMissing(status=Status.ACTIVE)

    def test_int_enum_missing(self, impl: Serializer) -> None:
        data = b"{}"
        result = impl.load(WithIntEnumMissing, data)
        assert result == WithIntEnumMissing()

    def test_int_enum_missing_with_value(self, impl: Serializer) -> None:
        data = b'{"priority":3}'
        result = impl.load(WithIntEnumMissing, data)
        assert result == WithIntEnumMissing(priority=Priority.HIGH)

    @pytest.mark.parametrize("value", ["true", "false"])
    def test_int_enum_bool_rejected(self, impl: Serializer, value: str) -> None:
        data = f'{{"value":{value}}}'.encode()
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[Priority], data)
        assert exc.value.messages == {"value": ["Not a valid enum."]}


class TestEnumDumpInvalidType:
    """Test that invalid types in enum fields raise ValidationError on dump."""

    def test_str_enum_with_string(self, impl: Serializer) -> None:
        obj = ValueOf[Status](value="active")  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(ValueOf[Status], obj)

    def test_str_enum_with_int(self, impl: Serializer) -> None:
        obj = ValueOf[Status](value=1)  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(ValueOf[Status], obj)

    def test_int_enum_with_int(self, impl: Serializer) -> None:
        obj = ValueOf[Priority](value=1)  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(ValueOf[Priority], obj)

    def test_int_enum_with_string(self, impl: Serializer) -> None:
        obj = ValueOf[Priority](value="high")  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(ValueOf[Priority], obj)
