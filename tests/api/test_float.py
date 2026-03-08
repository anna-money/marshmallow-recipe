import dataclasses

import marshmallow
import pytest

import marshmallow_recipe as mr

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
    @pytest.mark.parametrize(
        ("obj", "expected"),
        [
            (ValueOf[float](value=3.14), b'{"value":3.14}'),
            (ValueOf[float](value=-2.5), b'{"value":-2.5}'),
            (ValueOf[float](value=0.0), b'{"value":0.0}'),
            (ValueOf[float](value=3.141592653589793), b'{"value":3.141592653589793}'),
            (ValueOf[float](value=1), b'{"value":1}'),
            (ValueOf[float](value=1e-100), b'{"value":1e-100}'),
        ],
    )
    def test_dump(self, impl: Serializer, obj: ValueOf[float], expected: bytes) -> None:
        result = impl.dump(ValueOf[float], obj)
        assert result == expected

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

    @pytest.mark.parametrize(
        ("obj", "expected_message"),
        [
            pytest.param(ValueOf[float](value=float("nan")), {"value": ["Not a valid number."]}, id="nan"),
            pytest.param(ValueOf[float](value=float("inf")), {"value": ["Not a valid number."]}, id="inf"),
            pytest.param(ValueOf[float](value=float("-inf")), {"value": ["Not a valid number."]}, id="negative_inf"),
        ],
    )
    def test_special_values_fail(
        self, impl: Serializer, obj: ValueOf[float], expected_message: dict[str, list[str]]
    ) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.dump(ValueOf[float], obj)
        assert exc.value.messages == expected_message

    def test_missing(self, impl: Serializer) -> None:
        obj = WithFloatMissing()
        result = impl.dump(WithFloatMissing, obj)
        assert result == b"{}"

    def test_missing_with_value(self, impl: Serializer) -> None:
        obj = WithFloatMissing(value=3.14)
        result = impl.dump(WithFloatMissing, obj)
        assert result == b'{"value":3.14}'

    @pytest.mark.parametrize(
        ("obj", "expected"),
        [
            (ValueOf[float](value=9223372036854775808), b'{"value":9223372036854775808}'),
            (ValueOf[float](value=18446744073709551616), b'{"value":18446744073709551616}'),
        ],
    )
    def test_big_int_value(self, impl: Serializer, obj: ValueOf[float], expected: bytes) -> None:
        result = impl.dump(ValueOf[float], obj)
        assert result == expected

    def test_big_int_value_very_large(self, impl: Serializer) -> None:
        very_large = 2**100
        obj = ValueOf[float](value=very_large)
        result = impl.dump(ValueOf[float], obj)
        assert result == f'{{"value":{very_large}}}'.encode()

    @pytest.mark.parametrize(
        "obj",
        [
            pytest.param(ValueOf[float](**{"value": "not a float"}), id="string"),  # type: ignore[arg-type]
            pytest.param(ValueOf[float](**{"value": True}), id="bool"),  # type: ignore[arg-type]
            pytest.param(ValueOf[float](**{"value": [1.0, 2.0]}), id="list"),  # type: ignore[arg-type]
        ],
    )
    def test_invalid_type(self, impl: Serializer, obj: ValueOf[float]) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.dump(ValueOf[float], obj)
        if impl.supports_proper_validation_errors_on_dump:
            assert exc.value.messages == {"value": ["Not a valid number."]}

    def test_custom_invalid_error(self, impl: Serializer) -> None:
        obj = WithFloatInvalidError(**{"value": "not a float"})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.dump(WithFloatInvalidError, obj)
        if impl.supports_proper_validation_errors_on_dump:
            assert exc.value.messages == {"value": ["Custom invalid message"]}

    @pytest.mark.parametrize(
        ("meta", "value", "expected"),
        [
            pytest.param(mr.float_meta(gt=0), 1.0, b'{"value":1.0}', id="gt_float"),
            pytest.param(mr.float_meta(gt=0), 1, b'{"value":1}', id="gt_int_bound"),
            pytest.param(mr.float_meta(gte=0.0), 0.0, b'{"value":0.0}', id="gte"),
            pytest.param(mr.float_meta(lt=100), 99.9, b'{"value":99.9}', id="lt"),
            pytest.param(mr.float_meta(lte=100.0), 100.0, b'{"value":100.0}', id="lte"),
            pytest.param(mr.float_meta(gte=0, lte=100), 50.5, b'{"value":50.5}', id="range"),
        ],
    )
    def test_range_pass(self, impl: Serializer, meta: dict[str, object], value: float, expected: bytes) -> None:
        @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
        class DC:
            value: float = dataclasses.field(metadata=meta)

        result = impl.dump(DC, DC(value=value))
        assert result == expected

    @pytest.mark.parametrize(
        ("meta", "value", "expected_messages"),
        [
            pytest.param(mr.float_meta(gt=0), 0.0, {"value": ["Must be greater than 0."]}, id="gt_equal"),
            pytest.param(mr.float_meta(gt=0), -1.0, {"value": ["Must be greater than 0."]}, id="gt_less"),
            pytest.param(mr.float_meta(gte=0.0), -0.1, {"value": ["Must be greater than or equal to 0.0."]}, id="gte"),
            pytest.param(mr.float_meta(lt=100.0), 100.0, {"value": ["Must be less than 100.0."]}, id="lt_equal"),
            pytest.param(mr.float_meta(lt=100.0), 200.0, {"value": ["Must be less than 100.0."]}, id="lt_greater"),
            pytest.param(mr.float_meta(lte=100), 101.0, {"value": ["Must be less than or equal to 100."]}, id="lte"),
            pytest.param(
                mr.float_meta(gte=0.0, lte=100.0),
                -1.0,
                {"value": ["Must be greater than or equal to 0.0."]},
                id="range_below",
            ),
            pytest.param(
                mr.float_meta(gte=0.0, lte=100.0),
                101.0,
                {"value": ["Must be less than or equal to 100.0."]},
                id="range_above",
            ),
        ],
    )
    def test_range_fail(
        self, impl: Serializer, meta: dict[str, object], value: float, expected_messages: dict[str, list[str]]
    ) -> None:
        @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
        class DC:
            value: float = dataclasses.field(metadata=meta)

        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.dump(DC, DC(value=value))
        assert exc.value.messages == expected_messages

    @pytest.mark.parametrize(
        ("meta", "value", "expected_messages"),
        [
            pytest.param(mr.float_meta(gt=0, gt_error="Custom gt error"), 0.0, {"value": ["Custom gt error"]}, id="gt"),
            pytest.param(
                mr.float_meta(gte=0.0, gte_error="Custom gte error"), -1.0, {"value": ["Custom gte error"]}, id="gte"
            ),
            pytest.param(
                mr.float_meta(lt=100, lt_error="Custom lt error"), 100.0, {"value": ["Custom lt error"]}, id="lt"
            ),
            pytest.param(
                mr.float_meta(lte=100.0, lte_error="Custom lte error"), 101.0, {"value": ["Custom lte error"]}, id="lte"
            ),
        ],
    )
    def test_range_custom_error(
        self, impl: Serializer, meta: dict[str, object], value: float, expected_messages: dict[str, list[str]]
    ) -> None:
        @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
        class DC:
            value: float = dataclasses.field(metadata=meta)

        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.dump(DC, DC(value=value))
        assert exc.value.messages == expected_messages

    def test_range_optional_none(self, impl: Serializer) -> None:
        @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
        class DC:
            value: float | None = dataclasses.field(default=None, metadata=mr.float_meta(gt=0))

        result = impl.dump(DC, DC(value=None))
        assert result == b"{}"


class TestFloatLoad:
    @pytest.mark.parametrize(
        ("data", "expected"),
        [
            (b'{"value":3.14}', ValueOf[float](value=3.14)),
            (b'{"value":-2.5}', ValueOf[float](value=-2.5)),
            (b'{"value":0.0}', ValueOf[float](value=0.0)),
            (b'{"value":3.141592653589793}', ValueOf[float](value=3.141592653589793)),
            (b'{"value":1e-100}', ValueOf[float](value=1e-100)),
            (b'{"value":-0.0}', ValueOf[float](value=0.0)),
        ],
    )
    def test_load(self, impl: Serializer, data: bytes, expected: ValueOf[float]) -> None:
        result = impl.load(ValueOf[float], data)
        assert result == expected

    def test_integral_value(self, impl: Serializer) -> None:
        data = b'{"value":1}'
        result = impl.load(ValueOf[float], data)
        assert result == ValueOf[float](value=1)
        assert type(result.value) is int  # JSON int stays int, no precision loss

    @pytest.mark.parametrize(
        ("data", "expected"),
        [(b'{"value":5.5}', WithFloatValidation(value=5.5)), (b'{"value":0.0}', WithFloatValidation(value=0.0))],
    )
    def test_validation_pass(self, impl: Serializer, data: bytes, expected: WithFloatValidation) -> None:
        result = impl.load(WithFloatValidation, data)
        assert result == expected

    def test_validation_negative_fail(self, impl: Serializer) -> None:
        data = b'{"value":-1.5}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithFloatValidation, data)
        assert exc.value.messages == {"value": ["Invalid value."]}

    def test_two_validators_pass(self, impl: Serializer) -> None:
        data = b'{"value":50.5}'
        result = impl.load(WithFloatTwoValidators, data)
        assert result == WithFloatTwoValidators(value=50.5)

    @pytest.mark.parametrize(
        ("data", "expected_message"),
        [
            pytest.param(b'{"value":-1.0}', {"value": ["Invalid value."]}, id="first_fails"),
            pytest.param(b'{"value":150.0}', {"value": ["Invalid value."]}, id="second_fails"),
        ],
    )
    def test_two_validators_fail(self, impl: Serializer, data: bytes, expected_message: dict[str, list[str]]) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithFloatTwoValidators, data)
        assert exc.value.messages == expected_message

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

    @pytest.mark.parametrize(
        ("data",),
        [
            pytest.param(b'{"value":"not-a-number"}', id="null"),
            pytest.param(b'{"value":"+inf"}', id="special"),
            pytest.param(b'{"value":"-inf"}', id="special"),
            pytest.param(b'{"value":"nan"}', id="special"),
        ],
    )
    def test_custom_invalid_error(self, data: bytes, impl: Serializer) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithFloatInvalidError, data)
        assert exc.value.messages == {"value": ["Custom invalid message"]}

    @pytest.mark.parametrize(
        ("data", "expected_message"),
        [
            pytest.param(b'{"value":"not_a_float"}', {"value": ["Not a valid number."]}, id="string"),
            pytest.param(b'{"value":[1.0,2.0]}', {"value": ["Not a valid number."]}, id="list"),
            pytest.param(b'{"value":{"key":1.0}}', {"value": ["Not a valid number."]}, id="object"),
        ],
    )
    def test_wrong_type(self, impl: Serializer, data: bytes, expected_message: dict[str, list[str]]) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[float], data)
        assert exc.value.messages == expected_message

    def test_missing_required(self, impl: Serializer) -> None:
        data = b"{}"
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[float], data)
        assert exc.value.messages == {"value": ["Missing data for required field."]}

    @pytest.mark.parametrize(
        ("data", "expected"),
        [
            (b'{"value":9223372036854775808}', ValueOf[float](value=9223372036854775808.0)),
            (b'{"value":18446744073709551616}', ValueOf[float](value=18446744073709551616.0)),
        ],
    )
    def test_big_from_int(self, impl: Serializer, data: bytes, expected: ValueOf[float]) -> None:
        result = impl.load(ValueOf[float], data)
        assert result == expected

    def test_nan_fails(self, impl: Serializer) -> None:
        data = b'{"value":NaN}'
        if impl.supports_special_float_validation:
            with pytest.raises(marshmallow.ValidationError) as exc:
                impl.load(ValueOf[float], data)
            assert exc.value.messages == {"value": ["Not a valid number."]}
        else:
            with pytest.raises(Exception):
                impl.load(ValueOf[float], data)

    def test_inf_fails(self, impl: Serializer) -> None:
        data = b'{"value":Infinity}'
        if impl.supports_special_float_validation:
            with pytest.raises(marshmallow.ValidationError) as exc:
                impl.load(ValueOf[float], data)
            assert exc.value.messages == {"value": ["Not a valid number."]}
        else:
            with pytest.raises(Exception):
                impl.load(ValueOf[float], data)

    def test_negative_inf_fails(self, impl: Serializer) -> None:
        data = b'{"value":-Infinity}'
        if impl.supports_special_float_validation:
            with pytest.raises(marshmallow.ValidationError) as exc:
                impl.load(ValueOf[float], data)
            assert exc.value.messages == {"value": ["Not a valid number."]}
        else:
            with pytest.raises(Exception):
                impl.load(ValueOf[float], data)

    @pytest.mark.parametrize(
        ("data", "expected"),
        [
            (b'{"value":"3.14"}', ValueOf[float](value=3.14)),
            (b'{"value":"-2.5"}', ValueOf[float](value=-2.5)),
            (b'{"value":"42"}', ValueOf[float](value=42.0)),
            (b'{"value":"1.5e10"}', ValueOf[float](value=1.5e10)),
            (b'{"value":"3.141592653589793238462643383279502884197"}', ValueOf[float](value=3.141592653589793)),
            (b'{"value":"1e-308"}', ValueOf[float](value=1e-308)),
            (b'{"value":"1e308"}', ValueOf[float](value=1e308)),
        ],
    )
    def test_from_string(self, impl: Serializer, data: bytes, expected: ValueOf[float]) -> None:
        result = impl.load(ValueOf[float], data)
        assert result == expected

    @pytest.mark.parametrize(
        ("data", "expected_message"),
        [
            pytest.param(b'{"value":"not_a_number"}', {"value": ["Not a valid number."]}, id="invalid"),
            pytest.param(b'{"value":""}', {"value": ["Not a valid number."]}, id="empty"),
        ],
    )
    def test_from_string_invalid(self, impl: Serializer, data: bytes, expected_message: dict[str, list[str]]) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[float], data)
        assert exc.value.messages == expected_message

    @pytest.mark.parametrize(
        ("data", "expected_message"),
        [
            pytest.param(b'{"value":"NaN"}', {"value": ["Not a valid number."]}, id="nan"),
            pytest.param(b'{"value":"Infinity"}', {"value": ["Not a valid number."]}, id="inf"),
            pytest.param(b'{"value":"-Infinity"}', {"value": ["Not a valid number."]}, id="negative_inf"),
        ],
    )
    def test_from_string_special_values_fail(
        self, impl: Serializer, data: bytes, expected_message: dict[str, list[str]]
    ) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[float], data)
        assert exc.value.messages == expected_message

    def test_missing(self, impl: Serializer) -> None:
        data = b"{}"
        result = impl.load(WithFloatMissing, data)
        assert result == WithFloatMissing()

    def test_missing_with_value(self, impl: Serializer) -> None:
        data = b'{"value":3.14}'
        result = impl.load(WithFloatMissing, data)
        assert result == WithFloatMissing(value=3.14)

    @pytest.mark.parametrize(
        ("meta", "data", "expected_value"),
        [
            pytest.param(mr.float_meta(gt=0), b'{"value":1.0}', 1.0, id="gt"),
            pytest.param(mr.float_meta(gte=0.0), b'{"value":0.0}', 0.0, id="gte_equal"),
            pytest.param(mr.float_meta(gte=0), b'{"value":1.0}', 1.0, id="gte_above"),
            pytest.param(mr.float_meta(lt=100), b'{"value":99.9}', 99.9, id="lt"),
            pytest.param(mr.float_meta(lte=100.0), b'{"value":100.0}', 100.0, id="lte_equal"),
            pytest.param(mr.float_meta(gte=0, lte=100), b'{"value":50.5}', 50.5, id="range"),
        ],
    )
    def test_range_pass(self, impl: Serializer, meta: dict[str, object], data: bytes, expected_value: float) -> None:
        @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
        class DC:
            value: float = dataclasses.field(metadata=meta)

        result = impl.load(DC, data)
        assert result == DC(value=expected_value)

    @pytest.mark.parametrize(
        ("meta", "data", "expected_messages"),
        [
            pytest.param(mr.float_meta(gt=0), b'{"value":0.0}', {"value": ["Must be greater than 0."]}, id="gt_equal"),
            pytest.param(mr.float_meta(gt=0), b'{"value":-1.0}', {"value": ["Must be greater than 0."]}, id="gt_less"),
            pytest.param(
                mr.float_meta(gte=0.0),
                b'{"value":-0.1}',
                {"value": ["Must be greater than or equal to 0.0."]},
                id="gte",
            ),
            pytest.param(
                mr.float_meta(lt=100.0), b'{"value":100.0}', {"value": ["Must be less than 100.0."]}, id="lt_equal"
            ),
            pytest.param(
                mr.float_meta(lt=100.0), b'{"value":200.0}', {"value": ["Must be less than 100.0."]}, id="lt_greater"
            ),
            pytest.param(
                mr.float_meta(lte=100), b'{"value":101.0}', {"value": ["Must be less than or equal to 100."]}, id="lte"
            ),
            pytest.param(
                mr.float_meta(gte=0.0, lte=100.0),
                b'{"value":-1.0}',
                {"value": ["Must be greater than or equal to 0.0."]},
                id="range_below",
            ),
            pytest.param(
                mr.float_meta(gte=0.0, lte=100.0),
                b'{"value":101.0}',
                {"value": ["Must be less than or equal to 100.0."]},
                id="range_above",
            ),
        ],
    )
    def test_range_fail(
        self, impl: Serializer, meta: dict[str, object], data: bytes, expected_messages: dict[str, list[str]]
    ) -> None:
        @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
        class DC:
            value: float = dataclasses.field(metadata=meta)

        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(DC, data)
        assert exc.value.messages == expected_messages

    @pytest.mark.parametrize(
        ("meta", "data", "expected_messages"),
        [
            pytest.param(
                mr.float_meta(gt=0, gt_error="Custom gt error"),
                b'{"value":0.0}',
                {"value": ["Custom gt error"]},
                id="gt",
            ),
            pytest.param(
                mr.float_meta(gte=0.0, gte_error="Custom gte error"),
                b'{"value":-1.0}',
                {"value": ["Custom gte error"]},
                id="gte",
            ),
            pytest.param(
                mr.float_meta(lt=100, lt_error="Custom lt error"),
                b'{"value":100.0}',
                {"value": ["Custom lt error"]},
                id="lt",
            ),
            pytest.param(
                mr.float_meta(lte=100.0, lte_error="Custom lte error"),
                b'{"value":101.0}',
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
            value: float = dataclasses.field(metadata=meta)

        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(DC, data)
        assert exc.value.messages == expected_messages

    def test_range_optional_none(self, impl: Serializer) -> None:
        @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
        class DC:
            value: float | None = dataclasses.field(default=None, metadata=mr.float_meta(gt=0))

        result = impl.load(DC, b'{"value":null}')
        assert result == DC(value=None)


class TestFloatMetaValidation:
    @pytest.mark.parametrize("bound_name", ["gt", "gte", "lt", "lte"])
    def test_bool_bound_raises(self, bound_name: str) -> None:
        with pytest.raises(TypeError, match=f"{bound_name} must be float or int, got bool"):
            mr.float_meta(**{bound_name: True})  # type: ignore[reportArgumentType]

    @pytest.mark.parametrize("bound_name", ["gt", "gte", "lt", "lte"])
    def test_str_bound_raises(self, bound_name: str) -> None:
        with pytest.raises(TypeError, match=f"{bound_name} must be float or int, got str"):
            mr.float_meta(**{bound_name: "1"})  # type: ignore[reportArgumentType]

    def test_gt_and_gte_mutually_exclusive(self) -> None:
        with pytest.raises(ValueError, match="gt and gte are mutually exclusive"):
            mr.float_meta(gt=0, gte=0)

    def test_lt_and_lte_mutually_exclusive(self) -> None:
        with pytest.raises(ValueError, match="lt and lte are mutually exclusive"):
            mr.float_meta(lt=100.0, lte=100.0)

    @pytest.mark.parametrize(
        ("kwargs", "match"),
        [
            pytest.param({"gt": 10, "lt": 10}, "lower bound 10 must be less than upper bound 10", id="gt_eq_lt"),
            pytest.param({"gt": 10, "lt": 5}, "lower bound 10 must be less than upper bound 5", id="gt_above_lt"),
            pytest.param(
                {"gt": 10.0, "lte": 10.0}, "lower bound 10.0 must be less than upper bound 10.0", id="gt_eq_lte"
            ),
            pytest.param(
                {"gte": 10.0, "lt": 10.0}, "lower bound 10.0 must be less than upper bound 10.0", id="gte_eq_lt"
            ),
            pytest.param(
                {"gte": 10, "lte": 5}, "lower bound 10 must be less than or equal to upper bound 5", id="gte_above_lte"
            ),
        ],
    )
    def test_invalid_range(self, kwargs: dict[str, float | int], match: str) -> None:
        with pytest.raises(ValueError, match=match):
            mr.float_meta(**kwargs)  # type: ignore[reportArgumentType]

    @pytest.mark.parametrize(
        "kwargs",
        [
            pytest.param({"gt": 0, "lt": 10}, id="gt_lt"),
            pytest.param({"gt": 0.0, "lte": 10.0}, id="gt_lte"),
            pytest.param({"gte": 0, "lt": 10}, id="gte_lt"),
            pytest.param({"gte": 0.0, "lte": 10.0}, id="gte_lte"),
            pytest.param({"gte": 10.0, "lte": 10.0}, id="gte_eq_lte"),
        ],
    )
    def test_valid_range(self, kwargs: dict[str, float | int]) -> None:
        mr.float_meta(**kwargs)  # type: ignore[reportArgumentType]

    @pytest.mark.parametrize("bound_name", ["gt", "gte", "lt", "lte"])
    def test_nan_bound_raises(self, bound_name: str) -> None:
        with pytest.raises(ValueError, match=f"{bound_name} must be a finite number"):
            mr.float_meta(**{bound_name: float("nan")})  # type: ignore[reportArgumentType]

    @pytest.mark.parametrize("bound_name", ["gt", "gte", "lt", "lte"])
    def test_inf_bound_raises(self, bound_name: str) -> None:
        with pytest.raises(ValueError, match=f"{bound_name} must be a finite number"):
            mr.float_meta(**{bound_name: float("inf")})  # type: ignore[reportArgumentType]
