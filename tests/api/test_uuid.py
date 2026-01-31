import uuid

import marshmallow
import marshmallow_recipe as mr
import pytest

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
        obj = ValueOf[uuid.UUID](value=uuid.UUID("12345678-1234-5678-1234-567812345678"))
        result = impl.dump(ValueOf[uuid.UUID], obj)
        assert result == b'{"value":"12345678-1234-5678-1234-567812345678"}'

    @pytest.mark.parametrize(
        ("obj", "expected"),
        [
            (OptionalValueOf[uuid.UUID](value=None), b"{}"),
            (
                OptionalValueOf[uuid.UUID](value=uuid.UUID("12345678-1234-5678-1234-567812345678")),
                b'{"value":"12345678-1234-5678-1234-567812345678"}',
            ),
        ],
    )
    def test_optional(self, impl: Serializer, obj: OptionalValueOf[uuid.UUID], expected: bytes) -> None:
        result = impl.dump(OptionalValueOf[uuid.UUID], obj)
        assert result == expected

    @pytest.mark.parametrize(
        ("obj", "none_value_handling", "expected"),
        [
            (OptionalValueOf[uuid.UUID](value=None), mr.NoneValueHandling.IGNORE, b"{}"),
            (OptionalValueOf[uuid.UUID](value=None), mr.NoneValueHandling.INCLUDE, b'{"value":null}'),
            (
                OptionalValueOf[uuid.UUID](value=uuid.UUID("12345678-1234-5678-1234-567812345678")),
                mr.NoneValueHandling.INCLUDE,
                b'{"value":"12345678-1234-5678-1234-567812345678"}',
            ),
        ],
    )
    def test_none_handling(
        self,
        impl: Serializer,
        obj: OptionalValueOf[uuid.UUID],
        none_value_handling: mr.NoneValueHandling,
        expected: bytes,
    ) -> None:
        result = impl.dump(OptionalValueOf[uuid.UUID], obj, none_value_handling=none_value_handling)
        assert result == expected

    @pytest.mark.parametrize(
        ("obj", "expected"),
        [
            (WithUuidMissing(), b"{}"),
            (
                WithUuidMissing(value=uuid.UUID("12345678-1234-5678-1234-567812345678")),
                b'{"value":"12345678-1234-5678-1234-567812345678"}',
            ),
        ],
    )
    def test_missing(self, impl: Serializer, obj: WithUuidMissing, expected: bytes) -> None:
        result = impl.dump(WithUuidMissing, obj)
        assert result == expected

    @pytest.mark.parametrize(
        "obj",
        [
            pytest.param(
                ValueOf[uuid.UUID](**{"value": "550e8400-e29b-41d4-a716-446655440000"}),  # type: ignore[arg-type]
                id="string",
            ),
            pytest.param(
                ValueOf[uuid.UUID](**{"value": 123}),  # type: ignore[arg-type]
                id="int",
            ),
        ],
    )
    def test_invalid_type(self, impl: Serializer, obj: ValueOf[uuid.UUID]) -> None:
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(ValueOf[uuid.UUID], obj)


class TestUuidLoad:
    def test_value(self, impl: Serializer) -> None:
        data = b'{"value":"12345678-1234-5678-1234-567812345678"}'
        result = impl.load(ValueOf[uuid.UUID], data)
        assert result == ValueOf[uuid.UUID](value=uuid.UUID("12345678-1234-5678-1234-567812345678"))

    @pytest.mark.parametrize(
        ("data", "expected"),
        [
            (b'{"value":null}', OptionalValueOf[uuid.UUID](value=None)),
            (b"{}", OptionalValueOf[uuid.UUID](value=None)),
            (
                b'{"value":"12345678-1234-5678-1234-567812345678"}',
                OptionalValueOf[uuid.UUID](value=uuid.UUID("12345678-1234-5678-1234-567812345678")),
            ),
        ],
    )
    def test_optional(self, impl: Serializer, data: bytes, expected: OptionalValueOf[uuid.UUID]) -> None:
        result = impl.load(OptionalValueOf[uuid.UUID], data)
        assert result == expected

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

    @pytest.mark.parametrize(
        ("data", "error_messages"),
        [
            pytest.param(
                b'{"value":"a1234567-1234-1234-1234-567812345678"}', {"value": ["Invalid value."]}, id="first_fails"
            ),
            pytest.param(
                b'{"value":"b1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d"}', {"value": ["Invalid value."]}, id="second_fails"
            ),
        ],
    )
    def test_two_validators_fail(self, impl: Serializer, data: bytes, error_messages: dict[str, list[str]]) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithUuidTwoValidators, data)
        assert exc.value.messages == error_messages

    @pytest.mark.parametrize(
        ("data", "schema_type", "error_messages"),
        [
            pytest.param(b"{}", WithUuidRequiredError, {"value": ["Custom required message"]}, id="required"),
            pytest.param(b'{"value":null}', WithUuidNoneError, {"value": ["Custom none message"]}, id="none"),
            pytest.param(
                b'{"value":"not-a-uuid"}', WithUuidInvalidError, {"value": ["Custom invalid message"]}, id="invalid"
            ),
        ],
    )
    def test_custom_error(
        self, impl: Serializer, data: bytes, schema_type: type, error_messages: dict[str, list[str]]
    ) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(schema_type, data)
        assert exc.value.messages == error_messages

    @pytest.mark.parametrize(
        ("data", "error_messages"),
        [
            pytest.param(b'{"value":"not-a-uuid"}', {"value": ["Not a valid UUID."]}, id="invalid_format"),
            pytest.param(b'{"value":12345}', {"value": ["Not a valid UUID."]}, id="wrong_type_int"),
            pytest.param(
                b'{"value":["12345678-1234-5678-1234-567812345678"]}',
                {"value": ["Not a valid UUID."]},
                id="wrong_type_list",
            ),
            pytest.param(b"{}", {"value": ["Missing data for required field."]}, id="missing_required"),
        ],
    )
    def test_invalid(self, impl: Serializer, data: bytes, error_messages: dict[str, list[str]]) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[uuid.UUID], data)
        assert exc.value.messages == error_messages

    @pytest.mark.parametrize(
        ("data", "expected"),
        [
            (b"{}", WithUuidMissing()),
            (
                b'{"value":"12345678-1234-5678-1234-567812345678"}',
                WithUuidMissing(value=uuid.UUID("12345678-1234-5678-1234-567812345678")),
            ),
        ],
    )
    def test_missing(self, impl: Serializer, data: bytes, expected: WithUuidMissing) -> None:
        result = impl.load(WithUuidMissing, data)
        assert result == expected
