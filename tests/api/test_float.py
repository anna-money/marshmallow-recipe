import marshmallow
import pytest

from .conftest import (
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
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            pytest.param(3.14, b'{"value":3.14}', id="positive"),
            pytest.param(-2.5, b'{"value":-2.5}', id="negative"),
            pytest.param(0.0, b'{"value":0.0}', id="zero"),
            pytest.param(3.141592653589793, b'{"value":3.141592653589793}', id="pi_precision"),
            pytest.param(1, b'{"value":1}', id="integer"),
            pytest.param(1e-100, b'{"value":1e-100}', id="very_small"),
            pytest.param(1e100, b'{"value":1e+100}', id="very_large"),
            pytest.param(1.7976931348623157e308, b'{"value":1.7976931348623157e+308}', id="max_float"),
            pytest.param(2.2250738585072014e-308, b'{"value":2.2250738585072014e-308}', id="min_positive_normal"),
            pytest.param(0.1 + 0.2, b'{"value":0.30000000000000004}', id="float_precision_issue"),
        ],
    )
    def test_values(self, impl: Serializer, value: float, expected: bytes) -> None:
        obj = ValueOf[float](value=value)
        result = impl.dump(ValueOf[float], obj)
        assert result == expected

    def test_negative_zero(self, impl: Serializer) -> None:
        obj = ValueOf[float](value=-0.0)
        result = impl.dump(ValueOf[float], obj)
        assert result == b'{"value":-0.0}' or result == b'{"value":0.0}'

    def test_default_provided(self, impl: Serializer) -> None:
        obj = WithFloatDefault(value=2.71)
        result = impl.dump(WithFloatDefault, obj)
        assert result == b'{"value":2.71}'

    @pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
    def test_special_values_fail(self, impl: Serializer, value: float) -> None:
        obj = ValueOf[float](value=value)
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

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (9223372036854775808, b'{"value":9223372036854775808}'),
            (18446744073709551616, b'{"value":18446744073709551616}'),
            (2**100, f'{{"value":{2**100}}}'.encode()),
        ],
    )
    def test_big_int(self, impl: Serializer, value: int, expected: bytes) -> None:
        obj = ValueOf[float](value=value)
        result = impl.dump(ValueOf[float], obj)
        assert result == expected


class TestFloatLoad:
    @pytest.mark.parametrize(
        ("data", "expected"),
        [
            pytest.param(b'{"value":3.14}', 3.14, id="positive"),
            pytest.param(b'{"value":-2.5}', -2.5, id="negative"),
            pytest.param(b'{"value":0.0}', 0.0, id="zero"),
            pytest.param(b'{"value":3.141592653589793}', 3.141592653589793, id="pi_precision"),
            pytest.param(b'{"value":1}', 1.0, id="integer"),
            pytest.param(b'{"value":1e-100}', 1e-100, id="very_small"),
            pytest.param(b'{"value":-0.0}', 0.0, id="negative_zero"),
            pytest.param(b'{"value":1e+100}', 1e100, id="very_large"),
            pytest.param(b'{"value":1.7976931348623157e+308}', 1.7976931348623157e308, id="max_float"),
            pytest.param(b'{"value":2.2250738585072014e-308}', 2.2250738585072014e-308, id="min_positive_normal"),
        ],
    )
    def test_values(self, impl: Serializer, data: bytes, expected: float) -> None:
        result = impl.load(ValueOf[float], data)
        assert result == ValueOf[float](value=expected)

    def test_validation_pass(self, impl: Serializer) -> None:
        data = b'{"value":5.5}'
        result = impl.load(WithFloatValidation, data)
        assert result == WithFloatValidation(value=5.5)

    @pytest.mark.parametrize(("data", "expected"), [(b'{"value":0.0}', 0.0), (b'{"value":50.5}', 50.5)])
    def test_validation_pass_values(self, impl: Serializer, data: bytes, expected: float) -> None:
        result = impl.load(WithFloatValidation, data)
        assert result == WithFloatValidation(value=expected)

    def test_validation_fail(self, impl: Serializer) -> None:
        data = b'{"value":-1.5}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithFloatValidation, data)
        assert exc.value.messages == {"value": ["Invalid value."]}

    def test_two_validators_pass(self, impl: Serializer) -> None:
        data = b'{"value":50.5}'
        result = impl.load(WithFloatTwoValidators, data)
        assert result == WithFloatTwoValidators(value=50.5)

    @pytest.mark.parametrize("data", [b'{"value":-1.0}', b'{"value":150.0}'])
    def test_two_validators_fail(self, impl: Serializer, data: bytes) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithFloatTwoValidators, data)
        assert exc.value.messages == {"value": ["Invalid value."]}

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

    @pytest.mark.parametrize("data", [b'{"value":"not_a_float"}', b'{"value":[1.0,2.0]}', b'{"value":{"key":1.0}}'])
    def test_wrong_type(self, impl: Serializer, data: bytes) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[float], data)
        assert exc.value.messages == {"value": ["Not a valid number."]}

    @pytest.mark.parametrize(
        ("data", "expected"),
        [
            (b'{"value":9223372036854775808}', 9223372036854775808.0),
            (b'{"value":18446744073709551616}', 18446744073709551616.0),
        ],
    )
    def test_big_int(self, impl: Serializer, data: bytes, expected: float) -> None:
        result = impl.load(ValueOf[float], data)
        assert result == ValueOf[float](value=expected)

    @pytest.mark.parametrize("data", [b'{"value":NaN}', b'{"value":Infinity}', b'{"value":-Infinity}'])
    def test_special_values_fail(self, impl: Serializer, data: bytes) -> None:
        if impl.supports_special_float_validation:
            with pytest.raises(marshmallow.ValidationError) as exc:
                impl.load(ValueOf[float], data)
            assert exc.value.messages == {"value": ["Special numeric values (nan or infinity) are not permitted."]}
        else:
            with pytest.raises(Exception):
                impl.load(ValueOf[float], data)

    @pytest.mark.parametrize(
        ("data", "expected"),
        [
            (b'{"value":"3.14"}', 3.14),
            (b'{"value":"-2.5"}', -2.5),
            (b'{"value":"42"}', 42.0),
            (b'{"value":"1.5e10"}', 1.5e10),
            (b'{"value":"3.141592653589793238462643383279502884197"}', 3.141592653589793),
            (b'{"value":"1e-308"}', 1e-308),
            (b'{"value":"1e308"}', 1e308),
        ],
    )
    def test_from_string(self, impl: Serializer, data: bytes, expected: float) -> None:
        result = impl.load(ValueOf[float], data)
        assert result == ValueOf[float](value=expected)

    @pytest.mark.parametrize("data", [b'{"value":"not_a_number"}', b'{"value":""}'])
    def test_from_string_invalid(self, impl: Serializer, data: bytes) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[float], data)
        assert exc.value.messages == {"value": ["Not a valid number."]}

    @pytest.mark.parametrize("data", [b'{"value":"NaN"}', b'{"value":"Infinity"}', b'{"value":"-Infinity"}'])
    def test_from_string_special_values_fail(self, impl: Serializer, data: bytes) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[float], data)
        assert exc.value.messages == {"value": ["Special numeric values (nan or infinity) are not permitted."]}

    def test_missing(self, impl: Serializer) -> None:
        data = b"{}"
        result = impl.load(WithFloatMissing, data)
        assert result == WithFloatMissing()

    def test_missing_with_value(self, impl: Serializer) -> None:
        data = b'{"value":3.14}'
        result = impl.load(WithFloatMissing, data)
        assert result == WithFloatMissing(value=3.14)


class TestFloatEdgeCases:
    """Test float boundary and special edge cases."""

    @pytest.mark.parametrize(
        ("value", "id_"),
        [
            pytest.param(5e-324, "smallest_subnormal"),
            pytest.param(-5e-324, "negative_smallest_subnormal"),
            pytest.param(1e-307, "near_subnormal_boundary"),
        ],
    )
    def test_subnormal_roundtrip(self, impl: Serializer, value: float, id_: str) -> None:
        obj = ValueOf[float](value=value)
        result = impl.dump(ValueOf[float], obj)
        loaded = impl.load(ValueOf[float], result)
        assert loaded.value == value or abs(loaded.value - value) < 1e-400

    @pytest.mark.parametrize(
        ("data", "expected"),
        [
            pytest.param(b'{"value":1e-400}', 0.0, id="underflow_to_zero"),
            pytest.param(b'{"value":-1e-400}', 0.0, id="negative_underflow_to_zero"),
        ],
    )
    def test_underflow(self, impl: Serializer, data: bytes, expected: float) -> None:
        result = impl.load(ValueOf[float], data)
        assert result.value == expected

    @pytest.mark.parametrize(
        "data",
        [
            pytest.param(b'{"value":1e309}', id="overflow_positive"),
            pytest.param(b'{"value":-1e309}', id="overflow_negative"),
            pytest.param(b'{"value":1e1000}', id="extreme_overflow"),
        ],
    )
    def test_overflow_fails(self, impl: Serializer, data: bytes) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[float], data)
        assert exc.value.messages == {"value": ["Special numeric values (nan or infinity) are not permitted."]}


class TestFloatDumpInvalidType:
    """Test that invalid types in float fields raise ValidationError on dump."""

    @pytest.mark.parametrize("value", ["not a float", True, [1.0, 2.0]])
    def test_invalid_type(self, impl: Serializer, value: object) -> None:
        obj = ValueOf[float](**{"value": value})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(ValueOf[float], obj)
