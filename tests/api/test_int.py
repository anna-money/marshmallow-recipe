import marshmallow
import pytest

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
        ("value", "expected"),
        [
            pytest.param(42, b'{"value":42}', id="positive"),
            pytest.param(-100, b'{"value":-100}', id="negative"),
            pytest.param(0, b'{"value":0}', id="zero"),
            pytest.param(1, b'{"value":1}', id="one"),
            pytest.param(-1, b'{"value":-1}', id="minus_one"),
            pytest.param(9999999999, b'{"value":9999999999}', id="large"),
            # Int32 boundaries
            pytest.param(2147483647, b'{"value":2147483647}', id="int32_max"),
            pytest.param(-2147483648, b'{"value":-2147483648}', id="int32_min"),
            # Int64 boundaries
            pytest.param(9223372036854775807, b'{"value":9223372036854775807}', id="int64_max"),
            pytest.param(-9223372036854775808, b'{"value":-9223372036854775808}', id="int64_min"),
        ],
    )
    def test_values(self, impl: Serializer, value: int, expected: bytes) -> None:
        obj = ValueOf[int](value=value)
        result = impl.dump(ValueOf[int], obj)
        assert result == expected

    def test_default_provided(self, impl: Serializer) -> None:
        obj = WithIntDefault(value=100)
        result = impl.dump(WithIntDefault, obj)
        assert result == b'{"value":100}'

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (9223372036854775808, b'{"value":9223372036854775808}'),
            (18446744073709551616, b'{"value":18446744073709551616}'),
            (2**100, f'{{"value":{2**100}}}'.encode()),
            (-9223372036854775809, b'{"value":-9223372036854775809}'),
            (-(2**100), f'{{"value":{-(2**100)}}}'.encode()),
        ],
    )
    def test_big_int(self, impl: Serializer, value: int, expected: bytes) -> None:
        obj = ValueOf[int](value=value)
        result = impl.dump(ValueOf[int], obj)
        assert result == expected

    def test_missing(self, impl: Serializer) -> None:
        obj = WithIntMissing()
        result = impl.dump(WithIntMissing, obj)
        assert result == b"{}"

    def test_missing_with_value(self, impl: Serializer) -> None:
        obj = WithIntMissing(value=42)
        result = impl.dump(WithIntMissing, obj)
        assert result == b'{"value":42}'


class TestIntLoad:
    @pytest.mark.parametrize(
        ("data", "expected"),
        [
            pytest.param(b'{"value":42}', 42, id="positive"),
            pytest.param(b'{"value":-100}', -100, id="negative"),
            pytest.param(b'{"value":0}', 0, id="zero"),
            pytest.param(b'{"value":1}', 1, id="one"),
            pytest.param(b'{"value":-1}', -1, id="minus_one"),
            pytest.param(b'{"value":9999999999}', 9999999999, id="large"),
            # Int32 boundaries
            pytest.param(b'{"value":2147483647}', 2147483647, id="int32_max"),
            pytest.param(b'{"value":-2147483648}', -2147483648, id="int32_min"),
            # Int64 boundaries
            pytest.param(b'{"value":9223372036854775807}', 9223372036854775807, id="int64_max"),
            pytest.param(b'{"value":-9223372036854775808}', -9223372036854775808, id="int64_min"),
        ],
    )
    def test_values(self, impl: Serializer, data: bytes, expected: int) -> None:
        result = impl.load(ValueOf[int], data)
        assert result == ValueOf[int](value=expected)

    def test_validation_pass(self, impl: Serializer) -> None:
        data = b'{"value":10}'
        result = impl.load(WithIntValidation, data)
        assert result == WithIntValidation(value=10)

    @pytest.mark.parametrize("data", [b'{"value":0}', b'{"value":-5}'])
    def test_validation_fail(self, impl: Serializer, data: bytes) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithIntValidation, data)
        assert exc.value.messages == {"value": ["Invalid value."]}

    def test_two_validators_pass(self, impl: Serializer) -> None:
        data = b'{"value":50}'
        result = impl.load(WithIntTwoValidators, data)
        assert result == WithIntTwoValidators(value=50)

    @pytest.mark.parametrize("data", [b'{"value":0}', b'{"value":150}'])
    def test_two_validators_fail(self, impl: Serializer, data: bytes) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithIntTwoValidators, data)
        assert exc.value.messages == {"value": ["Invalid value."]}

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

    @pytest.mark.parametrize("data", [b'{"value":"not_an_int"}', b'{"value":[1,2,3]}', b'{"value":{"key":1}}'])
    def test_wrong_type(self, impl: Serializer, data: bytes) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[int], data)
        assert exc.value.messages == {"value": ["Not a valid integer."]}

    @pytest.mark.parametrize(
        ("data", "expected"),
        [
            pytest.param(b'{"value":"42"}', 42, id="positive_string"),
            pytest.param(b'{"value":"-100"}', -100, id="negative_string"),
            pytest.param(b'{"value":"0"}', 0, id="zero_string"),
            pytest.param(b'{"value":"9223372036854775807"}', 9223372036854775807, id="int64_max_string"),
        ],
    )
    def test_from_string(self, impl: Serializer, data: bytes, expected: int) -> None:
        result = impl.load(ValueOf[int], data)
        assert result == ValueOf[int](value=expected)

    @pytest.mark.parametrize("data", [b'{"value":""}', b'{"value":"12.5"}', b'{"value":"1e10"}'])
    def test_from_string_invalid(self, impl: Serializer, data: bytes) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[int], data)
        assert exc.value.messages == {"value": ["Not a valid integer."]}

    @pytest.mark.parametrize("data", [b'{"value":3.14}', b'{"value":1e10}', b'{"value":1.0}'])
    def test_rejects_float(self, impl: Serializer, data: bytes) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[int], data)
        assert exc.value.messages == {"value": ["Not a valid integer."]}

    @pytest.mark.parametrize(
        ("data", "expected"),
        [
            (b'{"value":9223372036854775808}', 9223372036854775808),
            (b'{"value":18446744073709551616}', 18446744073709551616),
            (f'{{"value":{2**100}}}'.encode(), 2**100),
            (b'{"value":-9223372036854775809}', -9223372036854775809),
            (f'{{"value":{-(2**100)}}}'.encode(), -(2**100)),
        ],
    )
    def test_big_int(self, impl: Serializer, data: bytes, expected: int) -> None:
        result = impl.load(ValueOf[int], data)
        assert result == ValueOf[int](value=expected)

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


class TestIntEdgeCases:
    """Test int boundary crossing edge cases."""

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            pytest.param(2147483648, b'{"value":2147483648}', id="int32_max_plus_1"),
            pytest.param(-2147483649, b'{"value":-2147483649}', id="int32_min_minus_1"),
            pytest.param(9223372036854775808, b'{"value":9223372036854775808}', id="int64_max_plus_1"),
            pytest.param(-9223372036854775809, b'{"value":-9223372036854775809}', id="int64_min_minus_1"),
            pytest.param(18446744073709551615, b'{"value":18446744073709551615}', id="uint64_max"),
            pytest.param(18446744073709551616, b'{"value":18446744073709551616}', id="uint64_max_plus_1"),
        ],
    )
    def test_boundary_crossings_dump(self, impl: Serializer, value: int, expected: bytes) -> None:
        obj = ValueOf[int](value=value)
        result = impl.dump(ValueOf[int], obj)
        assert result == expected

    @pytest.mark.parametrize(
        ("data", "expected"),
        [
            pytest.param(b'{"value":2147483648}', 2147483648, id="int32_max_plus_1"),
            pytest.param(b'{"value":-2147483649}', -2147483649, id="int32_min_minus_1"),
            pytest.param(b'{"value":9223372036854775808}', 9223372036854775808, id="int64_max_plus_1"),
            pytest.param(b'{"value":-9223372036854775809}', -9223372036854775809, id="int64_min_minus_1"),
            pytest.param(b'{"value":18446744073709551615}', 18446744073709551615, id="uint64_max"),
            pytest.param(b'{"value":18446744073709551616}', 18446744073709551616, id="uint64_max_plus_1"),
        ],
    )
    def test_boundary_crossings_load(self, impl: Serializer, data: bytes, expected: int) -> None:
        result = impl.load(ValueOf[int], data)
        assert result == ValueOf[int](value=expected)

    def test_powers_of_two_roundtrip(self, impl: Serializer) -> None:
        for exp in [31, 32, 63, 64, 100, 127]:
            value = 2**exp
            obj = ValueOf[int](value=value)
            result = impl.dump(ValueOf[int], obj)
            loaded = impl.load(ValueOf[int], result)
            assert loaded.value == value


class TestIntDumpInvalidType:
    """Test that invalid types in int fields raise ValidationError on dump."""

    @pytest.mark.parametrize("value", ["not an int", True, 3.14, [1, 2, 3]])
    def test_invalid_type(self, impl: Serializer, value: object) -> None:
        obj = ValueOf[int](**{"value": value})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(ValueOf[int], obj)
