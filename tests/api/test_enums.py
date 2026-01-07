import marshmallow
import pytest

from .conftest import (
    Priority,
    Serializer,
    Status,
    WithEnums,
    WithIntEnumMissing,
    WithIntEnumTwoValidators,
    WithIntEnumValidation,
    WithStrEnumMissing,
    WithStrEnumTwoValidators,
    WithStrEnumValidation,
)


class TestEnumDump:
    def test_str_enum(self, impl: Serializer) -> None:
        obj = WithEnums(status=Status.ACTIVE, priority=Priority.HIGH, optional_status=None)
        result = impl.dump(WithEnums, obj)
        assert result == b'{"status":"active","priority":3}'

    def test_int_enum(self, impl: Serializer) -> None:
        obj = WithEnums(status=Status.PENDING, priority=Priority.LOW, optional_status=None)
        result = impl.dump(WithEnums, obj)
        assert result == b'{"status":"pending","priority":1}'

    def test_optional_none(self, impl: Serializer) -> None:
        obj = WithEnums(status=Status.ACTIVE, priority=Priority.MEDIUM, optional_status=None)
        result = impl.dump(WithEnums, obj)
        assert result == b'{"status":"active","priority":2}'

    def test_optional_value(self, impl: Serializer) -> None:
        obj = WithEnums(status=Status.ACTIVE, priority=Priority.MEDIUM, optional_status=Status.PENDING)
        result = impl.dump(WithEnums, obj)
        assert result == b'{"status":"active","priority":2,"optional_status":"pending"}'

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
        data = b'{"status":"inactive","priority":2}'
        result = impl.load(WithEnums, data)
        assert result == WithEnums(status=Status.INACTIVE, priority=Priority.MEDIUM, optional_status=None)

    def test_int_enum(self, impl: Serializer) -> None:
        data = b'{"status":"active","priority":3}'
        result = impl.load(WithEnums, data)
        assert result == WithEnums(status=Status.ACTIVE, priority=Priority.HIGH, optional_status=None)

    def test_str_enum_invalid_value(self, impl: Serializer) -> None:
        data = b'{"status":"invalid_status","priority":1}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithEnums, data)
        assert exc.value.messages == {
            "status": ["Not a valid choice: 'invalid_status'. Allowed values: ['active', 'inactive', 'pending']"]
        }

    def test_int_enum_invalid_value(self, impl: Serializer) -> None:
        data = b'{"status":"active","priority":999}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithEnums, data)
        assert exc.value.messages == {"priority": ["Not a valid choice: '999'. Allowed values: [1, 2, 3]"]}

    def test_str_enum_wrong_type(self, impl: Serializer) -> None:
        data = b'{"status":123,"priority":1}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithEnums, data)
        assert exc.value.messages == {
            "status": ["Not a valid choice: '123'. Allowed values: ['active', 'inactive', 'pending']"]
        }

    def test_int_enum_wrong_type(self, impl: Serializer) -> None:
        data = b'{"status":"active","priority":"not_a_number"}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithEnums, data)
        assert exc.value.messages == {"priority": ["Not a valid choice: 'not_a_number'. Allowed values: [1, 2, 3]"]}

    def test_missing_required(self, impl: Serializer) -> None:
        data = b'{"priority":1}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithEnums, data)
        assert exc.value.messages == {"status": ["Missing data for required field."]}

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


class TestEnumDumpInvalidType:
    """Test that invalid types in enum fields raise ValidationError on dump."""

    def test_str_enum_with_string(self, impl: Serializer) -> None:
        obj = WithEnums(**{"status": "active", "priority": Priority.HIGH, "optional_status": None})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(WithEnums, obj)

    def test_str_enum_with_int(self, impl: Serializer) -> None:
        obj = WithEnums(**{"status": 1, "priority": Priority.HIGH, "optional_status": None})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(WithEnums, obj)

    def test_int_enum_with_int(self, impl: Serializer) -> None:
        obj = WithEnums(**{"status": Status.ACTIVE, "priority": 1, "optional_status": None})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(WithEnums, obj)

    def test_int_enum_with_string(self, impl: Serializer) -> None:
        obj = WithEnums(**{"status": Status.ACTIVE, "priority": "high", "optional_status": None})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(WithEnums, obj)
