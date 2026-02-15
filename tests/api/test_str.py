import dataclasses
import re
from typing import Any

import marshmallow
import pytest

import marshmallow_recipe as mr

from .conftest import (
    OptionalValueOf,
    Serializer,
    ValueOf,
    WithOptionalStrStripWhitespace,
    WithPostLoadAndStrip,
    WithPostLoadTransform,
    WithStrDefault,
    WithStrInvalidError,
    WithStripWhitespace,
    WithStrMissing,
    WithStrNoneError,
    WithStrRequiredError,
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
        ("meta", "value", "expected"),
        [
            pytest.param(mr.str_meta(min_length=3), "abc", b'{"value":"abc"}', id="min_length"),
            pytest.param(mr.str_meta(max_length=5), "hello", b'{"value":"hello"}', id="max_length"),
            pytest.param(mr.str_meta(regexp=r"^\d+$"), "12345", b'{"value":"12345"}', id="regexp"),
            pytest.param(
                mr.str_meta(min_length=2, max_length=10, regexp=r"^[a-z]+$"),
                "hello",
                b'{"value":"hello"}',
                id="combined",
            ),
        ],
    )
    def test_validator_pass(self, impl: Serializer, meta: dict, value: str, expected: bytes) -> None:
        @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
        class DC:
            value: str = dataclasses.field(metadata=meta)

        result = impl.dump(DC, DC(value=value))
        assert result == expected

    @pytest.mark.parametrize(
        ("meta", "value", "expected_messages"),
        [
            pytest.param(mr.str_meta(min_length=3), "ab", {"value": ["Length must be at least 3."]}, id="min_length"),
            pytest.param(
                mr.str_meta(max_length=5), "toolong", {"value": ["Length must be at most 5."]}, id="max_length"
            ),
            pytest.param(
                mr.str_meta(regexp=r"^\d+$"), "abc", {"value": ["String does not match expected pattern."]}, id="regexp"
            ),
        ],
    )
    def test_validator_fail(self, impl: Serializer, meta: dict, value: str, expected_messages: dict) -> None:
        if not impl.supports_proper_validation_errors_on_dump:
            return

        @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
        class DC:
            value: str = dataclasses.field(metadata=meta)

        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.dump(DC, DC(value=value))
        assert exc.value.messages == expected_messages

    @pytest.mark.parametrize(
        ("meta", "value", "expected_messages"),
        [
            pytest.param(
                mr.str_meta(min_length=3, min_length_error="Too short"), "ab", {"value": ["Too short"]}, id="min_length"
            ),
            pytest.param(
                mr.str_meta(max_length=5, max_length_error="Too long"),
                "toolong",
                {"value": ["Too long"]},
                id="max_length",
            ),
            pytest.param(
                mr.str_meta(regexp=r"^\d+$", regexp_error="Must be digits"),
                "abc",
                {"value": ["Must be digits"]},
                id="regexp",
            ),
            pytest.param(
                mr.str_meta(min_length=3, min_length_error="At least {min} chars"),
                "ab",
                {"value": ["At least 3 chars"]},
                id="min_length_interpolated",
            ),
            pytest.param(
                mr.str_meta(max_length=5, max_length_error="At most {max} chars"),
                "toolong",
                {"value": ["At most 5 chars"]},
                id="max_length_interpolated",
            ),
        ],
    )
    def test_validator_custom_error(self, impl: Serializer, meta: dict, value: str, expected_messages: dict) -> None:
        if not impl.supports_proper_validation_errors_on_dump:
            return

        @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
        class DC:
            value: str = dataclasses.field(metadata=meta)

        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.dump(DC, DC(value=value))
        assert exc.value.messages == expected_messages

    def test_validators_with_strip(self, impl: Serializer) -> None:
        @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
        class DC:
            value: str = dataclasses.field(metadata=mr.str_meta(strip_whitespaces=True, min_length=2, max_length=10))

        result = impl.dump(DC, DC(value="  hello  "))
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

    def test_missing(self, impl: Serializer) -> None:
        data = b"{}"
        result = impl.load(WithStrMissing, data)
        assert result == WithStrMissing()

    def test_missing_with_value(self, impl: Serializer) -> None:
        data = b'{"value":"hello"}'
        result = impl.load(WithStrMissing, data)
        assert result == WithStrMissing(value="hello")

    @pytest.mark.parametrize(
        ("meta", "value"),
        [
            pytest.param(mr.str_meta(min_length=3), "abc", id="min_length"),
            pytest.param(mr.str_meta(max_length=5), "hello", id="max_length"),
            pytest.param(mr.str_meta(regexp=r"^\d+$"), "12345", id="regexp"),
            pytest.param(mr.str_meta(min_length=2, max_length=10, regexp=r"^[a-z]+$"), "hello", id="combined"),
        ],
    )
    def test_validator_pass(self, impl: Serializer, meta: dict, value: str) -> None:
        @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
        class DC:
            value: str = dataclasses.field(metadata=meta)

        data = b'{"value":"' + value.encode() + b'"}'
        result = impl.load(DC, data)
        assert result == DC(value=value)

    @pytest.mark.parametrize(
        ("meta", "value", "expected_messages"),
        [
            pytest.param(mr.str_meta(min_length=3), "ab", {"value": ["Length must be at least 3."]}, id="min_length"),
            pytest.param(
                mr.str_meta(max_length=5), "toolong", {"value": ["Length must be at most 5."]}, id="max_length"
            ),
            pytest.param(
                mr.str_meta(regexp=r"^\d+$"), "abc", {"value": ["String does not match expected pattern."]}, id="regexp"
            ),
        ],
    )
    def test_validator_fail(self, impl: Serializer, meta: dict, value: str, expected_messages: dict) -> None:
        @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
        class DC:
            value: str = dataclasses.field(metadata=meta)

        data = b'{"value":"' + value.encode() + b'"}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(DC, data)
        assert exc.value.messages == expected_messages

    @pytest.mark.parametrize(
        ("meta", "value", "expected_messages"),
        [
            pytest.param(
                mr.str_meta(min_length=3, min_length_error="Too short"), "ab", {"value": ["Too short"]}, id="min_length"
            ),
            pytest.param(
                mr.str_meta(max_length=5, max_length_error="Too long"),
                "toolong",
                {"value": ["Too long"]},
                id="max_length",
            ),
            pytest.param(
                mr.str_meta(regexp=r"^\d+$", regexp_error="Must be digits"),
                "abc",
                {"value": ["Must be digits"]},
                id="regexp",
            ),
            pytest.param(
                mr.str_meta(min_length=3, min_length_error="At least {min} chars"),
                "ab",
                {"value": ["At least 3 chars"]},
                id="min_length_interpolated",
            ),
            pytest.param(
                mr.str_meta(max_length=5, max_length_error="At most {max} chars"),
                "toolong",
                {"value": ["At most 5 chars"]},
                id="max_length_interpolated",
            ),
        ],
    )
    def test_validator_custom_error(self, impl: Serializer, meta: dict, value: str, expected_messages: dict) -> None:
        @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
        class DC:
            value: str = dataclasses.field(metadata=meta)

        data = b'{"value":"' + value.encode() + b'"}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(DC, data)
        assert exc.value.messages == expected_messages

    @pytest.mark.parametrize(
        ("meta", "value", "expected_messages"),
        [
            pytest.param(
                mr.str_meta(min_length=2, max_length=10, regexp=r"^[a-z]+$"),
                "a",
                {"value": ["Length must be at least 2."]},
                id="min_length",
            ),
            pytest.param(
                mr.str_meta(min_length=2, max_length=10, regexp=r"^[a-z]+$"),
                "abcdefghijk",
                {"value": ["Length must be at most 10."]},
                id="max_length",
            ),
            pytest.param(
                mr.str_meta(min_length=2, max_length=10, regexp=r"^[a-z]+$"),
                "HELLO",
                {"value": ["String does not match expected pattern."]},
                id="regexp",
            ),
        ],
    )
    def test_combined_validators_fail(self, impl: Serializer, meta: dict, value: str, expected_messages: dict) -> None:
        @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
        class DC:
            value: str = dataclasses.field(metadata=meta)

        data = b'{"value":"' + value.encode() + b'"}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(DC, data)
        assert exc.value.messages == expected_messages

    def test_validators_with_strip_pass(self, impl: Serializer) -> None:
        @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
        class DC:
            value: str = dataclasses.field(metadata=mr.str_meta(strip_whitespaces=True, min_length=2, max_length=10))

        data = b'{"value":"  hello  "}'
        result = impl.load(DC, data)
        assert result == DC(value="hello")

    def test_validators_with_strip_fail(self, impl: Serializer) -> None:
        @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
        class DC:
            value: str = dataclasses.field(metadata=mr.str_meta(strip_whitespaces=True, min_length=2, max_length=10))

        data = b'{"value":"  a  "}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(DC, data)
        assert exc.value.messages == {"value": ["Length must be at least 2."]}


class TestStrMetadata:
    @pytest.mark.parametrize(
        ("kwargs", "match"),
        [
            pytest.param(
                {"min_length": -1}, "min_length must be a non-negative integer, got -1", id="negative_min_length"
            ),
            pytest.param(
                {"max_length": -3}, "max_length must be a non-negative integer, got -3", id="negative_max_length"
            ),
            pytest.param(
                {"min_length": 10, "max_length": 5},
                r"min_length \(10\) must be less than or equal to max_length \(5\)",
                id="min_greater_than_max",
            ),
        ],
    )
    def test_invalid_args(self, kwargs: dict, match: str) -> None:
        with pytest.raises(ValueError, match=match):
            mr.str_meta(**kwargs)

    def test_invalid_regexp(self, impl: Serializer) -> None:
        @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
        class WithInvalidRegexp:
            value: str = dataclasses.field(metadata=mr.str_meta(regexp="[invalid"))

        with pytest.raises((re.error, ValueError)):
            impl.load(WithInvalidRegexp, b'{"value":"test"}')

    @pytest.mark.parametrize(
        "params",
        [
            pytest.param({"min_length": 0}, id="zero_min_length"),
            pytest.param({"max_length": 0}, id="zero_max_length"),
            pytest.param({"min_length": 5, "max_length": 5}, id="equal_min_max"),
        ],
    )
    def test_valid_args(self, params: dict[str, Any]) -> None:
        mr.str_meta(**params)
