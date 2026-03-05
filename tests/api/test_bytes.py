import base64

import marshmallow
import pytest

import marshmallow_recipe as mr

from .conftest import (
    OptionalValueOf,
    Serializer,
    ValueOf,
    WithBytesInvalidError,
    WithBytesMissing,
    WithBytesNoneError,
    WithBytesRequiredError,
    WithBytesTwoValidators,
    WithBytesValidation,
)


class TestBytesDump:
    def test_value(self, impl: Serializer) -> None:
        obj = ValueOf[bytes](value=b"\x00\x01\x02\x03")
        result = impl.dump(ValueOf[bytes], obj)
        assert result == b'{"value":"AAECAw=="}'

    @pytest.mark.parametrize(
        ("obj", "expected"),
        [(OptionalValueOf[bytes](value=None), b"{}"), (OptionalValueOf[bytes](value=b"\x00\x01"), b'{"value":"AAE="}')],
    )
    def test_optional(self, impl: Serializer, obj: OptionalValueOf[bytes], expected: bytes) -> None:
        result = impl.dump(OptionalValueOf[bytes], obj)
        assert result == expected

    @pytest.mark.parametrize(
        ("obj", "none_value_handling", "expected"),
        [
            (OptionalValueOf[bytes](value=None), mr.NoneValueHandling.IGNORE, b"{}"),
            (OptionalValueOf[bytes](value=None), mr.NoneValueHandling.INCLUDE, b'{"value":null}'),
            (OptionalValueOf[bytes](value=b"\x00"), mr.NoneValueHandling.INCLUDE, b'{"value":"AA=="}'),
        ],
    )
    def test_none_handling(
        self, impl: Serializer, obj: OptionalValueOf[bytes], none_value_handling: mr.NoneValueHandling, expected: bytes
    ) -> None:
        result = impl.dump(OptionalValueOf[bytes], obj, none_value_handling=none_value_handling)
        assert result == expected

    @pytest.mark.parametrize(
        ("obj", "expected"), [(WithBytesMissing(), b"{}"), (WithBytesMissing(value=b"\x00\x01"), b'{"value":"AAE="}')]
    )
    def test_missing(self, impl: Serializer, obj: WithBytesMissing, expected: bytes) -> None:
        result = impl.dump(WithBytesMissing, obj)
        assert result == expected

    def test_empty_bytes(self, impl: Serializer) -> None:
        obj = ValueOf[bytes](value=b"")
        result = impl.dump(ValueOf[bytes], obj)
        assert result == b'{"value":""}'

    @pytest.mark.parametrize(
        "obj",
        [
            pytest.param(ValueOf[bytes](**{"value": 12345}), id="int"),  # type: ignore[arg-type]
            pytest.param(ValueOf[bytes](**{"value": "not-bytes"}), id="string"),  # type: ignore[arg-type]
        ],
    )
    def test_invalid_type(self, impl: Serializer, obj: ValueOf[bytes]) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.dump(ValueOf[bytes], obj)
        if impl.supports_proper_validation_errors_on_dump:
            assert exc.value.messages == {"value": ["Not valid base64-encoded bytes."]}

    def test_validation_pass(self, impl: Serializer) -> None:
        obj = WithBytesValidation(value=b"\x00\x01")
        result = impl.dump(WithBytesValidation, obj)
        assert result == b'{"value":"AAE="}'

    def test_validation_fail(self, impl: Serializer) -> None:
        obj = WithBytesValidation(value=b"\x00" * 20)
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.dump(WithBytesValidation, obj)
        assert exc.value.messages == {"value": ["Invalid value."]}

    def test_two_validators_both_fail(self, impl: Serializer) -> None:
        obj = WithBytesTwoValidators(value=b"\x01" * 20)
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.dump(WithBytesTwoValidators, obj)
        assert exc.value.messages == {"value": ["Invalid value.", "Invalid value."]}


class TestBytesLoad:
    def test_value(self, impl: Serializer) -> None:
        data = b'{"value":"AAECAw=="}'
        result = impl.load(ValueOf[bytes], data)
        assert result == ValueOf[bytes](value=b"\x00\x01\x02\x03")

    @pytest.mark.parametrize(
        ("data", "expected"),
        [
            (b'{"value":null}', OptionalValueOf[bytes](value=None)),
            (b"{}", OptionalValueOf[bytes](value=None)),
            (b'{"value":"AAE="}', OptionalValueOf[bytes](value=b"\x00\x01")),
        ],
    )
    def test_optional(self, impl: Serializer, data: bytes, expected: OptionalValueOf[bytes]) -> None:
        result = impl.load(OptionalValueOf[bytes], data)
        assert result == expected

    def test_empty_string(self, impl: Serializer) -> None:
        data = b'{"value":""}'
        result = impl.load(ValueOf[bytes], data)
        assert result == ValueOf[bytes](value=b"")

    def test_validation_pass(self, impl: Serializer) -> None:
        encoded = base64.b64encode(b"\x00\x01").decode("ascii")
        data = f'{{"value":"{encoded}"}}'.encode()
        result = impl.load(WithBytesValidation, data)
        assert result == WithBytesValidation(value=b"\x00\x01")

    def test_validation_fail(self, impl: Serializer) -> None:
        encoded = base64.b64encode(b"\x00" * 20).decode("ascii")
        data = f'{{"value":"{encoded}"}}'.encode()
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithBytesValidation, data)
        assert exc.value.messages == {"value": ["Invalid value."]}

    def test_two_validators_both_fail(self, impl: Serializer) -> None:
        encoded = base64.b64encode(b"\x01" * 20).decode("ascii")
        data = f'{{"value":"{encoded}"}}'.encode()
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithBytesTwoValidators, data)
        assert exc.value.messages == {"value": ["Invalid value.", "Invalid value."]}

    @pytest.mark.parametrize(
        ("data", "schema_type", "error_messages"),
        [
            pytest.param(b"{}", WithBytesRequiredError, {"value": ["Custom required message"]}, id="required"),
            pytest.param(b'{"value":null}', WithBytesNoneError, {"value": ["Custom none message"]}, id="none"),
            pytest.param(
                b'{"value":12345}', WithBytesInvalidError, {"value": ["Custom invalid message"]}, id="invalid"
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
            pytest.param(
                b'{"value":"!!!invalid-base64!!!"}', {"value": ["Not valid base64-encoded bytes."]}, id="invalid_base64"
            ),
            pytest.param(b'{"value":12345}', {"value": ["Not valid base64-encoded bytes."]}, id="wrong_type_int"),
            pytest.param(b'{"value":[1,2,3]}', {"value": ["Not valid base64-encoded bytes."]}, id="wrong_type_list"),
            pytest.param(b"{}", {"value": ["Missing data for required field."]}, id="missing_required"),
        ],
    )
    def test_invalid(self, impl: Serializer, data: bytes, error_messages: dict[str, list[str]]) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[bytes], data)
        assert exc.value.messages == error_messages

    @pytest.mark.parametrize(
        ("data", "expected"), [(b"{}", WithBytesMissing()), (b'{"value":"AAE="}', WithBytesMissing(value=b"\x00\x01"))]
    )
    def test_missing(self, impl: Serializer, data: bytes, expected: WithBytesMissing) -> None:
        result = impl.load(WithBytesMissing, data)
        assert result == expected
