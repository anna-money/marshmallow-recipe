import uuid

import marshmallow
import pytest

from .conftest import (
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
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            pytest.param(
                uuid.UUID("12345678-1234-5678-1234-567812345678"),
                b'{"value":"12345678-1234-5678-1234-567812345678"}',
                id="standard",
            ),
            pytest.param(
                uuid.UUID("00000000-0000-0000-0000-000000000000"),
                b'{"value":"00000000-0000-0000-0000-000000000000"}',
                id="nil_uuid",
            ),
            pytest.param(
                uuid.UUID("ffffffff-ffff-ffff-ffff-ffffffffffff"),
                b'{"value":"ffffffff-ffff-ffff-ffff-ffffffffffff"}',
                id="max_uuid",
            ),
            pytest.param(
                uuid.UUID("a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d"),
                b'{"value":"a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d"}',
                id="uuid_v4",
            ),
        ],
    )
    def test_value(self, impl: Serializer, value: uuid.UUID, expected: bytes) -> None:
        obj = ValueOf[uuid.UUID](value=value)
        result = impl.dump(ValueOf[uuid.UUID], obj)
        assert result == expected

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
    @pytest.mark.parametrize(
        ("data", "expected"),
        [
            pytest.param(
                b'{"value":"12345678-1234-5678-1234-567812345678"}',
                uuid.UUID("12345678-1234-5678-1234-567812345678"),
                id="standard",
            ),
            pytest.param(
                b'{"value":"00000000-0000-0000-0000-000000000000"}',
                uuid.UUID("00000000-0000-0000-0000-000000000000"),
                id="nil_uuid",
            ),
            pytest.param(
                b'{"value":"ffffffff-ffff-ffff-ffff-ffffffffffff"}',
                uuid.UUID("ffffffff-ffff-ffff-ffff-ffffffffffff"),
                id="max_uuid",
            ),
            pytest.param(
                b'{"value":"FFFFFFFF-FFFF-FFFF-FFFF-FFFFFFFFFFFF"}',
                uuid.UUID("ffffffff-ffff-ffff-ffff-ffffffffffff"),
                id="uppercase",
            ),
            pytest.param(
                b'{"value":"12345678123456781234567812345678"}',
                uuid.UUID("12345678-1234-5678-1234-567812345678"),
                id="no_dashes",
            ),
            # UUID v1 (time-based)
            pytest.param(
                b'{"value":"6ba7b810-9dad-11d1-80b4-00c04fd430c8"}',
                uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8"),
                id="uuid_v1",
            ),
            # UUID v3 (namespace MD5)
            pytest.param(
                b'{"value":"6fa459ea-ee8a-3ca4-894e-db77e160355e"}',
                uuid.UUID("6fa459ea-ee8a-3ca4-894e-db77e160355e"),
                id="uuid_v3",
            ),
            # UUID v5 (namespace SHA1)
            pytest.param(
                b'{"value":"886313e1-3b8a-5372-9b90-0c9aee199e5d"}',
                uuid.UUID("886313e1-3b8a-5372-9b90-0c9aee199e5d"),
                id="uuid_v5",
            ),
            # Braced format
            pytest.param(
                b'{"value":"{12345678-1234-5678-1234-567812345678}"}',
                uuid.UUID("12345678-1234-5678-1234-567812345678"),
                id="braced",
            ),
            # URN format
            pytest.param(
                b'{"value":"urn:uuid:12345678-1234-5678-1234-567812345678"}',
                uuid.UUID("12345678-1234-5678-1234-567812345678"),
                id="urn",
            ),
        ],
    )
    def test_value(self, impl: Serializer, data: bytes, expected: uuid.UUID) -> None:
        result = impl.load(ValueOf[uuid.UUID], data)
        assert result == ValueOf[uuid.UUID](value=expected)

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
        "data",
        [b'{"value":"a1234567-1234-1234-1234-567812345678"}', b'{"value":"b1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d"}'],
    )
    def test_two_validators_fail(self, impl: Serializer, data: bytes) -> None:
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

    @pytest.mark.parametrize("data", [b'{"value":12345}', b'{"value":["12345678-1234-5678-1234-567812345678"]}'])
    def test_wrong_type(self, impl: Serializer, data: bytes) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[uuid.UUID], data)
        assert exc.value.messages == {"value": ["Not a valid UUID."]}

    def test_missing(self, impl: Serializer) -> None:
        data = b"{}"
        result = impl.load(WithUuidMissing, data)
        assert result == WithUuidMissing()

    def test_missing_with_value(self, impl: Serializer) -> None:
        data = b'{"value":"12345678-1234-5678-1234-567812345678"}'
        result = impl.load(WithUuidMissing, data)
        assert result == WithUuidMissing(value=uuid.UUID("12345678-1234-5678-1234-567812345678"))


class TestUuidEdgeCases:
    """Test UUID edge cases with various formats and boundary values."""

    @pytest.mark.parametrize(
        ("data", "id_"),
        [
            pytest.param(b'{"value":"not-a-uuid-format"}', "invalid_format"),
            pytest.param(b'{"value":"12345678-1234-5678-1234-56781234567"}', "too_short"),
            pytest.param(b'{"value":"12345678-1234-5678-1234-5678123456789"}', "too_long"),
            pytest.param(b'{"value":"12345678-1234-5678-1234-56781234567g"}', "invalid_hex_char"),
            pytest.param(b'{"value":"1234567-1234-5678-1234-567812345678"}', "wrong_group_length"),
            pytest.param(b'{"value":""}', "empty_string"),
        ],
    )
    def test_invalid_uuid_formats(self, impl: Serializer, data: bytes, id_: str) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[uuid.UUID], data)
        assert exc.value.messages == {"value": ["Not a valid UUID."]}

    def test_uuid_v4_random(self, impl: Serializer) -> None:
        random_uuid = uuid.uuid4()
        obj = ValueOf[uuid.UUID](value=random_uuid)
        result = impl.dump(ValueOf[uuid.UUID], obj)
        loaded = impl.load(ValueOf[uuid.UUID], result)
        assert loaded.value == random_uuid

    def test_uuid_from_bytes(self, impl: Serializer) -> None:
        uuid_from_bytes = uuid.UUID(bytes=b"\x12\x34\x56\x78" * 4)
        obj = ValueOf[uuid.UUID](value=uuid_from_bytes)
        result = impl.dump(ValueOf[uuid.UUID], obj)
        loaded = impl.load(ValueOf[uuid.UUID], result)
        assert loaded.value == uuid_from_bytes

    def test_uuid_from_int(self, impl: Serializer) -> None:
        uuid_from_int = uuid.UUID(int=0x12345678123456781234567812345678)
        obj = ValueOf[uuid.UUID](value=uuid_from_int)
        result = impl.dump(ValueOf[uuid.UUID], obj)
        loaded = impl.load(ValueOf[uuid.UUID], result)
        assert loaded.value == uuid_from_int

    def test_mixed_case_uuid(self, impl: Serializer) -> None:
        data = b'{"value":"AbCdEf12-3456-7890-AbCd-Ef1234567890"}'
        result = impl.load(ValueOf[uuid.UUID], data)
        assert result.value == uuid.UUID("abcdef12-3456-7890-abcd-ef1234567890")


class TestUuidDumpInvalidType:
    """Test that invalid types in uuid fields raise ValidationError on dump."""

    @pytest.mark.parametrize("value", ["550e8400-e29b-41d4-a716-446655440000", 123])
    def test_invalid_type(self, impl: Serializer, value: object) -> None:
        obj = ValueOf[uuid.UUID](**{"value": value})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(ValueOf[uuid.UUID], obj)
