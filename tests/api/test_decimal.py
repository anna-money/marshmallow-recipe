import decimal

import marshmallow
import pytest

import marshmallow_recipe as mr

from .conftest import (
    OptionalValueOf,
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
    def test_positive(self, impl: Serializer) -> None:
        obj = WithDecimal(value=decimal.Decimal("99.99"))
        result = impl.dump(WithDecimal, obj)
        assert result == b'{"value":"99.99"}'

    def test_negative(self, impl: Serializer) -> None:
        obj = WithDecimal(value=decimal.Decimal("-999.99"))
        result = impl.dump(WithDecimal, obj)
        assert result == b'{"value":"-999.99"}'

    def test_zero(self, impl: Serializer) -> None:
        obj = WithDecimal(value=decimal.Decimal("0"))
        result = impl.dump(WithDecimal, obj)
        assert result == b'{"value":"0.00"}'

    def test_very_large(self, impl: Serializer) -> None:
        obj = WithDecimal(value=decimal.Decimal("999999999999999.99"))
        result = impl.dump(WithDecimal, obj)
        assert result == b'{"value":"999999999999999.99"}'

    def test_very_small(self, impl: Serializer) -> None:
        obj = WithDecimal(value=decimal.Decimal("0.01"))
        result = impl.dump(WithDecimal, obj)
        assert result == b'{"value":"0.01"}'

    def test_places_0(self, impl: Serializer) -> None:
        obj = WithDecimal(value=decimal.Decimal("123.456"))
        result = impl.dump(WithDecimal, obj, decimal_places=0)
        assert result == b'{"value":"123"}'

    def test_places_5(self, impl: Serializer) -> None:
        obj = WithDecimal(value=decimal.Decimal("123.456"))
        result = impl.dump(WithDecimal, obj, decimal_places=5)
        assert result == b'{"value":"123.45600"}'

    def test_annotated_places(self, impl: Serializer) -> None:
        obj = WithAnnotatedDecimalPlaces(value=decimal.Decimal("123.456789"))
        result = impl.dump(WithAnnotatedDecimalPlaces, obj)
        assert result == b'{"value":"123.4568"}'

    def test_round_up(self, impl: Serializer) -> None:
        obj = WithDecimalRoundUp(value=decimal.Decimal("1.234"))
        result = impl.dump(WithDecimalRoundUp, obj)
        assert result == b'{"value":"1.24"}'

    def test_round_up_edge_case(self, impl: Serializer) -> None:
        obj = WithDecimalRoundUp(value=decimal.Decimal("1.235"))
        result = impl.dump(WithDecimalRoundUp, obj)
        assert result == b'{"value":"1.24"}'

    def test_round_up_already_rounded(self, impl: Serializer) -> None:
        obj = WithDecimalRoundUp(value=decimal.Decimal("1.20"))
        result = impl.dump(WithDecimalRoundUp, obj)
        assert result == b'{"value":"1.20"}'

    def test_round_down(self, impl: Serializer) -> None:
        obj = WithDecimalRoundDown(value=decimal.Decimal("1.239"))
        result = impl.dump(WithDecimalRoundDown, obj)
        assert result == b'{"value":"1.23"}'

    def test_round_down_edge_case(self, impl: Serializer) -> None:
        obj = WithDecimalRoundDown(value=decimal.Decimal("1.235"))
        result = impl.dump(WithDecimalRoundDown, obj)
        assert result == b'{"value":"1.23"}'

    def test_annotated_rounding(self, impl: Serializer) -> None:
        obj = WithAnnotatedDecimalRounding(value=decimal.Decimal("5.123"))
        result = impl.dump(WithAnnotatedDecimalRounding, obj)
        assert result == b'{"value":"5.13"}'

    def test_optional_none(self, impl: Serializer) -> None:
        obj = OptionalValueOf[decimal.Decimal](value=None)
        result = impl.dump(OptionalValueOf[decimal.Decimal], obj)
        assert result == b"{}"

    def test_optional_value(self, impl: Serializer) -> None:
        obj = OptionalValueOf[decimal.Decimal](value=decimal.Decimal("99.99"))
        result = impl.dump(OptionalValueOf[decimal.Decimal], obj)
        assert result == b'{"value":"99.99"}'

    def test_none_handling_ignore_default(self, impl: Serializer) -> None:
        obj = OptionalValueOf[decimal.Decimal](value=None)
        result = impl.dump(OptionalValueOf[decimal.Decimal], obj)
        assert result == b"{}"

    def test_none_handling_ignore_explicit(self, impl: Serializer) -> None:
        obj = OptionalValueOf[decimal.Decimal](value=None)
        result = impl.dump(OptionalValueOf[decimal.Decimal], obj, none_value_handling=mr.NoneValueHandling.IGNORE)
        assert result == b"{}"

    def test_none_handling_include(self, impl: Serializer) -> None:
        obj = OptionalValueOf[decimal.Decimal](value=None)
        result = impl.dump(OptionalValueOf[decimal.Decimal], obj, none_value_handling=mr.NoneValueHandling.INCLUDE)
        assert result == b'{"value":null}'

    def test_none_handling_include_with_value(self, impl: Serializer) -> None:
        obj = OptionalValueOf[decimal.Decimal](value=decimal.Decimal("99.99"))
        result = impl.dump(OptionalValueOf[decimal.Decimal], obj, none_value_handling=mr.NoneValueHandling.INCLUDE)
        assert result == b'{"value":"99.99"}'

    def test_missing(self, impl: Serializer) -> None:
        obj = WithDecimalMissing()
        result = impl.dump(WithDecimalMissing, obj)
        assert result == b"{}"

    def test_missing_with_value(self, impl: Serializer) -> None:
        obj = WithDecimalMissing(value=decimal.Decimal("99.99"))
        result = impl.dump(WithDecimalMissing, obj)
        assert result == b'{"value":"99.99"}'


class TestDecimalLoad:
    def test_positive(self, impl: Serializer) -> None:
        data = b'{"value":"99.99"}'
        result = impl.load(WithDecimal, data)
        assert result == WithDecimal(value=decimal.Decimal("99.99"))

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

    def test_validation_pass(self, impl: Serializer) -> None:
        data = b'{"value":"10.5"}'
        result = impl.load(WithDecimalValidation, data)
        assert result == WithDecimalValidation(value=decimal.Decimal("10.5"))

    def test_validation_zero_fail(self, impl: Serializer) -> None:
        data = b'{"value":"0"}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithDecimalValidation, data)
        assert exc.value.messages == {"value": ["Invalid value."]}

    def test_validation_negative_fail(self, impl: Serializer) -> None:
        data = b'{"value":"-5.5"}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithDecimalValidation, data)
        assert exc.value.messages == {"value": ["Invalid value."]}

    def test_two_validators_pass(self, impl: Serializer) -> None:
        data = b'{"value":"50.5"}'
        result = impl.load(WithDecimalTwoValidators, data)
        assert result == WithDecimalTwoValidators(value=decimal.Decimal("50.5"))

    def test_two_validators_first_fails(self, impl: Serializer) -> None:
        data = b'{"value":"0"}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithDecimalTwoValidators, data)
        assert exc.value.messages == {"value": ["Invalid value."]}

    def test_two_validators_second_fails(self, impl: Serializer) -> None:
        data = b'{"value":"1500"}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithDecimalTwoValidators, data)
        assert exc.value.messages == {"value": ["Invalid value."]}

    def test_optional_none(self, impl: Serializer) -> None:
        data = b'{"value":null}'
        result = impl.load(OptionalValueOf[decimal.Decimal], data)
        assert result == OptionalValueOf[decimal.Decimal](value=None)

    def test_optional_missing(self, impl: Serializer) -> None:
        data = b"{}"
        result = impl.load(OptionalValueOf[decimal.Decimal], data)
        assert result == OptionalValueOf[decimal.Decimal](value=None)

    def test_optional_value(self, impl: Serializer) -> None:
        data = b'{"value":"99.99"}'
        result = impl.load(OptionalValueOf[decimal.Decimal], data)
        assert result == OptionalValueOf[decimal.Decimal](value=decimal.Decimal("99.99"))

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

    def test_invalid_format(self, impl: Serializer) -> None:
        data = b'{"value":"not-a-decimal"}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithDecimal, data)
        assert exc.value.messages == {"value": ["Not a valid number."]}

    def test_wrong_type_list(self, impl: Serializer) -> None:
        data = b'{"value":[1,2]}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithDecimal, data)
        assert exc.value.messages == {"value": ["Not a valid number."]}

    def test_wrong_type_object(self, impl: Serializer) -> None:
        data = b'{"value":{"key":"1.23"}}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithDecimal, data)
        assert exc.value.messages == {"value": ["Not a valid number."]}

    def test_missing_required(self, impl: Serializer) -> None:
        data = b"{}"
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithDecimal, data)
        assert exc.value.messages == {"value": ["Missing data for required field."]}

    def test_big_from_int_larger_than_i64_max(self, impl: Serializer) -> None:
        big_value = 9223372036854775808
        data = b'{"value":9223372036854775808}'
        result = impl.load(WithDecimal, data)
        assert result == WithDecimal(value=decimal.Decimal(big_value))

    def test_big_from_int_larger_than_u64_max(self, impl: Serializer) -> None:
        huge_value = 18446744073709551616
        data = b'{"value":18446744073709551616}'
        result = impl.load(WithDecimal, data)
        assert result == WithDecimal(value=decimal.Decimal(huge_value))

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

    def test_string(self, impl: Serializer) -> None:
        obj = WithDecimal(**{"value": "123.45"})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(WithDecimal, obj)

    def test_int(self, impl: Serializer) -> None:
        obj = WithDecimal(**{"value": 123})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(WithDecimal, obj)

    def test_float(self, impl: Serializer) -> None:
        obj = WithDecimal(**{"value": 123.45})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(WithDecimal, obj)


class TestDecimalNoPlaces:
    """Tests for places=None (no automatic rounding)."""

    def test_dump_preserves_full_precision(self, impl: Serializer) -> None:
        """With places=None, full precision should be preserved."""
        obj = WithDecimalNoPlaces(value=decimal.Decimal("123.456789012345678901234567890"))
        result = impl.dump(WithDecimalNoPlaces, obj)
        assert result == b'{"value":"123.456789012345678901234567890"}'

    def test_dump_simple(self, impl: Serializer) -> None:
        obj = WithDecimalNoPlaces(value=decimal.Decimal("99.99"))
        result = impl.dump(WithDecimalNoPlaces, obj)
        assert result == b'{"value":"99.99"}'

    def test_dump_integer(self, impl: Serializer) -> None:
        obj = WithDecimalNoPlaces(value=decimal.Decimal("100"))
        result = impl.dump(WithDecimalNoPlaces, obj)
        assert result == b'{"value":"100"}'

    def test_load_preserves_full_precision(self, impl: Serializer) -> None:
        data = b'{"value":"123.456789012345678901234567890"}'
        result = impl.load(WithDecimalNoPlaces, data)
        assert result == WithDecimalNoPlaces(value=decimal.Decimal("123.456789012345678901234567890"))
