import marshmallow
import pytest

import marshmallow_recipe as mr

from .conftest import (
    OptionalValueOf,
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
    def test_true(self, impl: Serializer) -> None:
        obj = ValueOf[bool](value=True)
        result = impl.dump(ValueOf[bool], obj)
        assert result == b'{"value":true}'

    def test_false(self, impl: Serializer) -> None:
        obj = ValueOf[bool](value=False)
        result = impl.dump(ValueOf[bool], obj)
        assert result == b'{"value":false}'

    def test_optional_none(self, impl: Serializer) -> None:
        obj = OptionalValueOf[bool](value=None)
        result = impl.dump(OptionalValueOf[bool], obj)
        assert result == b"{}"

    def test_optional_value(self, impl: Serializer) -> None:
        obj = OptionalValueOf[bool](value=True)
        result = impl.dump(OptionalValueOf[bool], obj)
        assert result == b'{"value":true}'

    def test_default_provided(self, impl: Serializer) -> None:
        obj = WithBoolDefault(value=False)
        result = impl.dump(WithBoolDefault, obj)
        assert result == b'{"value":false}'

    def test_none_handling_ignore_default(self, impl: Serializer) -> None:
        obj = OptionalValueOf[bool](value=None)
        result = impl.dump(OptionalValueOf[bool], obj)
        assert result == b"{}"

    def test_none_handling_ignore_explicit(self, impl: Serializer) -> None:
        obj = OptionalValueOf[bool](value=None)
        result = impl.dump(OptionalValueOf[bool], obj, none_value_handling=mr.NoneValueHandling.IGNORE)
        assert result == b"{}"

    def test_none_handling_include(self, impl: Serializer) -> None:
        obj = OptionalValueOf[bool](value=None)
        result = impl.dump(OptionalValueOf[bool], obj, none_value_handling=mr.NoneValueHandling.INCLUDE)
        assert result == b'{"value":null}'

    def test_none_handling_include_with_value(self, impl: Serializer) -> None:
        obj = OptionalValueOf[bool](value=True)
        result = impl.dump(OptionalValueOf[bool], obj, none_value_handling=mr.NoneValueHandling.INCLUDE)
        assert result == b'{"value":true}'

    def test_missing(self, impl: Serializer) -> None:
        obj = WithBoolMissing()
        result = impl.dump(WithBoolMissing, obj)
        assert result == b"{}"

    def test_missing_with_value(self, impl: Serializer) -> None:
        obj = WithBoolMissing(value=True)
        result = impl.dump(WithBoolMissing, obj)
        assert result == b'{"value":true}'


class TestBoolLoad:
    def test_true(self, impl: Serializer) -> None:
        data = b'{"value":true}'
        result = impl.load(ValueOf[bool], data)
        assert result == ValueOf[bool](value=True)

    def test_false(self, impl: Serializer) -> None:
        data = b'{"value":false}'
        result = impl.load(ValueOf[bool], data)
        assert result == ValueOf[bool](value=False)

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

    def test_optional_none(self, impl: Serializer) -> None:
        data = b'{"value":null}'
        result = impl.load(OptionalValueOf[bool], data)
        assert result == OptionalValueOf[bool](value=None)

    def test_optional_missing(self, impl: Serializer) -> None:
        data = b"{}"
        result = impl.load(OptionalValueOf[bool], data)
        assert result == OptionalValueOf[bool](value=None)

    def test_optional_value(self, impl: Serializer) -> None:
        data = b'{"value":true}'
        result = impl.load(OptionalValueOf[bool], data)
        assert result == OptionalValueOf[bool](value=True)

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

    def test_wrong_type_string(self, impl: Serializer) -> None:
        data = b'{"value":"not_bool"}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[bool], data)
        assert exc.value.messages == {"value": ["Not a valid boolean."]}

    def test_wrong_type_list(self, impl: Serializer) -> None:
        data = b'{"value":[true,false]}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[bool], data)
        assert exc.value.messages == {"value": ["Not a valid boolean."]}

    def test_missing_required(self, impl: Serializer) -> None:
        data = b"{}"
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[bool], data)
        assert exc.value.messages == {"value": ["Missing data for required field."]}

    def test_missing(self, impl: Serializer) -> None:
        data = b"{}"
        result = impl.load(WithBoolMissing, data)
        assert result == WithBoolMissing()

    def test_missing_with_value(self, impl: Serializer) -> None:
        data = b'{"value":true}'
        result = impl.load(WithBoolMissing, data)
        assert result == WithBoolMissing(value=True)


class TestBoolDumpInvalidType:
    """Test that invalid types in bool fields raise ValidationError on dump."""

    def test_string(self, impl: Serializer) -> None:
        obj = ValueOf[bool](**{"value": "not a bool"})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(ValueOf[bool], obj)

    def test_int(self, impl: Serializer) -> None:
        obj = ValueOf[bool](**{"value": 1})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(ValueOf[bool], obj)

    def test_list(self, impl: Serializer) -> None:
        obj = ValueOf[bool](**{"value": []})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(ValueOf[bool], obj)
