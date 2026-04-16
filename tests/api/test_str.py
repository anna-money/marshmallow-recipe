import re

import marshmallow
import pytest

import marshmallow_recipe as mr

from .conftest import (
    OptionalValueOf,
    Serializer,
    ValueOf,
    WithOptionalPostLoadAndStrip,
    WithOptionalStrStripWhitespace,
    WithPostLoadAndStrip,
    WithPostLoadTransform,
    WithStrDefault,
    WithStrInvalidError,
    WithStripWhitespace,
    WithStrLengthAndRegexp,
    WithStrMaxLength,
    WithStrMaxLengthError,
    WithStrMinLength,
    WithStrMinLengthError,
    WithStrMinMaxLength,
    WithStrMissing,
    WithStrNoneError,
    WithStrRegexp,
    WithStrRegexpError,
    WithStrRegexpUnanchored,
    WithStrRequiredError,
    WithStrStripAndRegexp,
    WithStrTwoValidators,
    WithStrValidation,
)


class TestStrDump:
    def test_non_empty(self, impl: Serializer) -> None:
        obj = ValueOf[str](value="hello")
        result = impl.dump(ValueOf[str], obj)
        assert result == b'{"value":"hello"}'

    def test_empty(self, impl: Serializer) -> None:
        obj = ValueOf[str](value="")
        result = impl.dump(ValueOf[str], obj)
        assert result == b'{"value":""}'

    def test_optional_none(self, impl: Serializer) -> None:
        obj = OptionalValueOf[str](value=None)
        result = impl.dump(OptionalValueOf[str], obj)
        assert result == b"{}"

    def test_optional_value(self, impl: Serializer) -> None:
        obj = OptionalValueOf[str](value="hello")
        result = impl.dump(OptionalValueOf[str], obj)
        assert result == b'{"value":"hello"}'

    def test_default_provided(self, impl: Serializer) -> None:
        obj = WithStrDefault(value="custom")
        result = impl.dump(WithStrDefault, obj)
        assert result == b'{"value":"custom"}'

    def test_none_handling_ignore_default(self, impl: Serializer) -> None:
        obj = OptionalValueOf[str](value=None)
        result = impl.dump(OptionalValueOf[str], obj)
        assert result == b"{}"

    def test_none_handling_ignore_explicit(self, impl: Serializer) -> None:
        obj = OptionalValueOf[str](value=None)
        result = impl.dump(OptionalValueOf[str], obj, none_value_handling=mr.NoneValueHandling.IGNORE)
        assert result == b"{}"

    def test_none_handling_include(self, impl: Serializer) -> None:
        obj = OptionalValueOf[str](value=None)
        result = impl.dump(OptionalValueOf[str], obj, none_value_handling=mr.NoneValueHandling.INCLUDE)
        assert result == b'{"value":null}'

    def test_none_handling_include_with_value(self, impl: Serializer) -> None:
        obj = OptionalValueOf[str](value="hello")
        result = impl.dump(OptionalValueOf[str], obj, none_value_handling=mr.NoneValueHandling.INCLUDE)
        assert result == b'{"value":"hello"}'

    def test_strip_whitespace(self, impl: Serializer) -> None:
        obj = WithStripWhitespace(name="  John  ", email="  test@example.com  ")
        result = impl.dump(WithStripWhitespace, obj)
        assert result == b'{"name":"John","email":"test@example.com"}'

    def test_strip_whitespace_already_clean(self, impl: Serializer) -> None:
        obj = WithStripWhitespace(name="Bob", email="bob@example.com")
        result = impl.dump(WithStripWhitespace, obj)
        assert result == b'{"name":"Bob","email":"bob@example.com"}'

    def test_strip_whitespace_optional_whitespace_only(self, impl: Serializer) -> None:
        obj = WithOptionalStrStripWhitespace(value="   ")
        result = impl.dump(WithOptionalStrStripWhitespace, obj)
        assert result == b"{}"

    def test_post_load_transform(self, impl: Serializer) -> None:
        obj = WithPostLoadTransform(name="hello")
        result = impl.dump(WithPostLoadTransform, obj)
        assert result == b'{"name":"hello"}'

    def test_post_load_with_strip(self, impl: Serializer) -> None:
        obj = WithPostLoadAndStrip(value="WORLD")
        result = impl.dump(WithPostLoadAndStrip, obj)
        assert result == b'{"value":"WORLD"}'

    @pytest.mark.parametrize(
        ("obj", "expected"),
        [
            pytest.param(WithOptionalPostLoadAndStrip(value="WORLD"), b'{"value":"WORLD"}', id="value"),
            pytest.param(WithOptionalPostLoadAndStrip(value=None), b"{}", id="none"),
        ],
    )
    def test_optional_post_load_with_strip(
        self, impl: Serializer, obj: WithOptionalPostLoadAndStrip, expected: bytes
    ) -> None:
        result = impl.dump(WithOptionalPostLoadAndStrip, obj)
        assert result == expected

    def test_missing(self, impl: Serializer) -> None:
        obj = WithStrMissing()
        result = impl.dump(WithStrMissing, obj)
        assert result == b"{}"

    def test_missing_with_value(self, impl: Serializer) -> None:
        obj = WithStrMissing(value="hello")
        result = impl.dump(WithStrMissing, obj)
        assert result == b'{"value":"hello"}'

    @pytest.mark.parametrize(
        "obj",
        [
            pytest.param(ValueOf[str](**{"value": 123}), id="int"),  # type: ignore[arg-type]
            pytest.param(ValueOf[str](**{"value": ["a", "b"]}), id="list"),  # type: ignore[arg-type]
        ],
    )
    def test_invalid_type(self, impl: Serializer, obj: ValueOf[str]) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.dump(ValueOf[str], obj)
        if impl.supports_proper_validation_errors_on_dump:
            assert exc.value.messages == {"value": ["Not a valid string."]}

    def test_custom_invalid_error(self, impl: Serializer) -> None:
        obj = WithStrInvalidError(**{"value": 123})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.dump(WithStrInvalidError, obj)
        if impl.supports_proper_validation_errors_on_dump:
            assert exc.value.messages == {"value": ["Custom invalid message"]}

    @pytest.mark.parametrize(
        ("schema_type", "obj"),
        [
            pytest.param(WithStrMinLength, WithStrMinLength(value="ab"), id="min_length_ok"),
            pytest.param(WithStrMaxLength, WithStrMaxLength(value="hello"), id="max_length_ok"),
            pytest.param(WithStrMinMaxLength, WithStrMinMaxLength(value="hello"), id="min_max_length_ok"),
        ],
    )
    def test_length_pass(self, impl: Serializer, schema_type: type, obj: object) -> None:
        impl.dump(schema_type, obj)

    @pytest.mark.parametrize(
        ("schema_type", "obj", "error_messages"),
        [
            pytest.param(
                WithStrMinLength,
                WithStrMinLength(value="a"),
                {"value": ["Shorter than minimum length 2."]},
                id="min_length",
            ),
            pytest.param(
                WithStrMaxLength,
                WithStrMaxLength(value="toolong"),
                {"value": ["Longer than maximum length 5."]},
                id="max_length",
            ),
            pytest.param(
                WithStrMinMaxLength,
                WithStrMinMaxLength(value=""),
                {"value": ["Shorter than minimum length 1."]},
                id="min_max_below",
            ),
            pytest.param(
                WithStrMinMaxLength,
                WithStrMinMaxLength(value="a" * 11),
                {"value": ["Longer than maximum length 10."]},
                id="min_max_above",
            ),
            pytest.param(
                WithStrMinLengthError,
                WithStrMinLengthError(value="a"),
                {"value": ["At least 2 chars"]},
                id="min_length_custom_error",
            ),
            pytest.param(
                WithStrMaxLengthError,
                WithStrMaxLengthError(value="toolong"),
                {"value": ["At most 5 chars"]},
                id="max_length_custom_error",
            ),
        ],
    )
    def test_length_fail(
        self, impl: Serializer, schema_type: type, obj: object, error_messages: dict[str, list[str]]
    ) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.dump(schema_type, obj)
        if impl.supports_proper_validation_errors_on_dump:
            assert exc.value.messages == error_messages

    @pytest.mark.parametrize(
        ("schema_type", "obj"),
        [
            pytest.param(WithStrRegexp, WithStrRegexp(value="12345"), id="regexp_anchored"),
            pytest.param(WithStrRegexpUnanchored, WithStrRegexpUnanchored(value="123abc"), id="regexp_unanchored"),
        ],
    )
    def test_regexp_pass(self, impl: Serializer, schema_type: type, obj: object) -> None:
        impl.dump(schema_type, obj)

    @pytest.mark.parametrize(
        ("schema_type", "obj", "error_messages"),
        [
            pytest.param(
                WithStrRegexp,
                WithStrRegexp(value="abc"),
                {"value": ["String does not match expected pattern."]},
                id="regexp_anchored",
            ),
            pytest.param(
                WithStrRegexpUnanchored,
                WithStrRegexpUnanchored(value="abc"),
                {"value": ["String does not match expected pattern."]},
                id="regexp_unanchored_no_match",
            ),
            pytest.param(
                WithStrRegexpUnanchored,
                WithStrRegexpUnanchored(value="abc123"),
                {"value": ["String does not match expected pattern."]},
                id="regexp_unanchored_match_not_at_start",
            ),
            pytest.param(
                WithStrRegexpError,
                WithStrRegexpError(value="abc"),
                {"value": ["Must be digits"]},
                id="regexp_custom_error",
            ),
        ],
    )
    def test_regexp_fail(
        self, impl: Serializer, schema_type: type, obj: object, error_messages: dict[str, list[str]]
    ) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.dump(schema_type, obj)
        if impl.supports_proper_validation_errors_on_dump:
            assert exc.value.messages == error_messages

    def test_strip_and_regexp_pass(self, impl: Serializer) -> None:
        obj = WithStrStripAndRegexp(value="hello")
        result = impl.dump(WithStrStripAndRegexp, obj)
        assert result == b'{"value":"hello"}'

    def test_strip_and_regexp_strips_before_validating(self, impl: Serializer) -> None:
        obj = WithStrStripAndRegexp(value="  hello  ")
        result = impl.dump(WithStrStripAndRegexp, obj)
        assert result == b'{"value":"hello"}'


class TestStrLoad:
    def test_non_empty(self, impl: Serializer) -> None:
        data = b'{"value":"hello"}'
        result = impl.load(ValueOf[str], data)
        assert result == ValueOf[str](value="hello")

    def test_empty(self, impl: Serializer) -> None:
        data = b'{"value":""}'
        result = impl.load(ValueOf[str], data)
        assert result == ValueOf[str](value="")

    def test_validation_pass(self, impl: Serializer) -> None:
        data = b'{"value":"hello"}'
        result = impl.load(WithStrValidation, data)
        assert result == WithStrValidation(value="hello")

    def test_validation_empty_fail(self, impl: Serializer) -> None:
        data = b'{"value":""}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithStrValidation, data)
        assert exc.value.messages == {"value": ["Invalid value."]}

    def test_two_validators_pass(self, impl: Serializer) -> None:
        data = b'{"value":"hello"}'
        result = impl.load(WithStrTwoValidators, data)
        assert result == WithStrTwoValidators(value="hello")

    def test_two_validators_first_fails(self, impl: Serializer) -> None:
        data = b'{"value":""}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithStrTwoValidators, data)
        assert exc.value.messages == {"value": ["Invalid value."]}

    def test_two_validators_second_fails(self, impl: Serializer) -> None:
        data = b'{"value":"' + b"x" * 150 + b'"}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithStrTwoValidators, data)
        assert exc.value.messages == {"value": ["Invalid value."]}

    def test_optional_none(self, impl: Serializer) -> None:
        data = b'{"value":null}'
        result = impl.load(OptionalValueOf[str], data)
        assert result == OptionalValueOf[str](value=None)

    def test_optional_missing(self, impl: Serializer) -> None:
        data = b"{}"
        result = impl.load(OptionalValueOf[str], data)
        assert result == OptionalValueOf[str](value=None)

    def test_optional_value(self, impl: Serializer) -> None:
        data = b'{"value":"hello"}'
        result = impl.load(OptionalValueOf[str], data)
        assert result == OptionalValueOf[str](value="hello")

    def test_default_omitted(self, impl: Serializer) -> None:
        data = b"{}"
        result = impl.load(WithStrDefault, data)
        assert result == WithStrDefault(value="default")

    def test_default_provided(self, impl: Serializer) -> None:
        data = b'{"value":"custom"}'
        result = impl.load(WithStrDefault, data)
        assert result == WithStrDefault(value="custom")

    def test_custom_required_error(self, impl: Serializer) -> None:
        data = b"{}"
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithStrRequiredError, data)
        assert exc.value.messages == {"value": ["Custom required message"]}

    def test_custom_none_error(self, impl: Serializer) -> None:
        data = b'{"value":null}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithStrNoneError, data)
        assert exc.value.messages == {"value": ["Custom none message"]}

    def test_custom_invalid_error(self, impl: Serializer) -> None:
        data = b'{"value":123}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithStrInvalidError, data)
        assert exc.value.messages == {"value": ["Custom invalid message"]}

    @pytest.mark.parametrize(
        "data",
        [
            pytest.param(b'{"value":123}', id="int"),
            pytest.param(b'{"value":["a","b"]}', id="list"),
            pytest.param(b'{"value":{"key":"val"}}', id="object"),
        ],
    )
    def test_wrong_type(self, impl: Serializer, data: bytes) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[str], data)
        assert exc.value.messages == {"value": ["Not a valid string."]}

    def test_missing_required(self, impl: Serializer) -> None:
        data = b"{}"
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[str], data)
        assert exc.value.messages == {"value": ["Missing data for required field."]}

    def test_strip_whitespace(self, impl: Serializer) -> None:
        data = b'{"name":"  Alice  ","email":"  alice@example.com  "}'
        result = impl.load(WithStripWhitespace, data)
        assert result == WithStripWhitespace(name="Alice", email="alice@example.com")

    def test_strip_whitespace_optional_whitespace_only(self, impl: Serializer) -> None:
        data = b'{"value":"   "}'
        result = impl.load(WithOptionalStrStripWhitespace, data)
        assert result == WithOptionalStrStripWhitespace(value=None)

    def test_post_load_transform(self, impl: Serializer) -> None:
        data = b'{"name":"hello"}'
        result = impl.load(WithPostLoadTransform, data)
        assert result == WithPostLoadTransform(name="HELLO")

    def test_post_load_with_strip(self, impl: Serializer) -> None:
        data = b'{"value":"  HELLO  "}'
        result = impl.load(WithPostLoadAndStrip, data)
        assert result == WithPostLoadAndStrip(value="hello")

    @pytest.mark.parametrize(
        ("data", "expected"),
        [
            pytest.param(b'{"value":"   "}', WithOptionalPostLoadAndStrip(value=None), id="whitespace_only"),
            pytest.param(
                b'{"value":"  HELLO  "}', WithOptionalPostLoadAndStrip(value="hello"), id="strip_and_post_load"
            ),
            pytest.param(b'{"value":null}', WithOptionalPostLoadAndStrip(value=None), id="null"),
        ],
    )
    def test_optional_post_load_with_strip(
        self, impl: Serializer, data: bytes, expected: WithOptionalPostLoadAndStrip
    ) -> None:
        result = impl.load(WithOptionalPostLoadAndStrip, data)
        assert result == expected

    def test_missing(self, impl: Serializer) -> None:
        data = b"{}"
        result = impl.load(WithStrMissing, data)
        assert result == WithStrMissing()

    def test_missing_with_value(self, impl: Serializer) -> None:
        data = b'{"value":"hello"}'
        result = impl.load(WithStrMissing, data)
        assert result == WithStrMissing(value="hello")

    @pytest.mark.parametrize(
        ("schema_type", "data", "expected"),
        [
            pytest.param(WithStrMinLength, b'{"value":"ab"}', WithStrMinLength(value="ab"), id="min_length_ok"),
            pytest.param(WithStrMaxLength, b'{"value":"hello"}', WithStrMaxLength(value="hello"), id="max_length_ok"),
            pytest.param(
                WithStrMinMaxLength, b'{"value":"hello"}', WithStrMinMaxLength(value="hello"), id="min_max_length_ok"
            ),
        ],
    )
    def test_length_pass(self, impl: Serializer, schema_type: type, data: bytes, expected: object) -> None:
        result = impl.load(schema_type, data)
        assert result == expected

    @pytest.mark.parametrize(
        ("schema_type", "data", "error_messages"),
        [
            pytest.param(
                WithStrMinLength, b'{"value":"a"}', {"value": ["Shorter than minimum length 2."]}, id="min_length"
            ),
            pytest.param(
                WithStrMaxLength, b'{"value":"toolong"}', {"value": ["Longer than maximum length 5."]}, id="max_length"
            ),
            pytest.param(
                WithStrMinMaxLength, b'{"value":""}', {"value": ["Shorter than minimum length 1."]}, id="min_max_below"
            ),
            pytest.param(
                WithStrMinMaxLength,
                b'{"value":"aaaaaaaaaaa"}',
                {"value": ["Longer than maximum length 10."]},
                id="min_max_above",
            ),
            pytest.param(
                WithStrMinLengthError, b'{"value":"a"}', {"value": ["At least 2 chars"]}, id="min_length_custom_error"
            ),
            pytest.param(
                WithStrMaxLengthError,
                b'{"value":"toolong"}',
                {"value": ["At most 5 chars"]},
                id="max_length_custom_error",
            ),
        ],
    )
    def test_length_fail(
        self, impl: Serializer, data: bytes, schema_type: type, error_messages: dict[str, list[str]]
    ) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(schema_type, data)
        assert exc.value.messages == error_messages

    @pytest.mark.parametrize(
        ("schema_type", "data", "expected"),
        [
            pytest.param(WithStrRegexp, b'{"value":"12345"}', WithStrRegexp(value="12345"), id="regexp_anchored"),
            pytest.param(
                WithStrRegexpUnanchored,
                b'{"value":"123abc"}',
                WithStrRegexpUnanchored(value="123abc"),
                id="regexp_unanchored",
            ),
        ],
    )
    def test_regexp_pass(self, impl: Serializer, schema_type: type, data: bytes, expected: object) -> None:
        result = impl.load(schema_type, data)
        assert result == expected

    @pytest.mark.parametrize(
        ("schema_type", "data", "error_messages"),
        [
            pytest.param(
                WithStrRegexp,
                b'{"value":"abc"}',
                {"value": ["String does not match expected pattern."]},
                id="regexp_anchored",
            ),
            pytest.param(
                WithStrRegexpUnanchored,
                b'{"value":"abc"}',
                {"value": ["String does not match expected pattern."]},
                id="regexp_unanchored_no_match",
            ),
            pytest.param(
                WithStrRegexpUnanchored,
                b'{"value":"abc123"}',
                {"value": ["String does not match expected pattern."]},
                id="regexp_unanchored_match_not_at_start",
            ),
            pytest.param(
                WithStrRegexpError, b'{"value":"abc"}', {"value": ["Must be digits"]}, id="regexp_custom_error"
            ),
        ],
    )
    def test_regexp_fail(
        self, impl: Serializer, schema_type: type, data: bytes, error_messages: dict[str, list[str]]
    ) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(schema_type, data)
        assert exc.value.messages == error_messages

    def test_strip_and_regexp_pass(self, impl: Serializer) -> None:
        data = b'{"value":"  hello  "}'
        result = impl.load(WithStrStripAndRegexp, data)
        assert result == WithStrStripAndRegexp(value="hello")

    def test_strip_and_regexp_fail(self, impl: Serializer) -> None:
        data = b'{"value":"  HELLO  "}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithStrStripAndRegexp, data)
        assert exc.value.messages == {"value": ["String does not match expected pattern."]}

    @pytest.mark.parametrize(
        ("schema_type", "data", "error_messages"),
        [
            pytest.param(
                WithStrLengthAndRegexp,
                b'{"value":"a"}',
                {"value": ["Shorter than minimum length 2."]},
                id="min_length_first",
            ),
            pytest.param(
                WithStrLengthAndRegexp,
                b'{"value":"abcdefghijk"}',
                {"value": ["Longer than maximum length 10."]},
                id="max_length_first",
            ),
            pytest.param(
                WithStrLengthAndRegexp,
                b'{"value":"HELLO"}',
                {"value": ["String does not match expected pattern."]},
                id="regexp_after_length",
            ),
        ],
    )
    def test_combined_length_and_regexp_fail(
        self, impl: Serializer, schema_type: type, data: bytes, error_messages: dict[str, list[str]]
    ) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(schema_type, data)
        assert exc.value.messages == error_messages


class TestStrMetaValidation:
    @pytest.mark.parametrize("bound_name", ["min_length", "max_length"])
    def test_bool_bound_raises(self, bound_name: str) -> None:
        with pytest.raises(TypeError, match=f"{bound_name} must be int, got bool"):
            mr.str_meta(**{bound_name: True})  # type: ignore[reportArgumentType]

    @pytest.mark.parametrize("bound_name", ["min_length", "max_length"])
    def test_float_bound_raises(self, bound_name: str) -> None:
        with pytest.raises(TypeError, match=f"{bound_name} must be int, got float"):
            mr.str_meta(**{bound_name: 1.5})  # type: ignore[reportArgumentType]

    @pytest.mark.parametrize("bound_name", ["min_length", "max_length"])
    def test_str_bound_raises(self, bound_name: str) -> None:
        with pytest.raises(TypeError, match=f"{bound_name} must be int, got str"):
            mr.str_meta(**{bound_name: "1"})  # type: ignore[reportArgumentType]

    @pytest.mark.parametrize("bound_name", ["min_length", "max_length"])
    def test_negative_bound_raises(self, bound_name: str) -> None:
        with pytest.raises(ValueError, match=f"{bound_name} must be a non-negative integer, got -1"):
            mr.str_meta(**{bound_name: -1})  # type: ignore[reportArgumentType]

    def test_min_greater_than_max_raises(self) -> None:
        with pytest.raises(ValueError, match="min_length 5 must be less than or equal to max_length 3"):
            mr.str_meta(min_length=5, max_length=3)

    @pytest.mark.parametrize(
        "kwargs",
        [
            pytest.param({"min_length": 0}, id="min_zero"),
            pytest.param({"max_length": 0}, id="max_zero"),
            pytest.param({"min_length": 1, "max_length": 5}, id="min_max"),
            pytest.param({"min_length": 3, "max_length": 3}, id="min_eq_max"),
        ],
    )
    def test_valid_bounds(self, kwargs: dict[str, int]) -> None:
        mr.str_meta(**kwargs)  # type: ignore[reportArgumentType]

    def test_regexp_int_raises(self) -> None:
        with pytest.raises(TypeError, match="regexp must be str, got int"):
            mr.str_meta(regexp=123)  # type: ignore[reportArgumentType]

    def test_regexp_bool_raises(self) -> None:
        with pytest.raises(TypeError, match="regexp must be str, got bool"):
            mr.str_meta(regexp=True)  # type: ignore[reportArgumentType]

    def test_invalid_regexp_raises(self) -> None:
        with pytest.raises(re.error):
            mr.str_meta(regexp="[invalid")
