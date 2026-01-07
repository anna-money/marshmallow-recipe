import uuid

import marshmallow
import pytest

import marshmallow_recipe as mr

from .conftest import (
    OptionalValueOf,
    Serializer,
    ValueOf,
    WithUuidInvalidError,
    WithUuidMissing,
    WithUuidNoneError,
    WithUuidRequiredError,
    WithUuidTwoValidators,
    WithUuidValidation,
)


class TestUuidDump:
    def test_value(self, impl: Serializer) -> None:
        test_uuid = uuid.UUID("12345678-1234-5678-1234-567812345678")
        obj = ValueOf[uuid.UUID](value=test_uuid)
        result = impl.dump(ValueOf[uuid.UUID], obj)
        assert result == b'{"value":"12345678-1234-5678-1234-567812345678"}'

    def test_optional_none(self, impl: Serializer) -> None:
        obj = OptionalValueOf[uuid.UUID](value=None)
        result = impl.dump(OptionalValueOf[uuid.UUID], obj)
        assert result == b"{}"

    def test_optional_value(self, impl: Serializer) -> None:
        test_uuid = uuid.UUID("12345678-1234-5678-1234-567812345678")
        obj = OptionalValueOf[uuid.UUID](value=test_uuid)
        result = impl.dump(OptionalValueOf[uuid.UUID], obj)
        assert result == b'{"value":"12345678-1234-5678-1234-567812345678"}'

    def test_none_handling_ignore_default(self, impl: Serializer) -> None:
        obj = OptionalValueOf[uuid.UUID](value=None)
        result = impl.dump(OptionalValueOf[uuid.UUID], obj)
        assert result == b"{}"

    def test_none_handling_ignore_explicit(self, impl: Serializer) -> None:
        obj = OptionalValueOf[uuid.UUID](value=None)
        result = impl.dump(OptionalValueOf[uuid.UUID], obj, none_value_handling=mr.NoneValueHandling.IGNORE)
        assert result == b"{}"

    def test_none_handling_include(self, impl: Serializer) -> None:
        obj = OptionalValueOf[uuid.UUID](value=None)
        result = impl.dump(OptionalValueOf[uuid.UUID], obj, none_value_handling=mr.NoneValueHandling.INCLUDE)
        assert result == b'{"value":null}'

    def test_none_handling_include_with_value(self, impl: Serializer) -> None:
        test_uuid = uuid.UUID("12345678-1234-5678-1234-567812345678")
        obj = OptionalValueOf[uuid.UUID](value=test_uuid)
        result = impl.dump(OptionalValueOf[uuid.UUID], obj, none_value_handling=mr.NoneValueHandling.INCLUDE)
        assert result == b'{"value":"12345678-1234-5678-1234-567812345678"}'

    def test_missing(self, impl: Serializer) -> None:
        obj = WithUuidMissing()
        result = impl.dump(WithUuidMissing, obj)
        assert result == b"{}"

    def test_missing_with_value(self, impl: Serializer) -> None:
        test_uuid = uuid.UUID("12345678-1234-5678-1234-567812345678")
        obj = WithUuidMissing(value=test_uuid)
        result = impl.dump(WithUuidMissing, obj)
        assert result == b'{"value":"12345678-1234-5678-1234-567812345678"}'


class TestUuidLoad:
    def test_value(self, impl: Serializer) -> None:
        data = b'{"value":"12345678-1234-5678-1234-567812345678"}'
        result = impl.load(ValueOf[uuid.UUID], data)
        assert result == ValueOf[uuid.UUID](value=uuid.UUID("12345678-1234-5678-1234-567812345678"))

    def test_optional_none(self, impl: Serializer) -> None:
        data = b'{"value":null}'
        result = impl.load(OptionalValueOf[uuid.UUID], data)
        assert result == OptionalValueOf[uuid.UUID](value=None)

    def test_optional_missing(self, impl: Serializer) -> None:
        data = b"{}"
        result = impl.load(OptionalValueOf[uuid.UUID], data)
        assert result == OptionalValueOf[uuid.UUID](value=None)

    def test_optional_value(self, impl: Serializer) -> None:
        data = b'{"value":"12345678-1234-5678-1234-567812345678"}'
        result = impl.load(OptionalValueOf[uuid.UUID], data)
        assert result == OptionalValueOf[uuid.UUID](value=uuid.UUID("12345678-1234-5678-1234-567812345678"))

    def test_validation_pass(self, impl: Serializer) -> None:
        data = b'{"value":"a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d"}'
        result = impl.load(WithUuidValidation, data)
        assert result == WithUuidValidation(value=uuid.UUID("a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d"))

    def test_validation_fail(self, impl: Serializer) -> None:
        data = b'{"value":"12345678-1234-1234-1234-567812345678"}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithUuidValidation, data)
        assert exc.value.messages == {"value": ["Invalid value."]}

    def test_two_validators_pass(self, impl: Serializer) -> None:
        data = b'{"value":"a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d"}'
        result = impl.load(WithUuidTwoValidators, data)
        assert result == WithUuidTwoValidators(value=uuid.UUID("a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d"))

    def test_two_validators_first_fails(self, impl: Serializer) -> None:
        data = b'{"value":"a1234567-1234-1234-1234-567812345678"}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithUuidTwoValidators, data)
        assert exc.value.messages == {"value": ["Invalid value."]}

    def test_two_validators_second_fails(self, impl: Serializer) -> None:
        data = b'{"value":"b1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d"}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithUuidTwoValidators, data)
        assert exc.value.messages == {"value": ["Invalid value."]}

    def test_custom_required_error(self, impl: Serializer) -> None:
        data = b"{}"
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithUuidRequiredError, data)
        assert exc.value.messages == {"value": ["Custom required message"]}

    def test_custom_none_error(self, impl: Serializer) -> None:
        data = b'{"value":null}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithUuidNoneError, data)
        assert exc.value.messages == {"value": ["Custom none message"]}

    def test_custom_invalid_error(self, impl: Serializer) -> None:
        data = b'{"value":"not-a-uuid"}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithUuidInvalidError, data)
        assert exc.value.messages == {"value": ["Custom invalid message"]}

    def test_invalid_format(self, impl: Serializer) -> None:
        data = b'{"value":"not-a-uuid"}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[uuid.UUID], data)
        assert exc.value.messages == {"value": ["Not a valid UUID."]}

    def test_wrong_type_int(self, impl: Serializer) -> None:
        data = b'{"value":12345}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[uuid.UUID], data)
        assert exc.value.messages == {"value": ["Not a valid UUID."]}

    def test_wrong_type_list(self, impl: Serializer) -> None:
        data = b'{"value":["12345678-1234-5678-1234-567812345678"]}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[uuid.UUID], data)
        assert exc.value.messages == {"value": ["Not a valid UUID."]}

    def test_missing_required(self, impl: Serializer) -> None:
        data = b"{}"
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[uuid.UUID], data)
        assert exc.value.messages == {"value": ["Missing data for required field."]}

    def test_missing(self, impl: Serializer) -> None:
        data = b"{}"
        result = impl.load(WithUuidMissing, data)
        assert result == WithUuidMissing()

    def test_missing_with_value(self, impl: Serializer) -> None:
        data = b'{"value":"12345678-1234-5678-1234-567812345678"}'
        result = impl.load(WithUuidMissing, data)
        assert result == WithUuidMissing(value=uuid.UUID("12345678-1234-5678-1234-567812345678"))


class TestUuidDumpInvalidType:
    """Test that invalid types in uuid fields raise ValidationError on dump."""

    def test_string(self, impl: Serializer) -> None:
        obj = ValueOf[uuid.UUID](**{"value": "550e8400-e29b-41d4-a716-446655440000"})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(ValueOf[uuid.UUID], obj)

    def test_int(self, impl: Serializer) -> None:
        obj = ValueOf[uuid.UUID](**{"value": 123})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(ValueOf[uuid.UUID], obj)
