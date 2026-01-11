import decimal

import marshmallow
import pytest

from .conftest import (
    Serializer,
    WithAnnotatedDecimalPlaces,
    WithAnnotatedDecimalRounding,
    WithDecimal,
    WithDecimalInvalidError,
    WithDecimalMissing,
    WithDecimalNoneError,
    WithDecimalNoPlaces,
    WithDecimalRequiredError,
    WithDecimalRoundDown,
    WithDecimalRoundUp,
    WithDecimalTwoValidators,
    WithDecimalValidation,
)


class TestDecimalDump:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            pytest.param("99.99", b'{"value":"99.99"}', id="positive"),
            pytest.param("-999.99", b'{"value":"-999.99"}', id="negative"),
            pytest.param("0", b'{"value":"0.00"}', id="zero"),
            pytest.param("999999999999999.99", b'{"value":"999999999999999.99"}', id="large"),
            pytest.param("0.01", b'{"value":"0.01"}', id="small_positive"),
            pytest.param("-0.01", b'{"value":"-0.01"}', id="small_negative"),
            pytest.param("1E+10", b'{"value":"10000000000.00"}', id="scientific_notation"),
            pytest.param("1.00", b'{"value":"1.00"}', id="trailing_zeros"),
            pytest.param("-0", b'{"value":"-0.00"}', id="negative_zero"),
            pytest.param("0.001", b'{"value":"0.00"}', id="rounds_to_zero"),
        ],
    )
    def test_values(self, impl: Serializer, value: str, expected: bytes) -> None:
        obj = WithDecimal(value=decimal.Decimal(value))
        result = impl.dump(WithDecimal, obj)
        assert result == expected

    @pytest.mark.parametrize(
        ("places", "expected"),
        [
            (0, b'{"value":"123"}'),
            (1, b'{"value":"123.5"}'),
            (3, b'{"value":"123.456"}'),
            (5, b'{"value":"123.45600"}'),
        ],
    )
    def test_global_places(self, impl: Serializer, places: int, expected: bytes) -> None:
        obj = WithDecimal(value=decimal.Decimal("123.456"))
        result = impl.dump(WithDecimal, obj, decimal_places=places)
        assert result == expected

    def test_field_places_overrides_global(self, impl: Serializer) -> None:
        obj = WithAnnotatedDecimalPlaces(value=decimal.Decimal("123.456789"))
        result = impl.dump(WithAnnotatedDecimalPlaces, obj, decimal_places=1)
        assert result == b'{"value":"123.4568"}'

    def test_annotated_places(self, impl: Serializer) -> None:
        obj = WithAnnotatedDecimalPlaces(value=decimal.Decimal("123.456789"))
        result = impl.dump(WithAnnotatedDecimalPlaces, obj)
        assert result == b'{"value":"123.4568"}'

    @pytest.mark.parametrize(
        ("value", "expected"),
        [("1.234", b'{"value":"1.24"}'), ("1.235", b'{"value":"1.24"}'), ("1.20", b'{"value":"1.20"}')],
    )
    def test_round_up(self, impl: Serializer, value: str, expected: bytes) -> None:
        obj = WithDecimalRoundUp(value=decimal.Decimal(value))
        result = impl.dump(WithDecimalRoundUp, obj)
        assert result == expected

    @pytest.mark.parametrize(("value", "expected"), [("1.239", b'{"value":"1.23"}'), ("1.235", b'{"value":"1.23"}')])
    def test_round_down(self, impl: Serializer, value: str, expected: bytes) -> None:
        obj = WithDecimalRoundDown(value=decimal.Decimal(value))
        result = impl.dump(WithDecimalRoundDown, obj)
        assert result == expected

    def test_annotated_rounding(self, impl: Serializer) -> None:
        obj = WithAnnotatedDecimalRounding(value=decimal.Decimal("5.123"))
        result = impl.dump(WithAnnotatedDecimalRounding, obj)
        assert result == b'{"value":"5.13"}'

    def test_missing(self, impl: Serializer) -> None:
        obj = WithDecimalMissing()
        result = impl.dump(WithDecimalMissing, obj)
        assert result == b"{}"

    def test_missing_with_value(self, impl: Serializer) -> None:
        obj = WithDecimalMissing(value=decimal.Decimal("99.99"))
        result = impl.dump(WithDecimalMissing, obj)
        assert result == b'{"value":"99.99"}'


class TestDecimalLoad:
    @pytest.mark.parametrize(
        ("data", "expected"),
        [
            pytest.param(b'{"value":"99.99"}', decimal.Decimal("99.99"), id="positive"),
            pytest.param(b'{"value":"-99.99"}', decimal.Decimal("-99.99"), id="negative"),
            pytest.param(b'{"value":"0"}', decimal.Decimal("0"), id="zero"),
            pytest.param(b'{"value":"0.00"}', decimal.Decimal("0.00"), id="zero_with_decimals"),
            pytest.param(b'{"value":"1E+10"}', decimal.Decimal("1E+10"), id="scientific_notation"),
            pytest.param(b'{"value":99.99}', decimal.Decimal("99.99"), id="from_number"),
            pytest.param(b'{"value":100}', decimal.Decimal("100"), id="from_integer"),
            pytest.param(b'{"value":"-0"}', decimal.Decimal("-0"), id="negative_zero_string"),
            pytest.param(b'{"value":-0}', decimal.Decimal("0"), id="negative_zero_number"),
        ],
    )
    def test_value(self, impl: Serializer, data: bytes, expected: decimal.Decimal) -> None:
        result = impl.load(WithDecimal, data)
        assert result == WithDecimal(value=expected)

    def test_annotated_places(self, impl: Serializer) -> None:
        data = b'{"value":"99.12345"}'
        result = impl.load(WithAnnotatedDecimalPlaces, data)
        assert result == WithAnnotatedDecimalPlaces(value=decimal.Decimal("99.1234"))

    def test_round_up(self, impl: Serializer) -> None:
        data = b'{"value":"9.876"}'
        result = impl.load(WithDecimalRoundUp, data)
        assert result == WithDecimalRoundUp(value=decimal.Decimal("9.88"))

    def test_round_down(self, impl: Serializer) -> None:
        data = b'{"value":"7.654"}'
        result = impl.load(WithDecimalRoundDown, data)
        assert result == WithDecimalRoundDown(value=decimal.Decimal("7.65"))

    def test_annotated_rounding(self, impl: Serializer) -> None:
        data = b'{"value":"7.654"}'
        result = impl.load(WithAnnotatedDecimalRounding, data)
        assert result == WithAnnotatedDecimalRounding(value=decimal.Decimal("7.66"))

    @pytest.mark.parametrize(
        ("places", "expected"),
        [
            (0, decimal.Decimal("123")),
            (1, decimal.Decimal("123.5")),
            (3, decimal.Decimal("123.456")),
            (5, decimal.Decimal("123.45600")),
        ],
    )
    def test_global_places(self, impl: Serializer, places: int, expected: decimal.Decimal) -> None:
        data = b'{"value":"123.456"}'
        result = impl.load(WithDecimal, data, decimal_places=places)
        assert result == WithDecimal(value=expected)

    def test_field_places_overrides_global(self, impl: Serializer) -> None:
        data = b'{"value":"123.456789"}'
        result = impl.load(WithAnnotatedDecimalPlaces, data, decimal_places=1)
        assert result == WithAnnotatedDecimalPlaces(value=decimal.Decimal("123.4568"))

    def test_validation_pass(self, impl: Serializer) -> None:
        data = b'{"value":"10.5"}'
        result = impl.load(WithDecimalValidation, data)
        assert result == WithDecimalValidation(value=decimal.Decimal("10.5"))

    @pytest.mark.parametrize("data", [b'{"value":"0"}', b'{"value":"-5.5"}'])
    def test_validation_fail(self, impl: Serializer, data: bytes) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithDecimalValidation, data)
        assert exc.value.messages == {"value": ["Invalid value."]}

    def test_two_validators_pass(self, impl: Serializer) -> None:
        data = b'{"value":"50.5"}'
        result = impl.load(WithDecimalTwoValidators, data)
        assert result == WithDecimalTwoValidators(value=decimal.Decimal("50.5"))

    @pytest.mark.parametrize("data", [b'{"value":"0"}', b'{"value":"1500"}'])
    def test_two_validators_fail(self, impl: Serializer, data: bytes) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithDecimalTwoValidators, data)
        assert exc.value.messages == {"value": ["Invalid value."]}

    def test_custom_required_error(self, impl: Serializer) -> None:
        data = b"{}"
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithDecimalRequiredError, data)
        assert exc.value.messages == {"value": ["Custom required message"]}

    def test_custom_none_error(self, impl: Serializer) -> None:
        data = b'{"value":null}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithDecimalNoneError, data)
        assert exc.value.messages == {"value": ["Custom none message"]}

    def test_custom_invalid_error(self, impl: Serializer) -> None:
        data = b'{"value":"not-a-decimal"}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithDecimalInvalidError, data)
        assert exc.value.messages == {"value": ["Custom invalid message"]}

    @pytest.mark.parametrize("data", [b'{"value":"not-a-decimal"}', b'{"value":[1,2]}', b'{"value":{"key":"1.23"}}'])
    def test_invalid_format(self, impl: Serializer, data: bytes) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithDecimal, data)
        assert exc.value.messages == {"value": ["Not a valid number."]}

    @pytest.mark.parametrize(
        ("data", "expected"),
        [
            (b'{"value":9223372036854775808}', decimal.Decimal("9223372036854775808")),
            (b'{"value":18446744073709551616}', decimal.Decimal("18446744073709551616")),
        ],
    )
    def test_big_int(self, impl: Serializer, data: bytes, expected: decimal.Decimal) -> None:
        result = impl.load(WithDecimal, data)
        assert result == WithDecimal(value=expected)

    def test_missing(self, impl: Serializer) -> None:
        data = b"{}"
        result = impl.load(WithDecimalMissing, data)
        assert result == WithDecimalMissing()

    def test_missing_with_value(self, impl: Serializer) -> None:
        data = b'{"value":"99.99"}'
        result = impl.load(WithDecimalMissing, data)
        assert result == WithDecimalMissing(value=decimal.Decimal("99.99"))


class TestDecimalDumpInvalidType:
    """Test that invalid types in decimal fields raise ValidationError on dump."""

    @pytest.mark.parametrize("value", ["123.45", 123, 123.45])
    def test_invalid_type(self, impl: Serializer, value: object) -> None:
        obj = WithDecimal(**{"value": value})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(WithDecimal, obj)


class TestDecimalNoPlaces:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("123.456789012345678901234567890", b'{"value":"123.456789012345678901234567890"}'),
            ("99.99", b'{"value":"99.99"}'),
            ("100", b'{"value":"100"}'),
        ],
    )
    def test_dump(self, impl: Serializer, value: str, expected: bytes) -> None:
        obj = WithDecimalNoPlaces(value=decimal.Decimal(value))
        result = impl.dump(WithDecimalNoPlaces, obj)
        assert result == expected

    def test_dump_overrides_global_places(self, impl: Serializer) -> None:
        obj = WithDecimalNoPlaces(value=decimal.Decimal("123.456789"))
        result = impl.dump(WithDecimalNoPlaces, obj, decimal_places=2)
        assert result == b'{"value":"123.456789"}'

    def test_load_preserves_full_precision(self, impl: Serializer) -> None:
        data = b'{"value":"123.456789012345678901234567890"}'
        result = impl.load(WithDecimalNoPlaces, data)
        assert result == WithDecimalNoPlaces(value=decimal.Decimal("123.456789012345678901234567890"))

    def test_load_overrides_global_places(self, impl: Serializer) -> None:
        data = b'{"value":"123.456789"}'
        result = impl.load(WithDecimalNoPlaces, data, decimal_places=2)
        assert result == WithDecimalNoPlaces(value=decimal.Decimal("123.456789"))


class TestDecimalPrecisionEdgeCases:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            pytest.param("0.1", b'{"value":"0.10"}', id="simple_decimal"),
            pytest.param("0.10", b'{"value":"0.10"}', id="trailing_zero"),
            pytest.param("0.100", b'{"value":"0.10"}', id="extra_trailing_zeros"),
            pytest.param("1.005", b'{"value":"1.00"}', id="rounding_half"),
            pytest.param("1.015", b'{"value":"1.02"}', id="rounding_half_up"),
            pytest.param("99.999", b'{"value":"100.00"}', id="rounding_overflow"),
        ],
    )
    def test_dump_rounding(self, impl: Serializer, value: str, expected: bytes) -> None:
        obj = WithDecimal(value=decimal.Decimal(value))
        result = impl.dump(WithDecimal, obj)
        assert result == expected

    @pytest.mark.parametrize(
        ("data", "expected"),
        [
            pytest.param(b'{"value":"0.1"}', decimal.Decimal("0.10"), id="simple"),
            pytest.param(b'{"value":"0.10"}', decimal.Decimal("0.10"), id="with_trailing"),
            pytest.param(b'{"value":"0.100"}', decimal.Decimal("0.10"), id="extra_trailing"),
            pytest.param(b'{"value":"99.999"}', decimal.Decimal("100.00"), id="rounding_overflow"),
        ],
    )
    def test_load_rounding(self, impl: Serializer, data: bytes, expected: decimal.Decimal) -> None:
        result = impl.load(WithDecimal, data)
        assert result == WithDecimal(value=expected)


class TestDecimalEdgeCases:
    """Test decimal edge cases with boundary values and special representations."""

    @pytest.mark.parametrize(
        ("value", "id_"),
        [
            pytest.param("0.00000000000000000000000000001", "very_small_positive"),
            pytest.param("-0.00000000000000000000000000001", "very_small_negative"),
            pytest.param("99999999999999999999999999999", "very_large_positive"),
            pytest.param("-99999999999999999999999999999", "very_large_negative"),
        ],
    )
    def test_extreme_values_roundtrip(self, impl: Serializer, value: str, id_: str) -> None:
        obj = WithDecimalNoPlaces(value=decimal.Decimal(value))
        result = impl.dump(WithDecimalNoPlaces, obj)
        loaded = impl.load(WithDecimalNoPlaces, result)
        assert loaded.value == decimal.Decimal(value)

    @pytest.mark.parametrize(
        "value",
        [
            pytest.param("1E-28", id="scientific_small"),
            pytest.param("1E+28", id="scientific_large"),
            pytest.param("1.23E+10", id="scientific_with_decimals"),
            pytest.param("1.23E-10", id="scientific_negative_exp"),
        ],
    )
    def test_scientific_notation_roundtrip(self, impl: Serializer, value: str) -> None:
        obj = WithDecimalNoPlaces(value=decimal.Decimal(value))
        result = impl.dump(WithDecimalNoPlaces, obj)
        loaded = impl.load(WithDecimalNoPlaces, result)
        assert loaded.value == decimal.Decimal(value)

    def test_precision_30_digits(self, impl: Serializer) -> None:
        value = "1.23456789012345678901234567890"
        obj = WithDecimalNoPlaces(value=decimal.Decimal(value))
        result = impl.dump(WithDecimalNoPlaces, obj)
        loaded = impl.load(WithDecimalNoPlaces, result)
        assert loaded.value == decimal.Decimal(value)

    def test_many_trailing_zeros(self, impl: Serializer) -> None:
        obj = WithDecimalNoPlaces(value=decimal.Decimal("1.00000000000000000000"))
        result = impl.dump(WithDecimalNoPlaces, obj)
        loaded = impl.load(WithDecimalNoPlaces, result)
        assert loaded.value == decimal.Decimal("1.00000000000000000000")

    @pytest.mark.parametrize(
        "data",
        [
            pytest.param(b'{"value":"inf"}', id="inf_lowercase"),
            pytest.param(b'{"value":"Inf"}', id="inf_titlecase"),
            pytest.param(b'{"value":"INF"}', id="inf_uppercase"),
            pytest.param(b'{"value":"-inf"}', id="neg_inf"),
            pytest.param(b'{"value":"nan"}', id="nan_lowercase"),
            pytest.param(b'{"value":"NaN"}', id="nan_titlecase"),
        ],
    )
    def test_special_values_rejected(self, impl: Serializer, data: bytes) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithDecimal, data)
        assert exc.value.messages == {"value": ["Special numeric values (nan or infinity) are not permitted."]}

    def test_integer_coercion(self, impl: Serializer) -> None:
        data = b'{"value":123456789012345678901234567890}'
        result = impl.load(WithDecimalNoPlaces, data)
        assert result.value == decimal.Decimal("123456789012345678901234567890")
