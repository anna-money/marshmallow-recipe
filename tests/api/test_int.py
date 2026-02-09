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
    @pytest.mark.parametrize(
        "value",
        [
            pytest.param(0, id="zero"),
            pytest.param(42, id="positive"),
            pytest.param(-100, id="negative"),
            pytest.param(-(2**31) - 1, id="i32_min-1"),
            pytest.param(-(2**31), id="i32_min"),
            pytest.param(2**31 - 1, id="i32_max"),
            pytest.param(2**31, id="i32_max+1"),
            pytest.param(2**32 - 1, id="u32_max"),
            pytest.param(2**32, id="u32_max+1"),
            pytest.param(-(2**63) - 1, id="i64_min-1"),
            pytest.param(-(2**63), id="i64_min"),
            pytest.param(2**63 - 1, id="i64_max"),
            pytest.param(2**63, id="i64_max+1"),
            pytest.param(2**64 - 1, id="u64_max"),
            pytest.param(2**64, id="u64_max+1"),
            pytest.param(-(2**127) - 1, id="i128_min-1"),
            pytest.param(-(2**127), id="i128_min"),
            pytest.param(2**127 - 1, id="i128_max"),
            pytest.param(2**127, id="i128_max+1"),
            pytest.param(2**128 - 1, id="u128_max"),
            pytest.param(2**128, id="u128_max+1"),
        ],
    )
    def test_value(self, impl: Serializer, value: int) -> None:
        obj = ValueOf[int](value=value)
        result = impl.dump(ValueOf[int], obj)
        assert result == f'{{"value":{value}}}'.encode()

    @pytest.mark.parametrize(
        ("obj", "expected"),
        [(OptionalValueOf[int](value=None), b"{}"), (OptionalValueOf[int](value=42), b'{"value":42}')],
    )
    def test_optional(self, impl: Serializer, obj: OptionalValueOf[int], expected: bytes) -> None:
        result = impl.dump(OptionalValueOf[int], obj)
        assert result == expected

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

    @pytest.mark.parametrize(
        ("obj", "expected"), [(WithIntMissing(), b"{}"), (WithIntMissing(value=42), b'{"value":42}')]
    )
    def test_missing(self, impl: Serializer, obj: WithIntMissing, expected: bytes) -> None:
        result = impl.dump(WithIntMissing, obj)
        assert result == expected

    @pytest.mark.parametrize(
        "obj",
        [
            pytest.param(ValueOf[int](**{"value": "not an int"}), id="string"),  # type: ignore[arg-type]
            pytest.param(ValueOf[int](**{"value": True}), id="bool"),  # type: ignore[arg-type]
            pytest.param(ValueOf[int](**{"value": 3.14}), id="float"),  # type: ignore[arg-type]
            pytest.param(ValueOf[int](**{"value": [1, 2, 3]}), id="list"),  # type: ignore[arg-type]
        ],
    )
    def test_invalid_type(self, impl: Serializer, obj: ValueOf[int]) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.dump(ValueOf[int], obj)
        if impl.supports_proper_validation_errors_on_dump:
            assert exc.value.messages == {"value": ["Not a valid integer."]}

    def test_custom_invalid_error(self, impl: Serializer) -> None:
        obj = WithIntInvalidError(**{"value": "not an int"})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.dump(WithIntInvalidError, obj)
        if impl.supports_proper_validation_errors_on_dump:
            assert exc.value.messages == {"value": ["Custom invalid message"]}


class TestIntLoad:
    @pytest.mark.parametrize(
        "value",
        [
            pytest.param(0, id="zero"),
            pytest.param(42, id="positive"),
            pytest.param(-100, id="negative"),
            pytest.param(-(2**31) - 1, id="i32_min-1"),
            pytest.param(-(2**31), id="i32_min"),
            pytest.param(2**31 - 1, id="i32_max"),
            pytest.param(2**31, id="i32_max+1"),
            pytest.param(2**32 - 1, id="u32_max"),
            pytest.param(2**32, id="u32_max+1"),
            pytest.param(-(2**63) - 1, id="i64_min-1"),
            pytest.param(-(2**63), id="i64_min"),
            pytest.param(2**63 - 1, id="i64_max"),
            pytest.param(2**63, id="i64_max+1"),
            pytest.param(2**64 - 1, id="u64_max"),
            pytest.param(2**64, id="u64_max+1"),
            pytest.param(-(2**127) - 1, id="i128_min-1"),
            pytest.param(-(2**127), id="i128_min"),
            pytest.param(2**127 - 1, id="i128_max"),
            pytest.param(2**127, id="i128_max+1"),
            pytest.param(2**128 - 1, id="u128_max"),
            pytest.param(2**128, id="u128_max+1"),
        ],
    )
    def test_value(self, impl: Serializer, value: int) -> None:
        data = f'{{"value":{value}}}'.encode()
        result = impl.load(ValueOf[int], data)
        assert result == ValueOf[int](value=value)

    @pytest.mark.parametrize(
        "value",
        [
            pytest.param(-(2**31) - 1, id="i32_min-1"),
            pytest.param(-(2**31), id="i32_min"),
            pytest.param(2**31 - 1, id="i32_max"),
            pytest.param(2**31, id="i32_max+1"),
            pytest.param(2**32 - 1, id="u32_max"),
            pytest.param(2**32, id="u32_max+1"),
            pytest.param(-(2**63) - 1, id="i64_min-1"),
            pytest.param(-(2**63), id="i64_min"),
            pytest.param(2**63 - 1, id="i64_max"),
            pytest.param(2**63, id="i64_max+1"),
            pytest.param(2**64 - 1, id="u64_max"),
            pytest.param(2**64, id="u64_max+1"),
            pytest.param(-(2**127) - 1, id="i128_min-1"),
            pytest.param(-(2**127), id="i128_min"),
            pytest.param(2**127 - 1, id="i128_max"),
            pytest.param(2**127, id="i128_max+1"),
            pytest.param(2**128 - 1, id="u128_max"),
            pytest.param(2**128, id="u128_max+1"),
        ],
    )
    def test_value_as_string(self, impl: Serializer, value: int) -> None:
        data = f'{{"value":"{value}"}}'.encode()
        result = impl.load(ValueOf[int], data)
        assert result == ValueOf[int](value=value)

    def test_validation_pass(self, impl: Serializer) -> None:
        data = b'{"value":10}'
        result = impl.load(WithIntValidation, data)
        assert result == WithIntValidation(value=10)

    @pytest.mark.parametrize(
        "data", [pytest.param(b'{"value":0}', id="zero"), pytest.param(b'{"value":-5}', id="negative")]
    )
    def test_validation_fail(self, impl: Serializer, data: bytes) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithIntValidation, data)
        assert exc.value.messages == {"value": ["Invalid value."]}

    def test_two_validators_pass(self, impl: Serializer) -> None:
        data = b'{"value":50}'
        result = impl.load(WithIntTwoValidators, data)
        assert result == WithIntTwoValidators(value=50)

    @pytest.mark.parametrize(
        "data", [pytest.param(b'{"value":0}', id="first_fails"), pytest.param(b'{"value":150}', id="second_fails")]
    )
    def test_two_validators_fail(self, impl: Serializer, data: bytes) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithIntTwoValidators, data)
        assert exc.value.messages == {"value": ["Invalid value."]}

    @pytest.mark.parametrize(
        ("data", "expected"),
        [
            (b'{"value":null}', OptionalValueOf[int](value=None)),
            (b"{}", OptionalValueOf[int](value=None)),
            (b'{"value":42}', OptionalValueOf[int](value=42)),
            (b'{"value":18446744073709551616}', OptionalValueOf[int](value=18446744073709551616)),
        ],
    )
    def test_optional(self, impl: Serializer, data: bytes, expected: OptionalValueOf[int]) -> None:
        result = impl.load(OptionalValueOf[int], data)
        assert result == expected

    @pytest.mark.parametrize(
        ("data", "expected"), [(b"{}", WithIntDefault(value=42)), (b'{"value":100}', WithIntDefault(value=100))]
    )
    def test_default(self, impl: Serializer, data: bytes, expected: WithIntDefault) -> None:
        result = impl.load(WithIntDefault, data)
        assert result == expected

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

    @pytest.mark.parametrize(
        "data",
        [
            pytest.param(b'{"value":"not_an_int"}', id="string"),
            pytest.param(b'{"value":[1,2,3]}', id="list"),
            pytest.param(b'{"value":{"key":1}}', id="object"),
            pytest.param(b'{"value":3.14}', id="float"),
            pytest.param(b'{"value":1e10}', id="float_exponent"),
            pytest.param(b'{"value":1.0}', id="float_zero"),
        ],
    )
    def test_wrong_type(self, impl: Serializer, data: bytes) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[int], data)
        assert exc.value.messages == {"value": ["Not a valid integer."]}

    def test_missing_required(self, impl: Serializer) -> None:
        data = b"{}"
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[int], data)
        assert exc.value.messages == {"value": ["Missing data for required field."]}

    def test_big_in_list(self, impl: Serializer) -> None:
        data = b'{"items":[1,9223372036854775808,3]}'
        result = impl.load(ListOf[int], data)
        assert result == ListOf[int](items=[1, 9223372036854775808, 3])

    def test_big_in_set(self, impl: Serializer) -> None:
        data = b'{"items":[1,18446744073709551616]}'
        result = impl.load(SetOf[int], data)
        assert result == SetOf[int](items={1, 18446744073709551616})

    def test_big_in_frozenset(self, impl: Serializer) -> None:
        data = b'{"items":[9223372036854775808,2]}'
        result = impl.load(FrozenSetOf[int], data)
        assert result == FrozenSetOf[int](items=frozenset({9223372036854775808, 2}))

    def test_big_in_tuple(self, impl: Serializer) -> None:
        data = b'{"items":[18446744073709551616,1,2]}'
        result = impl.load(TupleOf[int], data)
        assert result == TupleOf[int](items=(18446744073709551616, 1, 2))

    def test_big_in_dict_value(self, impl: Serializer) -> None:
        data = b'{"data":{"key":9223372036854775808}}'
        result = impl.load(DictOf[str, int], data)
        assert result == DictOf[str, int](data={"key": 9223372036854775808})

    def test_big_in_nested(self, impl: Serializer) -> None:
        data = f'{{"name": "John", "age": {9223372036854775808}, "address": {{"street": "Main", "city": "NYC", "zip_code": "10001"}}}}'.encode()
        result = impl.load(Person, data)
        assert result == Person(name="John", age=9223372036854775808, address=result.address)

    @pytest.mark.parametrize(
        ("data", "expected"), [(b"{}", WithIntMissing()), (b'{"value":42}', WithIntMissing(value=42))]
    )
    def test_missing(self, impl: Serializer, data: bytes, expected: WithIntMissing) -> None:
        result = impl.load(WithIntMissing, data)
        assert result == expected
