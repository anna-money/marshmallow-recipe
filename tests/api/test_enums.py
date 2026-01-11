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
    @pytest.mark.parametrize(
        ("enum_type", "value", "expected"),
        [
            pytest.param(Status, Status.ACTIVE, b'{"value":"active"}', id="str_enum"),
            pytest.param(Priority, Priority.LOW, b'{"value":1}', id="int_enum"),
        ],
    )
    def test_value(self, impl: Serializer, enum_type: type, value: object, expected: bytes) -> None:
        obj = ValueOf[enum_type](value=value)
        result = impl.dump(ValueOf[enum_type], obj)
        assert result == expected

    @pytest.mark.parametrize(
        ("enum_type", "value", "expected"),
        [
            pytest.param(Status, None, b"{}", id="str_enum_none"),
            pytest.param(Status, Status.PENDING, b'{"value":"pending"}', id="str_enum_value"),
            pytest.param(Priority, None, b"{}", id="int_enum_none"),
            pytest.param(Priority, Priority.HIGH, b'{"value":3}', id="int_enum_value"),
        ],
    )
    def test_optional(self, impl: Serializer, enum_type: type, value: object, expected: bytes) -> None:
        obj = OptionalValueOf[enum_type](value=value)
        result = impl.dump(OptionalValueOf[enum_type], obj)
        assert result == expected

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
    @pytest.mark.parametrize(
        ("enum_type", "data", "expected_value"),
        [
            pytest.param(Status, b'{"value":"inactive"}', Status.INACTIVE, id="str_enum"),
            pytest.param(Priority, b'{"value":3}', Priority.HIGH, id="int_enum"),
        ],
    )
    def test_value(self, impl: Serializer, enum_type: type, data: bytes, expected_value: object) -> None:
        result = impl.load(ValueOf[enum_type], data)
        assert result == ValueOf[enum_type](value=expected_value)

    @pytest.mark.parametrize(
        ("data", "expected"),
        [
            pytest.param(b'{"value":"active"}', Status.ACTIVE, id="active"),
            pytest.param(b'{"value":"inactive"}', Status.INACTIVE, id="inactive"),
            pytest.param(b'{"value":"pending"}', Status.PENDING, id="pending"),
        ],
    )
    def test_all_str_enum_values(self, impl: Serializer, data: bytes, expected: Status) -> None:
        result = impl.load(ValueOf[Status], data)
        assert result == ValueOf[Status](value=expected)

    @pytest.mark.parametrize(
        ("data", "expected"),
        [
            pytest.param(b'{"value":1}', Priority.LOW, id="low"),
            pytest.param(b'{"value":2}', Priority.MEDIUM, id="medium"),
            pytest.param(b'{"value":3}', Priority.HIGH, id="high"),
        ],
    )
    def test_all_int_enum_values(self, impl: Serializer, data: bytes, expected: Priority) -> None:
        result = impl.load(ValueOf[Priority], data)
        assert result == ValueOf[Priority](value=expected)

    @pytest.mark.parametrize(
        ("enum_type", "data", "expected_message"),
        [
            pytest.param(
                Status,
                b'{"value":"invalid_status"}',
                {"value": ["Not a valid choice: 'invalid_status'. Allowed values: ['active', 'inactive', 'pending']"]},
                id="str_invalid_value",
            ),
            pytest.param(
                Priority,
                b'{"value":999}',
                {"value": ["Not a valid choice: '999'. Allowed values: [1, 2, 3]"]},
                id="int_invalid_value",
            ),
            pytest.param(
                Status,
                b'{"value":123}',
                {"value": ["Not a valid choice: '123'. Allowed values: ['active', 'inactive', 'pending']"]},
                id="str_wrong_type",
            ),
            pytest.param(
                Priority,
                b'{"value":"not_a_number"}',
                {"value": ["Not a valid choice: 'not_a_number'. Allowed values: [1, 2, 3]"]},
                id="int_wrong_type",
            ),
        ],
    )
    def test_invalid_value(self, impl: Serializer, enum_type: type, data: bytes, expected_message: dict) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[enum_type], data)
        assert exc.value.messages == expected_message

    @pytest.mark.parametrize("enum_type", [Status, Priority])
    def test_missing_required(self, impl: Serializer, enum_type: type) -> None:
        data = b"{}"
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[enum_type], data)
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

    @pytest.mark.parametrize("data", [b'{"priority":1}', b'{"priority":3}'])
    def test_int_enum_two_validators_fail(self, impl: Serializer, data: bytes) -> None:
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
        obj = ValueOf[Status](value="active")  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.dump(ValueOf[Status], obj)
        assert exc.value.messages == [
            "Expected Status instance, got str. Allowed values: [Status.ACTIVE, Status.INACTIVE, Status.PENDING]"
        ]

    def test_str_enum_with_int(self, impl: Serializer) -> None:
        obj = ValueOf[Status](value=1)  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.dump(ValueOf[Status], obj)
        assert exc.value.messages == [
            "Expected Status instance, got int. Allowed values: [Status.ACTIVE, Status.INACTIVE, Status.PENDING]"
        ]

    def test_int_enum_with_int(self, impl: Serializer) -> None:
        obj = ValueOf[Priority](value=1)  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.dump(ValueOf[Priority], obj)
        assert exc.value.messages == [
            "Expected Priority instance, got int. Allowed values: [Priority.LOW, Priority.MEDIUM, Priority.HIGH]"
        ]

    def test_int_enum_with_string(self, impl: Serializer) -> None:
        obj = ValueOf[Priority](value="high")  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.dump(ValueOf[Priority], obj)
        assert exc.value.messages == [
            "Expected Priority instance, got str. Allowed values: [Priority.LOW, Priority.MEDIUM, Priority.HIGH]"
        ]


class TestEnumEdgeCases:
    """Test enum edge cases with boundary values and special scenarios."""

    def test_all_str_enum_values_roundtrip(self, impl: Serializer) -> None:
        for status in Status:
            obj = ValueOf[Status](value=status)
            result = impl.dump(ValueOf[Status], obj)
            loaded = impl.load(ValueOf[Status], result)
            assert loaded == obj

    def test_all_int_enum_values_roundtrip(self, impl: Serializer) -> None:
        for priority in Priority:
            obj = ValueOf[Priority](value=priority)
            result = impl.dump(ValueOf[Priority], obj)
            loaded = impl.load(ValueOf[Priority], result)
            assert loaded == obj

    def test_str_enum_case_sensitive(self, impl: Serializer) -> None:
        # "Active" should fail (case sensitive)
        data = b'{"value":"Active"}'
        with pytest.raises(marshmallow.ValidationError):
            impl.load(ValueOf[Status], data)

    def test_str_enum_uppercase_fails(self, impl: Serializer) -> None:
        data = b'{"value":"ACTIVE"}'
        with pytest.raises(marshmallow.ValidationError):
            impl.load(ValueOf[Status], data)

    def test_str_enum_with_leading_space_fails(self, impl: Serializer) -> None:
        data = b'{"value":" active"}'
        with pytest.raises(marshmallow.ValidationError):
            impl.load(ValueOf[Status], data)

    def test_str_enum_with_trailing_space_fails(self, impl: Serializer) -> None:
        data = b'{"value":"active "}'
        with pytest.raises(marshmallow.ValidationError):
            impl.load(ValueOf[Status], data)

    def test_int_enum_with_float_is_coerced(self, impl: Serializer) -> None:
        # 1.0 gets coerced to 1 by JSON parsing
        data = b'{"value":1.0}'
        result = impl.load(ValueOf[Priority], data)
        assert result.value == Priority.LOW

    def test_int_enum_with_string_number_fails(self, impl: Serializer) -> None:
        data = b'{"value":"1"}'
        with pytest.raises(marshmallow.ValidationError):
            impl.load(ValueOf[Priority], data)

    def test_int_enum_zero_not_valid(self, impl: Serializer) -> None:
        data = b'{"value":0}'
        with pytest.raises(marshmallow.ValidationError):
            impl.load(ValueOf[Priority], data)

    def test_int_enum_negative_not_valid(self, impl: Serializer) -> None:
        data = b'{"value":-1}'
        with pytest.raises(marshmallow.ValidationError):
            impl.load(ValueOf[Priority], data)

    def test_int_enum_big_int_not_valid(self, impl: Serializer) -> None:
        data = b'{"value":9223372036854775807}'
        with pytest.raises(marshmallow.ValidationError):
            impl.load(ValueOf[Priority], data)

    def test_str_enum_empty_string_not_valid(self, impl: Serializer) -> None:
        data = b'{"value":""}'
        with pytest.raises(marshmallow.ValidationError):
            impl.load(ValueOf[Status], data)

    def test_str_enum_null_not_valid(self, impl: Serializer) -> None:
        data = b'{"value":null}'
        with pytest.raises(marshmallow.ValidationError):
            impl.load(ValueOf[Status], data)

    def test_int_enum_null_not_valid(self, impl: Serializer) -> None:
        data = b'{"value":null}'
        with pytest.raises(marshmallow.ValidationError):
            impl.load(ValueOf[Priority], data)

    def test_optional_str_enum_none(self, impl: Serializer) -> None:
        obj = OptionalValueOf[Status](value=None)
        result = impl.dump(OptionalValueOf[Status], obj)
        assert result == b"{}"

    def test_optional_int_enum_none(self, impl: Serializer) -> None:
        obj = OptionalValueOf[Priority](value=None)
        result = impl.dump(OptionalValueOf[Priority], obj)
        assert result == b"{}"

    def test_optional_str_enum_with_value(self, impl: Serializer) -> None:
        for status in Status:
            obj = OptionalValueOf[Status](value=status)
            result = impl.dump(OptionalValueOf[Status], obj)
            loaded = impl.load(OptionalValueOf[Status], result)
            assert loaded == obj

    def test_optional_int_enum_with_value(self, impl: Serializer) -> None:
        for priority in Priority:
            obj = OptionalValueOf[Priority](value=priority)
            result = impl.dump(OptionalValueOf[Priority], obj)
            loaded = impl.load(OptionalValueOf[Priority], result)
            assert loaded == obj
