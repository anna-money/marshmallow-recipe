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
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            pytest.param(b"", b'{"value":""}', id="empty"),
            pytest.param(b"\x00", b'{"value":"AA=="}', id="1_byte_2_padding"),
            pytest.param(b"\x00\x01", b'{"value":"AAE="}', id="2_bytes_1_padding"),
            pytest.param(b"\x00\x01\x02", b'{"value":"AAEC"}', id="3_bytes_no_padding"),
            pytest.param(b"\x00\x01\x02\x03", b'{"value":"AAECAw=="}', id="4_bytes_2_padding"),
            pytest.param(b"\xff" * 100, b'{"value":"' + base64.b64encode(b"\xff" * 100) + b'"}', id="100_bytes"),
        ],
    )
    def test_value(self, impl: Serializer, value: bytes, expected: bytes) -> None:
        obj = ValueOf[bytes](value=value)
        result = impl.dump(ValueOf[bytes], obj)
        assert result == expected

    @pytest.mark.parametrize(
        ("obj", "expected"),
        [
            pytest.param(OptionalValueOf[bytes](value=None), b"{}", id="none"),
            pytest.param(OptionalValueOf[bytes](value=b"\x00\x01"), b'{"value":"AAE="}', id="value"),
        ],
    )
    def test_optional(self, impl: Serializer, obj: OptionalValueOf[bytes], expected: bytes) -> None:
        result = impl.dump(OptionalValueOf[bytes], obj)
        assert result == expected

    @pytest.mark.parametrize(
        ("obj", "none_value_handling", "expected"),
        [
            pytest.param(OptionalValueOf[bytes](value=None), mr.NoneValueHandling.IGNORE, b"{}", id="ignore_none"),
            pytest.param(
                OptionalValueOf[bytes](value=None), mr.NoneValueHandling.INCLUDE, b'{"value":null}', id="include_none"
            ),
            pytest.param(
                OptionalValueOf[bytes](value=b"\x00"),
                mr.NoneValueHandling.INCLUDE,
                b'{"value":"AA=="}',
                id="include_value",
            ),
        ],
    )
    def test_none_handling(
        self, impl: Serializer, obj: OptionalValueOf[bytes], none_value_handling: mr.NoneValueHandling, expected: bytes
    ) -> None:
        result = impl.dump(OptionalValueOf[bytes], obj, none_value_handling=none_value_handling)
        assert result == expected

    @pytest.mark.parametrize(
        ("obj", "expected"),
        [
            pytest.param(WithBytesMissing(), b"{}", id="missing"),
            pytest.param(WithBytesMissing(value=b"\x00\x01"), b'{"value":"AAE="}', id="present"),
        ],
    )
    def test_missing(self, impl: Serializer, obj: WithBytesMissing, expected: bytes) -> None:
        result = impl.dump(WithBytesMissing, obj)
        assert result == expected

    @pytest.mark.parametrize(
        "obj",
        [
            pytest.param(ValueOf[bytes](**{"value": 12345}), id="int"),  # type: ignore[arg-type]
            pytest.param(ValueOf[bytes](**{"value": True}), id="bool"),  # type: ignore[arg-type]
            pytest.param(ValueOf[bytes](**{"value": "not-bytes"}), id="string"),  # type: ignore[arg-type]
            pytest.param(ValueOf[bytes](**{"value": [1, 2, 3]}), id="list"),  # type: ignore[arg-type]
            pytest.param(ValueOf[bytes](**{"value": {"a": 1}}), id="dict"),  # type: ignore[arg-type]
            pytest.param(ValueOf[bytes](**{"value": bytearray(b"\x00")}), id="bytearray"),  # type: ignore[arg-type]
        ],
    )
    def test_invalid_type(self, impl: Serializer, obj: ValueOf[bytes]) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.dump(ValueOf[bytes], obj)
        if impl.supports_proper_validation_errors_on_dump:
            assert exc.value.messages == {"value": ["Not valid base64-encoded bytes."]}

    def test_custom_invalid_error(self, impl: Serializer) -> None:
        obj = WithBytesInvalidError(**{"value": 12345})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.dump(WithBytesInvalidError, obj)
        if impl.supports_proper_validation_errors_on_dump:
            assert exc.value.messages == {"value": ["Custom invalid message"]}

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
    @pytest.mark.parametrize(
        ("data", "expected_value"),
        [
            pytest.param(b'{"value":""}', b"", id="empty"),
            pytest.param(b'{"value":"AA=="}', b"\x00", id="2_padding"),
            pytest.param(b'{"value":"AAE="}', b"\x00\x01", id="1_padding"),
            pytest.param(b'{"value":"AAEC"}', b"\x00\x01\x02", id="no_padding"),
            pytest.param(b'{"value":"AAECAw=="}', b"\x00\x01\x02\x03", id="4_bytes"),
            pytest.param(b'{"value":"' + base64.b64encode(b"\xff" * 100) + b'"}', b"\xff" * 100, id="100_bytes"),
        ],
    )
    def test_value(self, impl: Serializer, data: bytes, expected_value: bytes) -> None:
        result = impl.load(ValueOf[bytes], data)
        assert result == ValueOf[bytes](value=expected_value)

    @pytest.mark.parametrize(
        ("data", "expected"),
        [
            pytest.param(b'{"value":null}', OptionalValueOf[bytes](value=None), id="null"),
            pytest.param(b"{}", OptionalValueOf[bytes](value=None), id="missing"),
            pytest.param(b'{"value":"AAE="}', OptionalValueOf[bytes](value=b"\x00\x01"), id="value"),
        ],
    )
    def test_optional(self, impl: Serializer, data: bytes, expected: OptionalValueOf[bytes]) -> None:
        result = impl.load(OptionalValueOf[bytes], data)
        assert result == expected

    @pytest.mark.parametrize(
        ("data", "expected"),
        [
            pytest.param(b"{}", WithBytesMissing(), id="missing"),
            pytest.param(b'{"value":"AAE="}', WithBytesMissing(value=b"\x00\x01"), id="present"),
        ],
    )
    def test_missing(self, impl: Serializer, data: bytes, expected: WithBytesMissing) -> None:
        result = impl.load(WithBytesMissing, data)
        assert result == expected

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
            pytest.param(b'{"value":true}', {"value": ["Not valid base64-encoded bytes."]}, id="wrong_type_bool"),
            pytest.param(b'{"value":[1,2,3]}', {"value": ["Not valid base64-encoded bytes."]}, id="wrong_type_list"),
            pytest.param(b'{"value":{"a":1}}', {"value": ["Not valid base64-encoded bytes."]}, id="wrong_type_dict"),
            pytest.param(b"{}", {"value": ["Missing data for required field."]}, id="missing_required"),
        ],
    )
    def test_invalid(self, impl: Serializer, data: bytes, error_messages: dict[str, list[str]]) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[bytes], data)
        assert exc.value.messages == error_messages
