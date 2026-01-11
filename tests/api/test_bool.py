import marshmallow
import pytest

from .conftest import (
    Serializer,
    ValueOf,
    WithBoolDefault,
    WithBoolInvalidError,
    WithBoolMissing,
    WithBoolNoneError,
    WithBoolRequiredError,
    WithBoolTwoValidators,
    WithBoolValidation,
)


class TestBoolDump:
    @pytest.mark.parametrize(("value", "expected"), [(True, b'{"value":true}'), (False, b'{"value":false}')])
    def test_values(self, impl: Serializer, value: bool, expected: bytes) -> None:
        obj = ValueOf[bool](value=value)
        result = impl.dump(ValueOf[bool], obj)
        assert result == expected

    def test_default_provided(self, impl: Serializer) -> None:
        obj = WithBoolDefault(value=False)
        result = impl.dump(WithBoolDefault, obj)
        assert result == b'{"value":false}'

    def test_missing(self, impl: Serializer) -> None:
        obj = WithBoolMissing()
        result = impl.dump(WithBoolMissing, obj)
        assert result == b"{}"

    def test_missing_with_value(self, impl: Serializer) -> None:
        obj = WithBoolMissing(value=True)
        result = impl.dump(WithBoolMissing, obj)
        assert result == b'{"value":true}'


class TestBoolLoad:
    @pytest.mark.parametrize(("data", "expected"), [(b'{"value":true}', True), (b'{"value":false}', False)])
    def test_values(self, impl: Serializer, data: bytes, expected: bool) -> None:
        result = impl.load(ValueOf[bool], data)
        assert result == ValueOf[bool](value=expected)

    def test_validation_pass(self, impl: Serializer) -> None:
        data = b'{"value":true}'
        result = impl.load(WithBoolValidation, data)
        assert result == WithBoolValidation(value=True)

    def test_validation_fail(self, impl: Serializer) -> None:
        data = b'{"value":false}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithBoolValidation, data)
        assert exc.value.messages == {"value": ["Invalid value."]}

    def test_two_validators_pass(self, impl: Serializer) -> None:
        data = b'{"value":true}'
        result = impl.load(WithBoolTwoValidators, data)
        assert result == WithBoolTwoValidators(value=True)

    def test_two_validators_second_fails(self, impl: Serializer) -> None:
        data = b'{"value":false}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithBoolTwoValidators, data)
        assert exc.value.messages == {"value": ["Invalid value."]}

    def test_default_omitted(self, impl: Serializer) -> None:
        data = b"{}"
        result = impl.load(WithBoolDefault, data)
        assert result == WithBoolDefault(value=True)

    def test_default_provided(self, impl: Serializer) -> None:
        data = b'{"value":false}'
        result = impl.load(WithBoolDefault, data)
        assert result == WithBoolDefault(value=False)

    def test_custom_required_error(self, impl: Serializer) -> None:
        data = b"{}"
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithBoolRequiredError, data)
        assert exc.value.messages == {"value": ["Custom required message"]}

    def test_custom_none_error(self, impl: Serializer) -> None:
        data = b'{"value":null}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithBoolNoneError, data)
        assert exc.value.messages == {"value": ["Custom none message"]}

    def test_custom_invalid_error(self, impl: Serializer) -> None:
        data = b'{"value":"not-a-bool"}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithBoolInvalidError, data)
        assert exc.value.messages == {"value": ["Custom invalid message"]}

    @pytest.mark.parametrize("data", [b'{"value":"not_bool"}', b'{"value":[true,false]}'])
    def test_wrong_type(self, impl: Serializer, data: bytes) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[bool], data)
        assert exc.value.messages == {"value": ["Not a valid boolean."]}

    @pytest.mark.parametrize(
        ("data", "expected"),
        [
            pytest.param(b'{"value":0}', False, id="int_zero"),
            pytest.param(b'{"value":1}', True, id="int_one"),
            pytest.param(b'{"value":"true"}', True, id="string_true_lower"),
            pytest.param(b'{"value":"false"}', False, id="string_false_lower"),
            pytest.param(b'{"value":"True"}', True, id="string_true_title"),
            pytest.param(b'{"value":"False"}', False, id="string_false_title"),
        ],
    )
    def test_truthy_values_accepted(self, impl: Serializer, data: bytes, expected: bool) -> None:
        result = impl.load(ValueOf[bool], data)
        assert result == ValueOf[bool](value=expected)

    def test_missing(self, impl: Serializer) -> None:
        data = b"{}"
        result = impl.load(WithBoolMissing, data)
        assert result == WithBoolMissing()

    def test_missing_with_value(self, impl: Serializer) -> None:
        data = b'{"value":true}'
        result = impl.load(WithBoolMissing, data)
        assert result == WithBoolMissing(value=True)


class TestBoolEdgeCases:
    """Test bool edge cases with various truthy/falsy representations."""

    @pytest.mark.parametrize(
        ("data", "expected"),
        [
            pytest.param(b'{"value":"TRUE"}', True, id="string_true_upper"),
            pytest.param(b'{"value":"FALSE"}', False, id="string_false_upper"),
            pytest.param(b'{"value":"yes"}', True, id="string_yes"),
            pytest.param(b'{"value":"no"}', False, id="string_no"),
            pytest.param(b'{"value":"on"}', True, id="string_on"),
            pytest.param(b'{"value":"off"}', False, id="string_off"),
        ],
    )
    def test_string_truthy_values(self, impl: Serializer, data: bytes, expected: bool) -> None:
        result = impl.load(ValueOf[bool], data)
        assert result == ValueOf[bool](value=expected)

    @pytest.mark.parametrize(
        "data",
        [
            pytest.param(b'{"value":""}', id="empty_string"),
            pytest.param(b'{"value":"2"}', id="string_two"),
            pytest.param(b'{"value":"maybe"}', id="string_maybe"),
            pytest.param(b'{"value":"null"}', id="string_null"),
        ],
    )
    def test_invalid_string_values(self, impl: Serializer, data: bytes) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[bool], data)
        assert exc.value.messages == {"value": ["Not a valid boolean."]}

    def test_roundtrip_true(self, impl: Serializer) -> None:
        obj = ValueOf[bool](value=True)
        result = impl.dump(ValueOf[bool], obj)
        loaded = impl.load(ValueOf[bool], result)
        assert loaded.value is True

    def test_roundtrip_false(self, impl: Serializer) -> None:
        obj = ValueOf[bool](value=False)
        result = impl.dump(ValueOf[bool], obj)
        loaded = impl.load(ValueOf[bool], result)
        assert loaded.value is False


class TestBoolDumpInvalidType:
    """Test that invalid types in bool fields raise ValidationError on dump."""

    @pytest.mark.parametrize("value", ["not a bool", 1, []])
    def test_invalid_type(self, impl: Serializer, value: object) -> None:
        obj = ValueOf[bool](**{"value": value})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(ValueOf[bool], obj)
