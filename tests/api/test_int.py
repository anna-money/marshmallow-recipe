import marshmallow
import pytest

import marshmallow_recipe as mr

from .conftest import (
    DictOf,
    FrozenSetOf,
    ListOf,
    OptionalValueOf,
    Person,
    Serializer,
    SetOf,
    TupleOf,
    ValueOf,
    WithIntDefault,
    WithIntInvalidError,
    WithIntMissing,
    WithIntNoneError,
    WithIntRequiredError,
    WithIntTwoValidators,
    WithIntValidation,
)


class TestIntDump:
    def test_positive(self, impl: Serializer) -> None:
        obj = ValueOf[int](value=42)
        result = impl.dump(ValueOf[int], obj)
        assert result == b'{"value":42}'

    def test_negative(self, impl: Serializer) -> None:
        obj = ValueOf[int](value=-100)
        result = impl.dump(ValueOf[int], obj)
        assert result == b'{"value":-100}'

    def test_zero(self, impl: Serializer) -> None:
        obj = ValueOf[int](value=0)
        result = impl.dump(ValueOf[int], obj)
        assert result == b'{"value":0}'

    def test_large(self, impl: Serializer) -> None:
        obj = ValueOf[int](value=9999999999)
        result = impl.dump(ValueOf[int], obj)
        assert result == b'{"value":9999999999}'

    def test_optional_none(self, impl: Serializer) -> None:
        obj = OptionalValueOf[int](value=None)
        result = impl.dump(OptionalValueOf[int], obj)
        assert result == b"{}"

    def test_optional_value(self, impl: Serializer) -> None:
        obj = OptionalValueOf[int](value=42)
        result = impl.dump(OptionalValueOf[int], obj)
        assert result == b'{"value":42}'

    def test_default_provided(self, impl: Serializer) -> None:
        obj = WithIntDefault(value=100)
        result = impl.dump(WithIntDefault, obj)
        assert result == b'{"value":100}'

    def test_none_handling_ignore_default(self, impl: Serializer) -> None:
        obj = OptionalValueOf[int](value=None)
        result = impl.dump(OptionalValueOf[int], obj)
        assert result == b"{}"

    def test_none_handling_ignore_explicit(self, impl: Serializer) -> None:
        obj = OptionalValueOf[int](value=None)
        result = impl.dump(OptionalValueOf[int], obj, none_value_handling=mr.NoneValueHandling.IGNORE)
        assert result == b"{}"

    def test_none_handling_include(self, impl: Serializer) -> None:
        obj = OptionalValueOf[int](value=None)
        result = impl.dump(OptionalValueOf[int], obj, none_value_handling=mr.NoneValueHandling.INCLUDE)
        assert result == b'{"value":null}'

    def test_none_handling_include_with_value(self, impl: Serializer) -> None:
        obj = OptionalValueOf[int](value=42)
        result = impl.dump(OptionalValueOf[int], obj, none_value_handling=mr.NoneValueHandling.INCLUDE)
        assert result == b'{"value":42}'

    def test_big_larger_than_i64_max(self, impl: Serializer) -> None:
        big_value = 9223372036854775808
        obj = ValueOf[int](value=big_value)
        result = impl.dump(ValueOf[int], obj)
        assert result == b'{"value":9223372036854775808}'

    def test_big_larger_than_u64_max(self, impl: Serializer) -> None:
        huge_value = 18446744073709551616
        obj = ValueOf[int](value=huge_value)
        result = impl.dump(ValueOf[int], obj)
        assert result == b'{"value":18446744073709551616}'

    def test_big_very_large(self, impl: Serializer) -> None:
        very_large = 2**100
        obj = ValueOf[int](value=very_large)
        result = impl.dump(ValueOf[int], obj)
        assert result == f'{{"value":{very_large}}}'.encode()

    def test_big_negative_larger_than_i64_min(self, impl: Serializer) -> None:
        big_negative = -9223372036854775809
        obj = ValueOf[int](value=big_negative)
        result = impl.dump(ValueOf[int], obj)
        assert result == b'{"value":-9223372036854775809}'

    def test_big_very_large_negative(self, impl: Serializer) -> None:
        very_large_neg = -(2**100)
        obj = ValueOf[int](value=very_large_neg)
        result = impl.dump(ValueOf[int], obj)
        assert result == f'{{"value":{very_large_neg}}}'.encode()

    def test_missing(self, impl: Serializer) -> None:
        obj = WithIntMissing()
        result = impl.dump(WithIntMissing, obj)
        assert result == b"{}"

    def test_missing_with_value(self, impl: Serializer) -> None:
        obj = WithIntMissing(value=42)
        result = impl.dump(WithIntMissing, obj)
        assert result == b'{"value":42}'


class TestIntLoad:
    def test_positive(self, impl: Serializer) -> None:
        data = b'{"value":42}'
        result = impl.load(ValueOf[int], data)
        assert result == ValueOf[int](value=42)

    def test_negative(self, impl: Serializer) -> None:
        data = b'{"value":-100}'
        result = impl.load(ValueOf[int], data)
        assert result == ValueOf[int](value=-100)

    def test_zero(self, impl: Serializer) -> None:
        data = b'{"value":0}'
        result = impl.load(ValueOf[int], data)
        assert result == ValueOf[int](value=0)

    def test_large(self, impl: Serializer) -> None:
        data = b'{"value":9999999999}'
        result = impl.load(ValueOf[int], data)
        assert result == ValueOf[int](value=9999999999)

    def test_validation_pass(self, impl: Serializer) -> None:
        data = b'{"value":10}'
        result = impl.load(WithIntValidation, data)
        assert result == WithIntValidation(value=10)

    def test_validation_zero_fail(self, impl: Serializer) -> None:
        data = b'{"value":0}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithIntValidation, data)
        assert exc.value.messages == {"value": ["Invalid value."]}

    def test_validation_negative_fail(self, impl: Serializer) -> None:
        data = b'{"value":-5}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithIntValidation, data)
        assert exc.value.messages == {"value": ["Invalid value."]}

    def test_two_validators_pass(self, impl: Serializer) -> None:
        data = b'{"value":50}'
        result = impl.load(WithIntTwoValidators, data)
        assert result == WithIntTwoValidators(value=50)

    def test_two_validators_first_fails(self, impl: Serializer) -> None:
        data = b'{"value":0}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithIntTwoValidators, data)
        assert exc.value.messages == {"value": ["Invalid value."]}

    def test_two_validators_second_fails(self, impl: Serializer) -> None:
        data = b'{"value":150}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithIntTwoValidators, data)
        assert exc.value.messages == {"value": ["Invalid value."]}

    def test_optional_none(self, impl: Serializer) -> None:
        data = b'{"value":null}'
        result = impl.load(OptionalValueOf[int], data)
        assert result == OptionalValueOf[int](value=None)

    def test_optional_missing(self, impl: Serializer) -> None:
        data = b"{}"
        result = impl.load(OptionalValueOf[int], data)
        assert result == OptionalValueOf[int](value=None)

    def test_optional_value(self, impl: Serializer) -> None:
        data = b'{"value":42}'
        result = impl.load(OptionalValueOf[int], data)
        assert result == OptionalValueOf[int](value=42)

    def test_default_omitted(self, impl: Serializer) -> None:
        data = b"{}"
        result = impl.load(WithIntDefault, data)
        assert result == WithIntDefault(value=42)

    def test_default_provided(self, impl: Serializer) -> None:
        data = b'{"value":100}'
        result = impl.load(WithIntDefault, data)
        assert result == WithIntDefault(value=100)

    def test_custom_required_error(self, impl: Serializer) -> None:
        data = b"{}"
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithIntRequiredError, data)
        assert exc.value.messages == {"value": ["Custom required message"]}

    def test_custom_none_error(self, impl: Serializer) -> None:
        data = b'{"value":null}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithIntNoneError, data)
        assert exc.value.messages == {"value": ["Custom none message"]}

    def test_custom_invalid_error(self, impl: Serializer) -> None:
        data = b'{"value":"not-a-number"}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithIntInvalidError, data)
        assert exc.value.messages == {"value": ["Custom invalid message"]}

    def test_wrong_type_string(self, impl: Serializer) -> None:
        data = b'{"value":"not_an_int"}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[int], data)
        assert exc.value.messages == {"value": ["Not a valid integer."]}

    def test_wrong_type_list(self, impl: Serializer) -> None:
        data = b'{"value":[1,2,3]}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[int], data)
        assert exc.value.messages == {"value": ["Not a valid integer."]}

    def test_wrong_type_object(self, impl: Serializer) -> None:
        data = b'{"value":{"key":1}}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[int], data)
        assert exc.value.messages == {"value": ["Not a valid integer."]}

    def test_missing_required(self, impl: Serializer) -> None:
        data = b"{}"
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[int], data)
        assert exc.value.messages == {"value": ["Missing data for required field."]}

    def test_rejects_float(self, impl: Serializer) -> None:
        data = b'{"value":3.14}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[int], data)
        assert exc.value.messages == {"value": ["Not a valid integer."]}

    def test_rejects_float_with_exponent(self, impl: Serializer) -> None:
        data = b'{"value":1e10}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[int], data)
        assert exc.value.messages == {"value": ["Not a valid integer."]}

    def test_rejects_float_zero(self, impl: Serializer) -> None:
        data = b'{"value":1.0}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[int], data)
        assert exc.value.messages == {"value": ["Not a valid integer."]}

    def test_big_larger_than_i64_max(self, impl: Serializer) -> None:
        big_value = 9223372036854775808
        data = b'{"value":9223372036854775808}'
        result = impl.load(ValueOf[int], data)
        assert result == ValueOf[int](value=big_value)

    def test_big_larger_than_u64_max(self, impl: Serializer) -> None:
        huge_value = 18446744073709551616
        data = b'{"value":18446744073709551616}'
        result = impl.load(ValueOf[int], data)
        assert result == ValueOf[int](value=huge_value)

    def test_big_very_large(self, impl: Serializer) -> None:
        very_large = 2**100
        data = f'{{"value": {very_large}}}'.encode()
        result = impl.load(ValueOf[int], data)
        assert result == ValueOf[int](value=very_large)

    def test_big_negative_larger_than_i64_min(self, impl: Serializer) -> None:
        big_negative = -9223372036854775809
        data = b'{"value":-9223372036854775809}'
        result = impl.load(ValueOf[int], data)
        assert result == ValueOf[int](value=big_negative)

    def test_big_very_large_negative(self, impl: Serializer) -> None:
        very_large_neg = -(2**100)
        data = f'{{"value": {very_large_neg}}}'.encode()
        result = impl.load(ValueOf[int], data)
        assert result == ValueOf[int](value=very_large_neg)

    def test_big_in_list(self, impl: Serializer) -> None:
        big_value = 9223372036854775808
        data = b'{"items":[1,9223372036854775808,3]}'
        result = impl.load(ListOf[int], data)
        assert result == ListOf[int](items=[1, big_value, 3])

    def test_big_in_set(self, impl: Serializer) -> None:
        big_value = 18446744073709551616
        data = b'{"items":[1,18446744073709551616]}'
        result = impl.load(SetOf[int], data)
        assert result == SetOf[int](items={1, big_value})

    def test_big_in_frozenset(self, impl: Serializer) -> None:
        big_value = 9223372036854775808
        data = b'{"items":[9223372036854775808,2]}'
        result = impl.load(FrozenSetOf[int], data)
        assert result == FrozenSetOf[int](items=frozenset({big_value, 2}))

    def test_big_in_tuple(self, impl: Serializer) -> None:
        big_value = 18446744073709551616
        data = b'{"items":[18446744073709551616,1,2]}'
        result = impl.load(TupleOf[int], data)
        assert result == TupleOf[int](items=(big_value, 1, 2))

    def test_big_in_dict_value(self, impl: Serializer) -> None:
        big_value = 9223372036854775808
        data = b'{"data":{"key":9223372036854775808}}'
        result = impl.load(DictOf[str, int], data)
        assert result == DictOf[str, int](data={"key": big_value})

    def test_big_in_optional(self, impl: Serializer) -> None:
        big_value = 18446744073709551616
        data = b'{"value":18446744073709551616}'
        result = impl.load(OptionalValueOf[int], data)
        assert result == OptionalValueOf[int](value=big_value)

    def test_big_in_nested(self, impl: Serializer) -> None:
        big_age = 9223372036854775808
        data = f'{{"name": "John", "age": {big_age}, "address": {{"street": "Main", "city": "NYC", "zip_code": "10001"}}}}'.encode()
        result = impl.load(Person, data)
        assert result == Person(name="John", age=big_age, address=result.address)

    def test_missing(self, impl: Serializer) -> None:
        data = b"{}"
        result = impl.load(WithIntMissing, data)
        assert result == WithIntMissing()

    def test_missing_with_value(self, impl: Serializer) -> None:
        data = b'{"value":42}'
        result = impl.load(WithIntMissing, data)
        assert result == WithIntMissing(value=42)


class TestIntDumpInvalidType:
    """Test that invalid types in int fields raise ValidationError on dump."""

    def test_string(self, impl: Serializer) -> None:
        obj = ValueOf[int](**{"value": "not an int"})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(ValueOf[int], obj)

    def test_bool(self, impl: Serializer) -> None:
        obj = ValueOf[int](**{"value": True})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(ValueOf[int], obj)

    def test_float(self, impl: Serializer) -> None:
        obj = ValueOf[int](**{"value": 3.14})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(ValueOf[int], obj)

    def test_list(self, impl: Serializer) -> None:
        obj = ValueOf[int](**{"value": [1, 2, 3]})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(ValueOf[int], obj)
