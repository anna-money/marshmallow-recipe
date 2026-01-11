import marshmallow
import marshmallow_recipe as mr
import pytest

from .conftest import (
    OptionalValueOf,
    Serializer,
    ValueOf,
    WithFloatDefault,
    WithFloatInvalidError,
    WithFloatMissing,
    WithFloatNoneError,
    WithFloatRequiredError,
    WithFloatTwoValidators,
    WithFloatValidation,
)


class TestFloatDump:
    def test_positive(self, impl: Serializer) -> None:
        obj = ValueOf[float](value=3.14)
        result = impl.dump(ValueOf[float], obj)
        assert result == b'{"value":3.14}'

    def test_negative(self, impl: Serializer) -> None:
        obj = ValueOf[float](value=-2.5)
        result = impl.dump(ValueOf[float], obj)
        assert result == b'{"value":-2.5}'

    def test_zero(self, impl: Serializer) -> None:
        obj = ValueOf[float](value=0.0)
        result = impl.dump(ValueOf[float], obj)
        assert result == b'{"value":0.0}'

    def test_precision(self, impl: Serializer) -> None:
        obj = ValueOf[float](value=3.141592653589793)
        result = impl.dump(ValueOf[float], obj)
        assert result == b'{"value":3.141592653589793}'

    def test_integral_value(self, impl: Serializer) -> None:
        obj = ValueOf[float](value=1)
        result = impl.dump(ValueOf[float], obj)
        assert result == b'{"value":1}'

    def test_very_small(self, impl: Serializer) -> None:
        obj = ValueOf[float](value=1e-100)
        result = impl.dump(ValueOf[float], obj)
        assert result == b'{"value":1e-100}'

    def test_negative_zero(self, impl: Serializer) -> None:
        obj = ValueOf[float](value=-0.0)
        result = impl.dump(ValueOf[float], obj)
        assert result == b'{"value":-0.0}' or result == b'{"value":0.0}'

    def test_optional_none(self, impl: Serializer) -> None:
        obj = OptionalValueOf[float](value=None)
        result = impl.dump(OptionalValueOf[float], obj)
        assert result == b"{}"

    def test_optional_value(self, impl: Serializer) -> None:
        obj = OptionalValueOf[float](value=3.14)
        result = impl.dump(OptionalValueOf[float], obj)
        assert result == b'{"value":3.14}'

    def test_default_provided(self, impl: Serializer) -> None:
        obj = WithFloatDefault(value=2.71)
        result = impl.dump(WithFloatDefault, obj)
        assert result == b'{"value":2.71}'

    def test_none_handling_ignore_default(self, impl: Serializer) -> None:
        obj = OptionalValueOf[float](value=None)
        result = impl.dump(OptionalValueOf[float], obj)
        assert result == b"{}"

    def test_none_handling_ignore_explicit(self, impl: Serializer) -> None:
        obj = OptionalValueOf[float](value=None)
        result = impl.dump(OptionalValueOf[float], obj, none_value_handling=mr.NoneValueHandling.IGNORE)
        assert result == b"{}"

    def test_none_handling_include(self, impl: Serializer) -> None:
        obj = OptionalValueOf[float](value=None)
        result = impl.dump(OptionalValueOf[float], obj, none_value_handling=mr.NoneValueHandling.INCLUDE)
        assert result == b'{"value":null}'

    def test_none_handling_include_with_value(self, impl: Serializer) -> None:
        obj = OptionalValueOf[float](value=3.14)
        result = impl.dump(OptionalValueOf[float], obj, none_value_handling=mr.NoneValueHandling.INCLUDE)
        assert result == b'{"value":3.14}'

    # Special values - should fail
    def test_nan_fails(self, impl: Serializer) -> None:
        obj = ValueOf[float](value=float("nan"))
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.dump(ValueOf[float], obj)
        assert exc.value.messages == {"value": ["Special numeric values (nan or infinity) are not permitted."]}

    def test_inf_fails(self, impl: Serializer) -> None:
        obj = ValueOf[float](value=float("inf"))
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.dump(ValueOf[float], obj)
        assert exc.value.messages == {"value": ["Special numeric values (nan or infinity) are not permitted."]}

    def test_negative_inf_fails(self, impl: Serializer) -> None:
        obj = ValueOf[float](value=float("-inf"))
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.dump(ValueOf[float], obj)
        assert exc.value.messages == {"value": ["Special numeric values (nan or infinity) are not permitted."]}

    def test_missing(self, impl: Serializer) -> None:
        obj = WithFloatMissing()
        result = impl.dump(WithFloatMissing, obj)
        assert result == b"{}"

    def test_missing_with_value(self, impl: Serializer) -> None:
        obj = WithFloatMissing(value=3.14)
        result = impl.dump(WithFloatMissing, obj)
        assert result == b'{"value":3.14}'

    def test_big_int_value_larger_than_i64_max(self, impl: Serializer) -> None:
        big_value = 9223372036854775808
        obj = ValueOf[float](value=big_value)
        result = impl.dump(ValueOf[float], obj)
        assert result == b'{"value":9223372036854775808}'

    def test_big_int_value_larger_than_u64_max(self, impl: Serializer) -> None:
        huge_value = 18446744073709551616
        obj = ValueOf[float](value=huge_value)
        result = impl.dump(ValueOf[float], obj)
        assert result == b'{"value":18446744073709551616}'

    def test_big_int_value_very_large(self, impl: Serializer) -> None:
        very_large = 2**100
        obj = ValueOf[float](value=very_large)
        result = impl.dump(ValueOf[float], obj)
        assert result == f'{{"value":{very_large}}}'.encode()


class TestFloatLoad:
    def test_positive(self, impl: Serializer) -> None:
        data = b'{"value":3.14}'
        result = impl.load(ValueOf[float], data)
        assert result == ValueOf[float](value=3.14)

    def test_negative(self, impl: Serializer) -> None:
        data = b'{"value":-2.5}'
        result = impl.load(ValueOf[float], data)
        assert result == ValueOf[float](value=-2.5)

    def test_zero(self, impl: Serializer) -> None:
        data = b'{"value":0.0}'
        result = impl.load(ValueOf[float], data)
        assert result == ValueOf[float](value=0.0)

    def test_precision(self, impl: Serializer) -> None:
        data = b'{"value":3.141592653589793}'
        result = impl.load(ValueOf[float], data)
        assert result == ValueOf[float](value=3.141592653589793)

    def test_integral_value(self, impl: Serializer) -> None:
        data = b'{"value":1}'
        result = impl.load(ValueOf[float], data)
        assert result == ValueOf[float](value=1)
        assert type(result.value) is int  # JSON int stays int, no precision loss

    def test_very_small(self, impl: Serializer) -> None:
        data = b'{"value":1e-100}'
        result = impl.load(ValueOf[float], data)
        assert result == ValueOf[float](value=1e-100)

    def test_negative_zero(self, impl: Serializer) -> None:
        data = b'{"value":-0.0}'
        result = impl.load(ValueOf[float], data)
        assert result.value == 0.0

    def test_validation_pass(self, impl: Serializer) -> None:
        data = b'{"value":5.5}'
        result = impl.load(WithFloatValidation, data)
        assert result == WithFloatValidation(value=5.5)

    def test_validation_zero_pass(self, impl: Serializer) -> None:
        data = b'{"value":0.0}'
        result = impl.load(WithFloatValidation, data)
        assert result == WithFloatValidation(value=0.0)

    def test_validation_negative_fail(self, impl: Serializer) -> None:
        data = b'{"value":-1.5}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithFloatValidation, data)
        assert exc.value.messages == {"value": ["Invalid value."]}

    def test_two_validators_pass(self, impl: Serializer) -> None:
        data = b'{"value":50.5}'
        result = impl.load(WithFloatTwoValidators, data)
        assert result == WithFloatTwoValidators(value=50.5)

    def test_two_validators_first_fails(self, impl: Serializer) -> None:
        data = b'{"value":-1.0}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithFloatTwoValidators, data)
        assert exc.value.messages == {"value": ["Invalid value."]}

    def test_two_validators_second_fails(self, impl: Serializer) -> None:
        data = b'{"value":150.0}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithFloatTwoValidators, data)
        assert exc.value.messages == {"value": ["Invalid value."]}

    def test_optional_none(self, impl: Serializer) -> None:
        data = b'{"value":null}'
        result = impl.load(OptionalValueOf[float], data)
        assert result == OptionalValueOf[float](value=None)

    def test_optional_missing(self, impl: Serializer) -> None:
        data = b"{}"
        result = impl.load(OptionalValueOf[float], data)
        assert result == OptionalValueOf[float](value=None)

    def test_optional_value(self, impl: Serializer) -> None:
        data = b'{"value":3.14}'
        result = impl.load(OptionalValueOf[float], data)
        assert result == OptionalValueOf[float](value=3.14)

    def test_default_omitted(self, impl: Serializer) -> None:
        data = b"{}"
        result = impl.load(WithFloatDefault, data)
        assert result == WithFloatDefault(value=3.14)

    def test_default_provided(self, impl: Serializer) -> None:
        data = b'{"value":2.71}'
        result = impl.load(WithFloatDefault, data)
        assert result == WithFloatDefault(value=2.71)

    def test_custom_required_error(self, impl: Serializer) -> None:
        data = b"{}"
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithFloatRequiredError, data)
        assert exc.value.messages == {"value": ["Custom required message"]}

    def test_custom_none_error(self, impl: Serializer) -> None:
        data = b'{"value":null}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithFloatNoneError, data)
        assert exc.value.messages == {"value": ["Custom none message"]}

    def test_custom_invalid_error(self, impl: Serializer) -> None:
        data = b'{"value":"not-a-number"}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithFloatInvalidError, data)
        assert exc.value.messages == {"value": ["Custom invalid message"]}

    def test_wrong_type_string(self, impl: Serializer) -> None:
        data = b'{"value":"not_a_float"}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[float], data)
        assert exc.value.messages == {"value": ["Not a valid number."]}

    def test_wrong_type_list(self, impl: Serializer) -> None:
        data = b'{"value":[1.0,2.0]}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[float], data)
        assert exc.value.messages == {"value": ["Not a valid number."]}

    def test_wrong_type_object(self, impl: Serializer) -> None:
        data = b'{"value":{"key":1.0}}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[float], data)
        assert exc.value.messages == {"value": ["Not a valid number."]}

    def test_missing_required(self, impl: Serializer) -> None:
        data = b"{}"
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[float], data)
        assert exc.value.messages == {"value": ["Missing data for required field."]}

    def test_big_from_int_larger_than_i64_max(self, impl: Serializer) -> None:
        data = b'{"value":9223372036854775808}'
        result = impl.load(ValueOf[float], data)
        assert result == ValueOf[float](value=9223372036854775808.0)

    def test_big_from_int_larger_than_u64_max(self, impl: Serializer) -> None:
        data = b'{"value":18446744073709551616}'
        result = impl.load(ValueOf[float], data)
        assert result == ValueOf[float](value=18446744073709551616.0)

    # Special values - should fail
    def test_nan_fails(self, impl: Serializer) -> None:
        data = b'{"value":NaN}'
        if impl.supports_special_float_validation:
            with pytest.raises(marshmallow.ValidationError) as exc:
                impl.load(ValueOf[float], data)
            assert exc.value.messages == {"value": ["Special numeric values (nan or infinity) are not permitted."]}
        else:
            # NaN is not valid JSON per spec, serde rejects at parsing level
            with pytest.raises(Exception):
                impl.load(ValueOf[float], data)

    def test_inf_fails(self, impl: Serializer) -> None:
        data = b'{"value":Infinity}'
        if impl.supports_special_float_validation:
            with pytest.raises(marshmallow.ValidationError) as exc:
                impl.load(ValueOf[float], data)
            assert exc.value.messages == {"value": ["Special numeric values (nan or infinity) are not permitted."]}
        else:
            # Infinity is not valid JSON per spec, serde rejects at parsing level
            with pytest.raises(Exception):
                impl.load(ValueOf[float], data)

    def test_negative_inf_fails(self, impl: Serializer) -> None:
        data = b'{"value":-Infinity}'
        if impl.supports_special_float_validation:
            with pytest.raises(marshmallow.ValidationError) as exc:
                impl.load(ValueOf[float], data)
            assert exc.value.messages == {"value": ["Special numeric values (nan or infinity) are not permitted."]}
        else:
            # -Infinity is not valid JSON per spec, serde rejects at parsing level
            with pytest.raises(Exception):
                impl.load(ValueOf[float], data)

    def test_from_string(self, impl: Serializer) -> None:
        data = b'{"value":"3.14"}'
        result = impl.load(ValueOf[float], data)
        assert result == ValueOf[float](value=3.14)

    def test_from_string_negative(self, impl: Serializer) -> None:
        data = b'{"value":"-2.5"}'
        result = impl.load(ValueOf[float], data)
        assert result == ValueOf[float](value=-2.5)

    def test_from_string_integer(self, impl: Serializer) -> None:
        data = b'{"value":"42"}'
        result = impl.load(ValueOf[float], data)
        assert result == ValueOf[float](value=42.0)

    def test_from_string_scientific(self, impl: Serializer) -> None:
        data = b'{"value":"1.5e10"}'
        result = impl.load(ValueOf[float], data)
        assert result == ValueOf[float](value=1.5e10)

    def test_from_string_invalid(self, impl: Serializer) -> None:
        data = b'{"value":"not_a_number"}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[float], data)
        assert exc.value.messages == {"value": ["Not a valid number."]}

    def test_from_string_empty(self, impl: Serializer) -> None:
        data = b'{"value":""}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[float], data)
        assert exc.value.messages == {"value": ["Not a valid number."]}

    def test_from_string_nan_fails(self, impl: Serializer) -> None:
        data = b'{"value":"NaN"}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[float], data)
        assert exc.value.messages == {"value": ["Special numeric values (nan or infinity) are not permitted."]}

    def test_from_string_inf_fails(self, impl: Serializer) -> None:
        data = b'{"value":"Infinity"}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[float], data)
        assert exc.value.messages == {"value": ["Special numeric values (nan or infinity) are not permitted."]}

    def test_from_string_negative_inf_fails(self, impl: Serializer) -> None:
        data = b'{"value":"-Infinity"}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[float], data)
        assert exc.value.messages == {"value": ["Special numeric values (nan or infinity) are not permitted."]}

    def test_from_string_arbitrary_precision(self, impl: Serializer) -> None:
        data = b'{"value":"3.141592653589793238462643383279502884197"}'
        result = impl.load(ValueOf[float], data)
        assert result == ValueOf[float](value=3.141592653589793)

    def test_from_string_very_small(self, impl: Serializer) -> None:
        data = b'{"value":"1e-308"}'
        result = impl.load(ValueOf[float], data)
        assert result == ValueOf[float](value=1e-308)

    def test_from_string_very_large(self, impl: Serializer) -> None:
        data = b'{"value":"1e308"}'
        result = impl.load(ValueOf[float], data)
        assert result == ValueOf[float](value=1e308)

    def test_missing(self, impl: Serializer) -> None:
        data = b"{}"
        result = impl.load(WithFloatMissing, data)
        assert result == WithFloatMissing()

    def test_missing_with_value(self, impl: Serializer) -> None:
        data = b'{"value":3.14}'
        result = impl.load(WithFloatMissing, data)
        assert result == WithFloatMissing(value=3.14)


class TestFloatDumpInvalidType:
    """Test that invalid types in float fields raise ValidationError on dump."""

    def test_string(self, impl: Serializer) -> None:
        obj = ValueOf[float](**{"value": "not a float"})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(ValueOf[float], obj)

    def test_bool(self, impl: Serializer) -> None:
        obj = ValueOf[float](**{"value": True})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(ValueOf[float], obj)

    def test_list(self, impl: Serializer) -> None:
        obj = ValueOf[float](**{"value": [1.0, 2.0]})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(ValueOf[float], obj)
