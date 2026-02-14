import dataclasses
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
    WithDecimalDefault,
    WithDecimalInvalidError,
    WithDecimalMissing,
    WithDecimalNoneError,
    WithDecimalNoPlaces,
    WithDecimalPlacesAndRange,
    WithDecimalPlacesZero,
    WithDecimalRequiredError,
    WithDecimalRoundCeiling,
    WithDecimalRoundDown,
    WithDecimalRoundFloor,
    WithDecimalRoundHalfDown,
    WithDecimalRoundHalfEven,
    WithDecimalRoundHalfUp,
    WithDecimalRoundUp,
    WithDecimalTwoValidators,
    WithDecimalValidation,
)


class TestDecimalDump:
    @pytest.mark.parametrize(
        ("obj", "expected"),
        [
            (WithDecimal(value=decimal.Decimal("123.45")), b'{"value":"123.45"}'),
            (WithDecimal(value=decimal.Decimal("99.99")), b'{"value":"99.99"}'),
            (WithDecimal(value=decimal.Decimal("-999.99")), b'{"value":"-999.99"}'),
            (WithDecimal(value=decimal.Decimal("0")), b'{"value":"0"}'),
            (WithDecimal(value=decimal.Decimal("999999999999999.99")), b'{"value":"999999999999999.99"}'),
            (WithDecimal(value=decimal.Decimal("0.01")), b'{"value":"0.01"}'),
            (WithDecimal(value=decimal.Decimal("1E+5")), b'{"value":"100000"}'),
            (WithDecimal(value=decimal.Decimal("1.100")), b'{"value":"1.100"}'),
            (WithDecimal(value=decimal.Decimal("0.00")), b'{"value":"0.00"}'),
        ],
    )
    def test_valid_values(self, impl: Serializer, obj: WithDecimal, expected: bytes) -> None:
        result = impl.dump(WithDecimal, obj)
        assert result == expected

    @pytest.mark.parametrize(
        ("obj", "expected_messages"),
        [
            pytest.param(
                WithDecimal(value=decimal.Decimal("123.456")), {"value": ["Not a valid number."]}, id="too_many_places"
            ),
            pytest.param(
                WithDecimal(value=decimal.Decimal("-1.234")),
                {"value": ["Not a valid number."]},
                id="negative_exceeds_places",
            ),
            pytest.param(
                WithDecimal(value=decimal.Decimal("1E-5")),
                {"value": ["Not a valid number."]},
                id="scientific_notation_small",
            ),
        ],
    )
    def test_invalid_places(self, impl: Serializer, obj: WithDecimal, expected_messages: dict[str, list[str]]) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.dump(WithDecimal, obj)
        assert exc.value.messages == expected_messages

    @pytest.mark.parametrize(
        ("obj", "places", "expected"),
        [
            (WithDecimal(value=decimal.Decimal("123.456")), 3, b'{"value":"123.456"}'),
            (WithDecimal(value=decimal.Decimal("123.456")), 5, b'{"value":"123.456"}'),
        ],
    )
    def test_global_places_valid(self, impl: Serializer, obj: WithDecimal, places: int, expected: bytes) -> None:
        result = impl.dump(WithDecimal, obj, decimal_places=places)
        assert result == expected

    @pytest.mark.parametrize("places", [0, 1, 2])
    def test_global_places_too_many_places(self, impl: Serializer, places: int) -> None:
        obj = WithDecimal(value=decimal.Decimal("123.456"))
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(WithDecimal, obj, decimal_places=places)

    def test_field_places_overrides_global(self, impl: Serializer) -> None:
        obj = WithAnnotatedDecimalPlaces(value=decimal.Decimal("123.4567"))
        result = impl.dump(WithAnnotatedDecimalPlaces, obj, decimal_places=1)
        assert result == b'{"value":"123.4567"}'

    def test_annotated_places(self, impl: Serializer) -> None:
        obj = WithAnnotatedDecimalPlaces(value=decimal.Decimal("123.4567"))
        result = impl.dump(WithAnnotatedDecimalPlaces, obj)
        assert result == b'{"value":"123.4567"}'

    def test_annotated_places_too_many(self, impl: Serializer) -> None:
        obj = WithAnnotatedDecimalPlaces(value=decimal.Decimal("123.45678"))
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(WithAnnotatedDecimalPlaces, obj)

    @pytest.mark.parametrize(
        ("obj", "expected"),
        [
            pytest.param(WithDecimalRoundUp(value=decimal.Decimal("1.234")), b'{"value":"1.24"}', id="round_up"),
            pytest.param(WithDecimalRoundUp(value=decimal.Decimal("1.235")), b'{"value":"1.24"}', id="round_up_edge"),
            pytest.param(
                WithDecimalRoundUp(value=decimal.Decimal("1.20")), b'{"value":"1.20"}', id="round_up_already_rounded"
            ),
            pytest.param(WithDecimalRoundDown(value=decimal.Decimal("1.239")), b'{"value":"1.23"}', id="round_down"),
            pytest.param(
                WithDecimalRoundDown(value=decimal.Decimal("1.235")), b'{"value":"1.23"}', id="round_down_edge"
            ),
            pytest.param(
                WithDecimalRoundCeiling(value=decimal.Decimal("1.231")),
                b'{"value":"1.24"}',
                id="round_ceiling_positive",
            ),
            pytest.param(
                WithDecimalRoundCeiling(value=decimal.Decimal("-1.239")),
                b'{"value":"-1.23"}',
                id="round_ceiling_negative",
            ),
            pytest.param(
                WithDecimalRoundFloor(value=decimal.Decimal("1.239")), b'{"value":"1.23"}', id="round_floor_positive"
            ),
            pytest.param(
                WithDecimalRoundFloor(value=decimal.Decimal("-1.231")), b'{"value":"-1.24"}', id="round_floor_negative"
            ),
            pytest.param(
                WithDecimalRoundHalfUp(value=decimal.Decimal("1.235")), b'{"value":"1.24"}', id="round_half_up_midpoint"
            ),
            pytest.param(
                WithDecimalRoundHalfUp(value=decimal.Decimal("1.234")),
                b'{"value":"1.23"}',
                id="round_half_up_below_midpoint",
            ),
            pytest.param(
                WithDecimalRoundHalfUp(value=decimal.Decimal("-1.235")),
                b'{"value":"-1.24"}',
                id="round_half_up_negative_midpoint",
            ),
            pytest.param(
                WithDecimalRoundHalfDown(value=decimal.Decimal("1.235")),
                b'{"value":"1.23"}',
                id="round_half_down_midpoint",
            ),
            pytest.param(
                WithDecimalRoundHalfDown(value=decimal.Decimal("1.236")),
                b'{"value":"1.24"}',
                id="round_half_down_above_midpoint",
            ),
            pytest.param(
                WithDecimalRoundHalfDown(value=decimal.Decimal("-1.235")),
                b'{"value":"-1.23"}',
                id="round_half_down_negative_midpoint",
            ),
            pytest.param(
                WithDecimalRoundHalfEven(value=decimal.Decimal("1.235")),
                b'{"value":"1.24"}',
                id="round_half_even_to_even_up",
            ),
            pytest.param(
                WithDecimalRoundHalfEven(value=decimal.Decimal("1.225")),
                b'{"value":"1.22"}',
                id="round_half_even_to_even_down",
            ),
            pytest.param(
                WithDecimalRoundHalfEven(value=decimal.Decimal("1.245")), b'{"value":"1.24"}', id="round_half_even_245"
            ),
            pytest.param(
                WithAnnotatedDecimalRounding(value=decimal.Decimal("5.123")),
                b'{"value":"5.13"}',
                id="annotated_rounding",
            ),
        ],
    )
    def test_rounding_modes(self, impl: Serializer, obj: object, expected: bytes) -> None:
        result = impl.dump(type(obj), obj)
        assert result == expected

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

    @pytest.mark.parametrize(
        ("obj", "expected"),
        [
            (WithDecimalPlacesZero(value=decimal.Decimal("100")), b'{"value":"100"}'),
            (WithDecimalPlacesZero(value=decimal.Decimal("-50")), b'{"value":"-50"}'),
        ],
    )
    def test_places_zero_valid(self, impl: Serializer, obj: WithDecimalPlacesZero, expected: bytes) -> None:
        result = impl.dump(WithDecimalPlacesZero, obj)
        assert result == expected

    @pytest.mark.parametrize(
        "obj",
        [
            pytest.param(WithDecimalPlacesZero(value=decimal.Decimal("1.5")), id="decimal"),
            pytest.param(WithDecimalPlacesZero(value=decimal.Decimal("0.1")), id="small_decimal"),
        ],
    )
    def test_places_zero_invalid(self, impl: Serializer, obj: WithDecimalPlacesZero) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.dump(WithDecimalPlacesZero, obj)
        assert exc.value.messages == {"value": ["Not a valid number."]}

    def test_places_with_range_both_pass(self, impl: Serializer) -> None:
        obj = WithDecimalPlacesAndRange(value=decimal.Decimal("50.12"))
        result = impl.dump(WithDecimalPlacesAndRange, obj)
        assert result == b'{"value":"50.12"}'

    def test_places_with_range_places_fails(self, impl: Serializer) -> None:
        obj = WithDecimalPlacesAndRange(value=decimal.Decimal("50.123"))
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.dump(WithDecimalPlacesAndRange, obj)
        assert exc.value.messages == {"value": ["Not a valid number."]}

    def test_places_with_range_range_fails(self, impl: Serializer) -> None:
        obj = WithDecimalPlacesAndRange(value=decimal.Decimal("150.12"))
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.dump(WithDecimalPlacesAndRange, obj)
        assert exc.value.messages == {"value": ["Invalid value."]}

    @pytest.mark.parametrize(
        "obj",
        [
            pytest.param(WithDecimal(**{"value": "123.45"}), id="string"),  # type: ignore[arg-type]
            pytest.param(WithDecimal(**{"value": 123}), id="int"),  # type: ignore[arg-type]
            pytest.param(WithDecimal(**{"value": 123.45}), id="float"),  # type: ignore[arg-type]
        ],
    )
    def test_invalid_type(self, impl: Serializer, obj: WithDecimal) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.dump(WithDecimal, obj)
        if impl.supports_proper_validation_errors_on_dump:
            assert exc.value.messages == {"value": ["Not a valid number."]}

    def test_custom_invalid_error(self, impl: Serializer) -> None:
        obj = WithDecimalInvalidError(**{"value": "123.45"})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.dump(WithDecimalInvalidError, obj)
        if impl.supports_proper_validation_errors_on_dump:
            assert exc.value.messages == {"value": ["Custom invalid message"]}

    def test_default_provided(self, impl: Serializer) -> None:
        obj = WithDecimalDefault(value=decimal.Decimal("50.00"))
        result = impl.dump(WithDecimalDefault, obj)
        assert result == b'{"value":"50.00"}'

    @pytest.mark.parametrize(
        ("obj", "expected_message"),
        [
            pytest.param(
                WithDecimalNoPlaces(value=decimal.Decimal("NaN")), {"value": ["Not a valid number."]}, id="nan"
            ),
            pytest.param(
                WithDecimalNoPlaces(value=decimal.Decimal("Infinity")), {"value": ["Not a valid number."]}, id="inf"
            ),
            pytest.param(
                WithDecimalNoPlaces(value=decimal.Decimal("-Infinity")),
                {"value": ["Not a valid number."]},
                id="negative_inf",
            ),
            pytest.param(
                WithDecimalNoPlaces(value=decimal.Decimal("sNaN")), {"value": ["Not a valid number."]}, id="snan"
            ),
        ],
    )
    def test_special_values_fail(
        self, impl: Serializer, obj: WithDecimalNoPlaces, expected_message: dict[str, list[str]]
    ) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.dump(WithDecimalNoPlaces, obj)
        assert exc.value.messages == expected_message

    @pytest.mark.parametrize(
        ("meta", "value", "expected"),
        [
            pytest.param(mr.decimal_meta(gt=0), decimal.Decimal("1"), b'{"value":"1"}', id="gt_int"),
            pytest.param(
                mr.decimal_meta(gt=decimal.Decimal("0")), decimal.Decimal("1"), b'{"value":"1"}', id="gt_decimal"
            ),
            pytest.param(mr.decimal_meta(gte=0), decimal.Decimal("0"), b'{"value":"0"}', id="gte_int"),
            pytest.param(
                mr.decimal_meta(gte=decimal.Decimal("0")), decimal.Decimal("0"), b'{"value":"0"}', id="gte_decimal"
            ),
            pytest.param(mr.decimal_meta(lt=100), decimal.Decimal("99"), b'{"value":"99"}', id="lt_int"),
            pytest.param(
                mr.decimal_meta(lt=decimal.Decimal("100")), decimal.Decimal("99"), b'{"value":"99"}', id="lt_decimal"
            ),
            pytest.param(mr.decimal_meta(lte=100), decimal.Decimal("100"), b'{"value":"100"}', id="lte_int"),
            pytest.param(
                mr.decimal_meta(lte=decimal.Decimal("100")),
                decimal.Decimal("100"),
                b'{"value":"100"}',
                id="lte_decimal",
            ),
            pytest.param(mr.decimal_meta(gte=0, lte=100), decimal.Decimal("50"), b'{"value":"50"}', id="range_int"),
            pytest.param(
                mr.decimal_meta(gte=decimal.Decimal("0"), lte=decimal.Decimal("100")),
                decimal.Decimal("50"),
                b'{"value":"50"}',
                id="range_decimal",
            ),
        ],
    )
    def test_range_pass(
        self, impl: Serializer, meta: dict[str, object], value: decimal.Decimal, expected: bytes
    ) -> None:
        @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
        class DC:
            value: decimal.Decimal = dataclasses.field(metadata=meta)

        result = impl.dump(DC, DC(value=value))
        assert result == expected

    @pytest.mark.parametrize(
        ("meta", "value", "expected_messages"),
        [
            pytest.param(
                mr.decimal_meta(gt=0), decimal.Decimal("0"), {"value": ["Must be greater than 0."]}, id="gt_int_equal"
            ),
            pytest.param(
                mr.decimal_meta(gt=0), decimal.Decimal("-1"), {"value": ["Must be greater than 0."]}, id="gt_int_less"
            ),
            pytest.param(
                mr.decimal_meta(gt=decimal.Decimal("0")),
                decimal.Decimal("0"),
                {"value": ["Must be greater than 0."]},
                id="gt_decimal_equal",
            ),
            pytest.param(
                mr.decimal_meta(gte=0),
                decimal.Decimal("-1"),
                {"value": ["Must be greater than or equal to 0."]},
                id="gte_int",
            ),
            pytest.param(
                mr.decimal_meta(gte=decimal.Decimal("0")),
                decimal.Decimal("-1"),
                {"value": ["Must be greater than or equal to 0."]},
                id="gte_decimal",
            ),
            pytest.param(
                mr.decimal_meta(lt=100),
                decimal.Decimal("100"),
                {"value": ["Must be less than 100."]},
                id="lt_int_equal",
            ),
            pytest.param(
                mr.decimal_meta(lt=100),
                decimal.Decimal("101"),
                {"value": ["Must be less than 100."]},
                id="lt_int_greater",
            ),
            pytest.param(
                mr.decimal_meta(lt=decimal.Decimal("100")),
                decimal.Decimal("100"),
                {"value": ["Must be less than 100."]},
                id="lt_decimal_equal",
            ),
            pytest.param(
                mr.decimal_meta(lte=100),
                decimal.Decimal("101"),
                {"value": ["Must be less than or equal to 100."]},
                id="lte_int",
            ),
            pytest.param(
                mr.decimal_meta(lte=decimal.Decimal("100")),
                decimal.Decimal("101"),
                {"value": ["Must be less than or equal to 100."]},
                id="lte_decimal",
            ),
            pytest.param(
                mr.decimal_meta(gte=0, lte=100),
                decimal.Decimal("-1"),
                {"value": ["Must be greater than or equal to 0."]},
                id="range_below",
            ),
            pytest.param(
                mr.decimal_meta(gte=0, lte=100),
                decimal.Decimal("101"),
                {"value": ["Must be less than or equal to 100."]},
                id="range_above",
            ),
        ],
    )
    def test_range_fail(
        self, impl: Serializer, meta: dict[str, object], value: decimal.Decimal, expected_messages: dict[str, list[str]]
    ) -> None:
        @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
        class DC:
            value: decimal.Decimal = dataclasses.field(metadata=meta)

        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.dump(DC, DC(value=value))
        assert exc.value.messages == expected_messages

    @pytest.mark.parametrize(
        ("meta", "value", "expected_messages"),
        [
            pytest.param(
                mr.decimal_meta(gt=0, gt_error="Custom gt error"),
                decimal.Decimal("0"),
                {"value": ["Custom gt error"]},
                id="gt",
            ),
            pytest.param(
                mr.decimal_meta(gte=0, gte_error="Custom gte error"),
                decimal.Decimal("-1"),
                {"value": ["Custom gte error"]},
                id="gte",
            ),
            pytest.param(
                mr.decimal_meta(lt=100, lt_error="Custom lt error"),
                decimal.Decimal("100"),
                {"value": ["Custom lt error"]},
                id="lt",
            ),
            pytest.param(
                mr.decimal_meta(lte=100, lte_error="Custom lte error"),
                decimal.Decimal("101"),
                {"value": ["Custom lte error"]},
                id="lte",
            ),
        ],
    )
    def test_range_custom_error(
        self, impl: Serializer, meta: dict[str, object], value: decimal.Decimal, expected_messages: dict[str, list[str]]
    ) -> None:
        @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
        class DC:
            value: decimal.Decimal = dataclasses.field(metadata=meta)

        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.dump(DC, DC(value=value))
        assert exc.value.messages == expected_messages

    @pytest.mark.parametrize(
        ("value", "expected"), [pytest.param(decimal.Decimal("50.12"), b'{"value":"50.12"}', id="pass")]
    )
    def test_range_and_places_pass(self, impl: Serializer, value: decimal.Decimal, expected: bytes) -> None:
        @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
        class DC:
            value: decimal.Decimal = dataclasses.field(metadata=mr.decimal_meta(gte=0, lte=100, places=2))

        result = impl.dump(DC, DC(value=value))
        assert result == expected

    @pytest.mark.parametrize(
        ("value", "expected_messages"),
        [
            pytest.param(decimal.Decimal("50.123"), {"value": ["Not a valid number."]}, id="places_fail"),
            pytest.param(decimal.Decimal("150.12"), {"value": ["Must be less than or equal to 100."]}, id="range_fail"),
        ],
    )
    def test_range_and_places_fail(
        self, impl: Serializer, value: decimal.Decimal, expected_messages: dict[str, list[str]]
    ) -> None:
        @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
        class DC:
            value: decimal.Decimal = dataclasses.field(metadata=mr.decimal_meta(gte=0, lte=100, places=2))

        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.dump(DC, DC(value=value))
        assert exc.value.messages == expected_messages


class TestDecimalLoad:
    @pytest.mark.parametrize(
        ("data", "expected"),
        [
            (b'{"value":"123.45"}', WithDecimal(value=decimal.Decimal("123.45"))),
            (b'{"value":"99.99"}', WithDecimal(value=decimal.Decimal("99.99"))),
            (b'{"value":"1E+5"}', WithDecimal(value=decimal.Decimal("1E+5"))),
            (b'{"value":"1.100"}', WithDecimal(value=decimal.Decimal("1.100"))),
            (b'{"value":"0.00"}', WithDecimal(value=decimal.Decimal("0.00"))),
            pytest.param(b'{"value":100}', WithDecimal(value=decimal.Decimal("100")), id="int"),
            pytest.param(b'{"value":-50}', WithDecimal(value=decimal.Decimal("-50")), id="negative_int"),
            pytest.param(b'{"value":99.99}', WithDecimal(value=decimal.Decimal("99.99")), id="float"),
            pytest.param(b'{"value":-0.01}', WithDecimal(value=decimal.Decimal("-0.01")), id="negative_float"),
        ],
    )
    def test_valid_values(self, impl: Serializer, data: bytes, expected: WithDecimal) -> None:
        result = impl.load(WithDecimal, data)
        assert result == expected

    @pytest.mark.parametrize(
        ("data", "expected_messages"),
        [
            pytest.param(b'{"value":"123.456"}', {"value": ["Not a valid number."]}, id="too_many_places"),
            pytest.param(b'{"value":"-1.234"}', {"value": ["Not a valid number."]}, id="negative_exceeds_places"),
            pytest.param(b'{"value":"1E-5"}', {"value": ["Not a valid number."]}, id="scientific_notation_small"),
            pytest.param(b'{"value":123.456}', {"value": ["Not a valid number."]}, id="float_too_many_places"),
        ],
    )
    def test_invalid_places(self, impl: Serializer, data: bytes, expected_messages: dict[str, list[str]]) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithDecimal, data)
        assert exc.value.messages == expected_messages

    def test_annotated_places(self, impl: Serializer) -> None:
        data = b'{"value":"99.1234"}'
        result = impl.load(WithAnnotatedDecimalPlaces, data)
        assert result == WithAnnotatedDecimalPlaces(value=decimal.Decimal("99.1234"))

    def test_annotated_places_too_many(self, impl: Serializer) -> None:
        data = b'{"value":"99.12345"}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithAnnotatedDecimalPlaces, data)
        assert exc.value.messages == {"value": ["Not a valid number."]}

    @pytest.mark.parametrize(
        ("data", "expected"),
        [
            pytest.param(b'{"value":"9.876"}', WithDecimalRoundUp(value=decimal.Decimal("9.88")), id="round_up"),
            pytest.param(b'{"value":"7.654"}', WithDecimalRoundDown(value=decimal.Decimal("7.65")), id="round_down"),
            pytest.param(
                b'{"value":"7.654"}',
                WithAnnotatedDecimalRounding(value=decimal.Decimal("7.66")),
                id="annotated_rounding",
            ),
            pytest.param(
                b'{"value":"1.231"}',
                WithDecimalRoundCeiling(value=decimal.Decimal("1.24")),
                id="round_ceiling_positive",
            ),
            pytest.param(
                b'{"value":"-1.239"}',
                WithDecimalRoundCeiling(value=decimal.Decimal("-1.23")),
                id="round_ceiling_negative",
            ),
            pytest.param(
                b'{"value":"1.239"}', WithDecimalRoundFloor(value=decimal.Decimal("1.23")), id="round_floor_positive"
            ),
            pytest.param(
                b'{"value":"-1.231"}', WithDecimalRoundFloor(value=decimal.Decimal("-1.24")), id="round_floor_negative"
            ),
            pytest.param(
                b'{"value":"1.235"}', WithDecimalRoundHalfUp(value=decimal.Decimal("1.24")), id="round_half_up_midpoint"
            ),
            pytest.param(
                b'{"value":"1.234"}',
                WithDecimalRoundHalfUp(value=decimal.Decimal("1.23")),
                id="round_half_up_below_midpoint",
            ),
            pytest.param(
                b'{"value":"-1.235"}',
                WithDecimalRoundHalfUp(value=decimal.Decimal("-1.24")),
                id="round_half_up_negative_midpoint",
            ),
            pytest.param(
                b'{"value":"1.235"}',
                WithDecimalRoundHalfDown(value=decimal.Decimal("1.23")),
                id="round_half_down_midpoint",
            ),
            pytest.param(
                b'{"value":"1.236"}',
                WithDecimalRoundHalfDown(value=decimal.Decimal("1.24")),
                id="round_half_down_above_midpoint",
            ),
            pytest.param(
                b'{"value":"-1.235"}',
                WithDecimalRoundHalfDown(value=decimal.Decimal("-1.23")),
                id="round_half_down_negative_midpoint",
            ),
            pytest.param(
                b'{"value":"1.235"}',
                WithDecimalRoundHalfEven(value=decimal.Decimal("1.24")),
                id="round_half_even_to_even_up",
            ),
            pytest.param(
                b'{"value":"1.225"}',
                WithDecimalRoundHalfEven(value=decimal.Decimal("1.22")),
                id="round_half_even_to_even_down",
            ),
            pytest.param(
                b'{"value":"1.245"}', WithDecimalRoundHalfEven(value=decimal.Decimal("1.24")), id="round_half_even_245"
            ),
            pytest.param(b'{"value":9.876}', WithDecimalRoundUp(value=decimal.Decimal("9.88")), id="float_round_up"),
            pytest.param(
                b'{"value":7.654}', WithDecimalRoundDown(value=decimal.Decimal("7.65")), id="float_round_down"
            ),
            pytest.param(
                b'{"value":10}', WithDecimalRoundHalfUp(value=decimal.Decimal("10.00")), id="int_round_half_up"
            ),
        ],
    )
    def test_rounding_modes(self, impl: Serializer, data: bytes, expected: object) -> None:
        result = impl.load(type(expected), data)
        assert result == expected

    @pytest.mark.parametrize(
        ("places", "expected"),
        [(3, WithDecimal(value=decimal.Decimal("123.456"))), (5, WithDecimal(value=decimal.Decimal("123.456")))],
    )
    def test_global_places_valid(self, impl: Serializer, places: int, expected: WithDecimal) -> None:
        data = b'{"value":"123.456"}'
        result = impl.load(WithDecimal, data, decimal_places=places)
        assert result == expected

    @pytest.mark.parametrize("places", [0, 1, 2])
    def test_global_places_too_many(self, impl: Serializer, places: int) -> None:
        data = b'{"value":"123.456"}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithDecimal, data, decimal_places=places)
        assert exc.value.messages == {"value": ["Not a valid number."]}

    def test_field_places_overrides_global(self, impl: Serializer) -> None:
        data = b'{"value":"123.4567"}'
        result = impl.load(WithAnnotatedDecimalPlaces, data, decimal_places=1)
        assert result == WithAnnotatedDecimalPlaces(value=decimal.Decimal("123.4567"))

    def test_validation_pass(self, impl: Serializer) -> None:
        data = b'{"value":"10.5"}'
        result = impl.load(WithDecimalValidation, data)
        assert result == WithDecimalValidation(value=decimal.Decimal("10.5"))

    @pytest.mark.parametrize(
        "data", [pytest.param(b'{"value":"0"}', id="zero"), pytest.param(b'{"value":"-5.5"}', id="negative")]
    )
    def test_validation_fail(self, impl: Serializer, data: bytes) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithDecimalValidation, data)
        assert exc.value.messages == {"value": ["Invalid value."]}

    def test_two_validators_pass(self, impl: Serializer) -> None:
        data = b'{"value":"50.5"}'
        result = impl.load(WithDecimalTwoValidators, data)
        assert result == WithDecimalTwoValidators(value=decimal.Decimal("50.5"))

    @pytest.mark.parametrize(
        "data", [pytest.param(b'{"value":"0"}', id="first_fails"), pytest.param(b'{"value":"1500"}', id="second_fails")]
    )
    def test_two_validators_fail(self, impl: Serializer, data: bytes) -> None:
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

    @pytest.mark.parametrize(
        "data",
        [
            pytest.param(b'{"value":"not-a-decimal"}', id="invalid_string"),
            pytest.param(b'{"value":"NaN"}', id="nan"),
            pytest.param(b'{"value":"Infinity"}', id="infinity"),
            pytest.param(b'{"value":"-Infinity"}', id="negative_infinity"),
        ],
    )
    def test_custom_invalid_error(self, impl: Serializer, data: bytes) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithDecimalInvalidError, data)
        assert exc.value.messages == {"value": ["Custom invalid message"]}

    @pytest.mark.parametrize(
        "data",
        [
            pytest.param(b'{"value":"not-a-decimal"}', id="invalid_format"),
            pytest.param(b'{"value":[1,2]}', id="wrong_type_list"),
            pytest.param(b'{"value":{"key":"1.23"}}', id="wrong_type_object"),
            pytest.param(b'{"value":true}', id="bool_true"),
            pytest.param(b'{"value":false}', id="bool_false"),
        ],
    )
    def test_invalid_format(self, impl: Serializer, data: bytes) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithDecimal, data)
        assert exc.value.messages == {"value": ["Not a valid number."]}

    def test_missing_required(self, impl: Serializer) -> None:
        data = b"{}"
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithDecimal, data)
        assert exc.value.messages == {"value": ["Missing data for required field."]}

    @pytest.mark.parametrize(
        ("data", "expected"),
        [
            pytest.param(
                b'{"value":9223372036854775808}',
                WithDecimal(value=decimal.Decimal("9223372036854775808")),
                id="larger_than_i64_max",
            ),
            pytest.param(
                b'{"value":18446744073709551616}',
                WithDecimal(value=decimal.Decimal("18446744073709551616")),
                id="larger_than_u64_max",
            ),
        ],
    )
    def test_big_integers(self, impl: Serializer, data: bytes, expected: WithDecimal) -> None:
        result = impl.load(WithDecimal, data)
        assert result == expected

    def test_missing(self, impl: Serializer) -> None:
        data = b"{}"
        result = impl.load(WithDecimalMissing, data)
        assert result == WithDecimalMissing()

    def test_missing_with_value(self, impl: Serializer) -> None:
        data = b'{"value":"99.99"}'
        result = impl.load(WithDecimalMissing, data)
        assert result == WithDecimalMissing(value=decimal.Decimal("99.99"))

    def test_default_omitted(self, impl: Serializer) -> None:
        data = b"{}"
        result = impl.load(WithDecimalDefault, data)
        assert result == WithDecimalDefault(value=decimal.Decimal("99.99"))

    def test_default_provided(self, impl: Serializer) -> None:
        data = b'{"value":"50.00"}'
        result = impl.load(WithDecimalDefault, data)
        assert result == WithDecimalDefault(value=decimal.Decimal("50.00"))

    @pytest.mark.parametrize(
        ("data", "expected_message"),
        [
            pytest.param(b'{"value":"NaN"}', {"value": ["Not a valid number."]}, id="nan"),
            pytest.param(b'{"value":"Infinity"}', {"value": ["Not a valid number."]}, id="inf"),
            pytest.param(b'{"value":"-Infinity"}', {"value": ["Not a valid number."]}, id="negative_inf"),
            pytest.param(b'{"value":"sNaN"}', {"value": ["Not a valid number."]}, id="snan"),
        ],
    )
    def test_from_string_special_values_fail(
        self, impl: Serializer, data: bytes, expected_message: dict[str, list[str]]
    ) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithDecimalNoPlaces, data)
        assert exc.value.messages == expected_message

    @pytest.mark.parametrize(
        ("data", "expected"),
        [
            (b'{"value":"100"}', WithDecimalPlacesZero(value=decimal.Decimal("100"))),
            (b'{"value":"-50"}', WithDecimalPlacesZero(value=decimal.Decimal("-50"))),
            pytest.param(b'{"value":100}', WithDecimalPlacesZero(value=decimal.Decimal("100")), id="int"),
        ],
    )
    def test_places_zero_valid(self, impl: Serializer, data: bytes, expected: WithDecimalPlacesZero) -> None:
        result = impl.load(WithDecimalPlacesZero, data)
        assert result == expected

    @pytest.mark.parametrize(
        "data",
        [
            pytest.param(b'{"value":"1.5"}', id="decimal"),
            pytest.param(b'{"value":"0.1"}', id="small_decimal"),
            pytest.param(b'{"value":1.5}', id="float_decimal"),
        ],
    )
    def test_places_zero_invalid(self, impl: Serializer, data: bytes) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithDecimalPlacesZero, data)
        assert exc.value.messages == {"value": ["Not a valid number."]}

    def test_places_with_range_both_pass(self, impl: Serializer) -> None:
        data = b'{"value":"50.12"}'
        result = impl.load(WithDecimalPlacesAndRange, data)
        assert result == WithDecimalPlacesAndRange(value=decimal.Decimal("50.12"))

    def test_places_with_range_places_fails(self, impl: Serializer) -> None:
        data = b'{"value":"50.123"}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithDecimalPlacesAndRange, data)
        assert exc.value.messages == {"value": ["Not a valid number."]}

    def test_places_with_range_range_fails(self, impl: Serializer) -> None:
        data = b'{"value":"150.12"}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithDecimalPlacesAndRange, data)
        assert exc.value.messages == {"value": ["Invalid value."]}

    @pytest.mark.parametrize(
        ("meta", "data", "expected_value"),
        [
            pytest.param(mr.decimal_meta(gt=0), b'{"value":"1"}', decimal.Decimal("1"), id="gt_int"),
            pytest.param(
                mr.decimal_meta(gt=decimal.Decimal("0")), b'{"value":"1"}', decimal.Decimal("1"), id="gt_decimal"
            ),
            pytest.param(mr.decimal_meta(gte=0), b'{"value":"0"}', decimal.Decimal("0"), id="gte_int_equal"),
            pytest.param(mr.decimal_meta(gte=0), b'{"value":"1"}', decimal.Decimal("1"), id="gte_int_above"),
            pytest.param(
                mr.decimal_meta(gte=decimal.Decimal("0")),
                b'{"value":"0"}',
                decimal.Decimal("0"),
                id="gte_decimal_equal",
            ),
            pytest.param(mr.decimal_meta(lt=100), b'{"value":"99"}', decimal.Decimal("99"), id="lt_int"),
            pytest.param(
                mr.decimal_meta(lt=decimal.Decimal("100")), b'{"value":"99"}', decimal.Decimal("99"), id="lt_decimal"
            ),
            pytest.param(mr.decimal_meta(lte=100), b'{"value":"100"}', decimal.Decimal("100"), id="lte_int_equal"),
            pytest.param(mr.decimal_meta(lte=100), b'{"value":"99"}', decimal.Decimal("99"), id="lte_int_below"),
            pytest.param(
                mr.decimal_meta(lte=decimal.Decimal("100")),
                b'{"value":"100"}',
                decimal.Decimal("100"),
                id="lte_decimal_equal",
            ),
            pytest.param(mr.decimal_meta(gte=0, lte=100), b'{"value":"50"}', decimal.Decimal("50"), id="range_int_mid"),
            pytest.param(mr.decimal_meta(gte=0, lte=100), b'{"value":"0"}', decimal.Decimal("0"), id="range_int_low"),
            pytest.param(
                mr.decimal_meta(gte=0, lte=100), b'{"value":"100"}', decimal.Decimal("100"), id="range_int_high"
            ),
            pytest.param(
                mr.decimal_meta(gte=decimal.Decimal("0"), lte=decimal.Decimal("100")),
                b'{"value":"50"}',
                decimal.Decimal("50"),
                id="range_decimal",
            ),
        ],
    )
    def test_range_pass(
        self, impl: Serializer, meta: dict[str, object], data: bytes, expected_value: decimal.Decimal
    ) -> None:
        @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
        class DC:
            value: decimal.Decimal = dataclasses.field(metadata=meta)

        result = impl.load(DC, data)
        assert result == DC(value=expected_value)

    @pytest.mark.parametrize(
        ("meta", "data", "expected_messages"),
        [
            pytest.param(
                mr.decimal_meta(gt=0), b'{"value":"0"}', {"value": ["Must be greater than 0."]}, id="gt_int_equal"
            ),
            pytest.param(
                mr.decimal_meta(gt=0), b'{"value":"-1"}', {"value": ["Must be greater than 0."]}, id="gt_int_less"
            ),
            pytest.param(
                mr.decimal_meta(gt=decimal.Decimal("0")),
                b'{"value":"0"}',
                {"value": ["Must be greater than 0."]},
                id="gt_decimal_equal",
            ),
            pytest.param(
                mr.decimal_meta(gte=0),
                b'{"value":"-1"}',
                {"value": ["Must be greater than or equal to 0."]},
                id="gte_int",
            ),
            pytest.param(
                mr.decimal_meta(gte=decimal.Decimal("0")),
                b'{"value":"-1"}',
                {"value": ["Must be greater than or equal to 0."]},
                id="gte_decimal",
            ),
            pytest.param(
                mr.decimal_meta(lt=100), b'{"value":"100"}', {"value": ["Must be less than 100."]}, id="lt_int_equal"
            ),
            pytest.param(
                mr.decimal_meta(lt=100), b'{"value":"101"}', {"value": ["Must be less than 100."]}, id="lt_int_greater"
            ),
            pytest.param(
                mr.decimal_meta(lt=decimal.Decimal("100")),
                b'{"value":"100"}',
                {"value": ["Must be less than 100."]},
                id="lt_decimal_equal",
            ),
            pytest.param(
                mr.decimal_meta(lte=100),
                b'{"value":"101"}',
                {"value": ["Must be less than or equal to 100."]},
                id="lte_int",
            ),
            pytest.param(
                mr.decimal_meta(lte=decimal.Decimal("100")),
                b'{"value":"101"}',
                {"value": ["Must be less than or equal to 100."]},
                id="lte_decimal",
            ),
            pytest.param(
                mr.decimal_meta(gte=0, lte=100),
                b'{"value":"-1"}',
                {"value": ["Must be greater than or equal to 0."]},
                id="range_below",
            ),
            pytest.param(
                mr.decimal_meta(gte=0, lte=100),
                b'{"value":"101"}',
                {"value": ["Must be less than or equal to 100."]},
                id="range_above",
            ),
        ],
    )
    def test_range_fail(
        self, impl: Serializer, meta: dict[str, object], data: bytes, expected_messages: dict[str, list[str]]
    ) -> None:
        @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
        class DC:
            value: decimal.Decimal = dataclasses.field(metadata=meta)

        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(DC, data)
        assert exc.value.messages == expected_messages

    @pytest.mark.parametrize(
        ("meta", "data", "expected_messages"),
        [
            pytest.param(
                mr.decimal_meta(gt=0, gt_error="Custom gt error"),
                b'{"value":"0"}',
                {"value": ["Custom gt error"]},
                id="gt",
            ),
            pytest.param(
                mr.decimal_meta(gte=0, gte_error="Custom gte error"),
                b'{"value":"-1"}',
                {"value": ["Custom gte error"]},
                id="gte",
            ),
            pytest.param(
                mr.decimal_meta(lt=100, lt_error="Custom lt error"),
                b'{"value":"100"}',
                {"value": ["Custom lt error"]},
                id="lt",
            ),
            pytest.param(
                mr.decimal_meta(lte=100, lte_error="Custom lte error"),
                b'{"value":"101"}',
                {"value": ["Custom lte error"]},
                id="lte",
            ),
        ],
    )
    def test_range_custom_error(
        self, impl: Serializer, meta: dict[str, object], data: bytes, expected_messages: dict[str, list[str]]
    ) -> None:
        @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
        class DC:
            value: decimal.Decimal = dataclasses.field(metadata=meta)

        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(DC, data)
        assert exc.value.messages == expected_messages

    @pytest.mark.parametrize(
        ("data", "expected_value"), [pytest.param(b'{"value":"50.12"}', decimal.Decimal("50.12"), id="pass")]
    )
    def test_range_and_places_pass(self, impl: Serializer, data: bytes, expected_value: decimal.Decimal) -> None:
        @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
        class DC:
            value: decimal.Decimal = dataclasses.field(metadata=mr.decimal_meta(gte=0, lte=100, places=2))

        result = impl.load(DC, data)
        assert result == DC(value=expected_value)

    @pytest.mark.parametrize(
        ("data", "expected_messages"),
        [
            pytest.param(b'{"value":"50.123"}', {"value": ["Not a valid number."]}, id="places_fail"),
            pytest.param(b'{"value":"150.12"}', {"value": ["Must be less than or equal to 100."]}, id="range_fail"),
        ],
    )
    def test_range_and_places_fail(
        self, impl: Serializer, data: bytes, expected_messages: dict[str, list[str]]
    ) -> None:
        @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
        class DC:
            value: decimal.Decimal = dataclasses.field(metadata=mr.decimal_meta(gte=0, lte=100, places=2))

        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(DC, data)
        assert exc.value.messages == expected_messages


class TestDecimalNoPlaces:
    @pytest.mark.parametrize(
        ("obj", "expected"),
        [
            (
                WithDecimalNoPlaces(value=decimal.Decimal("123.456789012345678901234567890")),
                b'{"value":"123.456789012345678901234567890"}',
            ),
            (WithDecimalNoPlaces(value=decimal.Decimal("99.99")), b'{"value":"99.99"}'),
            (WithDecimalNoPlaces(value=decimal.Decimal("100")), b'{"value":"100"}'),
        ],
    )
    def test_dump(self, impl: Serializer, obj: WithDecimalNoPlaces, expected: bytes) -> None:
        result = impl.dump(WithDecimalNoPlaces, obj)
        assert result == expected

    def test_dump_overrides_global_places(self, impl: Serializer) -> None:
        obj = WithDecimalNoPlaces(value=decimal.Decimal("123.456789"))
        result = impl.dump(WithDecimalNoPlaces, obj, decimal_places=2)
        assert result == b'{"value":"123.456789"}'

    @pytest.mark.parametrize(
        ("data", "expected"),
        [
            (
                b'{"value":"123.456789012345678901234567890"}',
                WithDecimalNoPlaces(value=decimal.Decimal("123.456789012345678901234567890")),
            ),
            pytest.param(b'{"value":42}', WithDecimalNoPlaces(value=decimal.Decimal("42")), id="int"),
            pytest.param(b'{"value":3.14}', WithDecimalNoPlaces(value=decimal.Decimal("3.14")), id="float"),
        ],
    )
    def test_load(self, impl: Serializer, data: bytes, expected: WithDecimalNoPlaces) -> None:
        result = impl.load(WithDecimalNoPlaces, data)
        assert result == expected

    def test_load_overrides_global_places(self, impl: Serializer) -> None:
        data = b'{"value":"123.456789"}'
        result = impl.load(WithDecimalNoPlaces, data, decimal_places=2)
        assert result == WithDecimalNoPlaces(value=decimal.Decimal("123.456789"))

    @pytest.mark.parametrize(
        ("obj", "expected"),
        [
            (
                WithDecimalNoPlaces(value=decimal.Decimal("79228162514264337593543950335")),
                b'{"value":"79228162514264337593543950335"}',
            ),
            (
                WithDecimalNoPlaces(value=decimal.Decimal("-79228162514264337593543950335")),
                b'{"value":"-79228162514264337593543950335"}',
            ),
            (
                WithDecimalNoPlaces(value=decimal.Decimal("0.0000000000000000000000000001")),
                b'{"value":"0.0000000000000000000000000001"}',
            ),
            (
                WithDecimalNoPlaces(value=decimal.Decimal("-0.0000000000000000000000000001")),
                b'{"value":"-0.0000000000000000000000000001"}',
            ),
            (
                WithDecimalNoPlaces(value=decimal.Decimal("7.9228162514264337593543950335")),
                b'{"value":"7.9228162514264337593543950335"}',
            ),
            (
                WithDecimalNoPlaces(value=decimal.Decimal("-7.9228162514264337593543950335")),
                b'{"value":"-7.9228162514264337593543950335"}',
            ),
        ],
    )
    def test_dump_boundary_values(self, impl: Serializer, obj: WithDecimalNoPlaces, expected: bytes) -> None:
        result = impl.dump(WithDecimalNoPlaces, obj)
        assert result == expected

    @pytest.mark.parametrize(
        ("data", "expected"),
        [
            (
                b'{"value":"79228162514264337593543950335"}',
                WithDecimalNoPlaces(value=decimal.Decimal("79228162514264337593543950335")),
            ),
            (
                b'{"value":"-79228162514264337593543950335"}',
                WithDecimalNoPlaces(value=decimal.Decimal("-79228162514264337593543950335")),
            ),
            (
                b'{"value":"0.0000000000000000000000000001"}',
                WithDecimalNoPlaces(value=decimal.Decimal("0.0000000000000000000000000001")),
            ),
            (
                b'{"value":"-0.0000000000000000000000000001"}',
                WithDecimalNoPlaces(value=decimal.Decimal("-0.0000000000000000000000000001")),
            ),
            (
                b'{"value":"7.9228162514264337593543950335"}',
                WithDecimalNoPlaces(value=decimal.Decimal("7.9228162514264337593543950335")),
            ),
            (
                b'{"value":"-7.9228162514264337593543950335"}',
                WithDecimalNoPlaces(value=decimal.Decimal("-7.9228162514264337593543950335")),
            ),
            pytest.param(
                b'{"value":79228162514264337593543950335}',
                WithDecimalNoPlaces(value=decimal.Decimal("79228162514264337593543950335")),
                id="int_max_boundary",
            ),
        ],
    )
    def test_load_boundary_values(self, impl: Serializer, data: bytes, expected: WithDecimalNoPlaces) -> None:
        result = impl.load(WithDecimalNoPlaces, data)
        assert result == expected


class TestDecimalPlacesValidation:
    def test_dump_negative_raises(self, impl: Serializer) -> None:
        with pytest.raises(ValueError, match="decimal_places must be None or a non-negative integer"):
            impl.dump(WithDecimal, WithDecimal(value=decimal.Decimal("1.23")), decimal_places=-1)

    def test_dump_many_negative_raises(self, impl: Serializer) -> None:
        if not impl.supports_many:
            pytest.skip("many not supported")
        with pytest.raises(ValueError, match="decimal_places must be None or a non-negative integer"):
            impl.dump_many(WithDecimal, [WithDecimal(value=decimal.Decimal("1.23"))], decimal_places=-1)

    def test_load_negative_raises(self, impl: Serializer) -> None:
        with pytest.raises(ValueError, match="decimal_places must be None or a non-negative integer"):
            impl.load(WithDecimal, b'{"value": "1.23"}', decimal_places=-1)

    def test_load_many_negative_raises(self, impl: Serializer) -> None:
        if not impl.supports_many:
            pytest.skip("many not supported")
        with pytest.raises(ValueError, match="decimal_places must be None or a non-negative integer"):
            impl.load_many(WithDecimal, b'[{"value": "1.23"}]', decimal_places=-1)

    @pytest.mark.parametrize(
        ("obj", "expected"),
        [
            (WithDecimal(value=decimal.Decimal("1.230")), b'{"value":"1.230"}'),
            (WithDecimal(value=decimal.Decimal("100")), b'{"value":"100"}'),
        ],
    )
    def test_dump_valid(self, impl: Serializer, obj: WithDecimal, expected: bytes) -> None:
        result = impl.dump(WithDecimal, obj)
        assert result == expected

    @pytest.mark.parametrize(
        ("data", "expected"),
        [
            (b'{"value":"1.230"}', WithDecimal(value=decimal.Decimal("1.230"))),
            (b'{"value":"100"}', WithDecimal(value=decimal.Decimal("100"))),
        ],
    )
    def test_load_valid(self, impl: Serializer, data: bytes, expected: WithDecimal) -> None:
        result = impl.load(WithDecimal, data)
        assert result == expected


class TestDecimalMetadata:
    @pytest.mark.parametrize(
        "rounding",
        [
            decimal.ROUND_UP,
            decimal.ROUND_DOWN,
            decimal.ROUND_CEILING,
            decimal.ROUND_FLOOR,
            decimal.ROUND_HALF_UP,
            decimal.ROUND_HALF_DOWN,
            decimal.ROUND_HALF_EVEN,
        ],
    )
    def test_supported_rounding_mode_accepted(self, rounding: str) -> None:
        mr.decimal_meta(rounding=rounding)

    def test_unsupported_rounding_mode_raises(self) -> None:
        with pytest.raises(ValueError, match="Unsupported rounding mode"):
            mr.decimal_meta(rounding=decimal.ROUND_05UP)

    @pytest.mark.parametrize("places", [0, 1, 2, 5, 10])
    def test_valid_places_accepted(self, places: int) -> None:
        mr.decimal_meta(places=places)

    def test_negative_places_raises(self) -> None:
        with pytest.raises(ValueError, match="decimal_places must be None or a non-negative integer"):
            mr.decimal_meta(places=-1)
