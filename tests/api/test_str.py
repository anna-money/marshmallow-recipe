import marshmallow
import pytest

import marshmallow_recipe as mr

from .conftest import (
    OptionalValueOf,
    Serializer,
    ValueOf,
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

    def test_unicode(self, impl: Serializer) -> None:
        obj = ValueOf[str](value="Привет мир")
        result = impl.dump(ValueOf[str], obj)
        loaded = impl.load(ValueOf[str], result)
        assert loaded == ValueOf[str](value="Привет мир")

    def test_unicode_chinese(self, impl: Serializer) -> None:
        obj = ValueOf[str](value="你好世界")
        result = impl.dump(ValueOf[str], obj)
        loaded = impl.load(ValueOf[str], result)
        assert loaded == ValueOf[str](value="你好世界")

    def test_emoji(self, impl: Serializer) -> None:
        obj = ValueOf[str](value="Hello 👋 World 🌍")
        result = impl.dump(ValueOf[str], obj)
        loaded = impl.load(ValueOf[str], result)
        assert loaded == ValueOf[str](value="Hello 👋 World 🌍")

    def test_whitespace(self, impl: Serializer) -> None:
        obj = ValueOf[str](value="  spaces  ")
        result = impl.dump(ValueOf[str], obj)
        loaded = impl.load(ValueOf[str], result)
        assert loaded == ValueOf[str](value="  spaces  ")

    def test_special_chars(self, impl: Serializer) -> None:
        obj = ValueOf[str](value="Line1\nLine2\tTab\r\nNewline\"Quote'")
        dumped = impl.dump(ValueOf[str], obj)
        loaded = impl.load(ValueOf[str], dumped)
        assert loaded == ValueOf[str](value="Line1\nLine2\tTab\r\nNewline\"Quote'")

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

    # Metadata: strip whitespace
    def test_strip_whitespace(self, impl: Serializer) -> None:
        obj = WithStripWhitespace(name="  John  ", email="  test@example.com  ")
        result = impl.dump(WithStripWhitespace, obj)
        assert result == b'{"name":"John","email":"test@example.com"}'

    def test_strip_whitespace_already_clean(self, impl: Serializer) -> None:
        obj = WithStripWhitespace(name="Bob", email="bob@example.com")
        result = impl.dump(WithStripWhitespace, obj)
        assert result == b'{"name":"Bob","email":"bob@example.com"}'

    # Metadata: post_load
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

    def test_wrong_type_int(self, impl: Serializer) -> None:
        data = b'{"value":123}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[str], data)
        assert exc.value.messages == {"value": ["Not a valid string."]}

    def test_wrong_type_list(self, impl: Serializer) -> None:
        data = b'{"value":["a","b"]}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[str], data)
        assert exc.value.messages == {"value": ["Not a valid string."]}

    def test_wrong_type_object(self, impl: Serializer) -> None:
        data = b'{"value":{"key":"val"}}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[str], data)
        assert exc.value.messages == {"value": ["Not a valid string."]}

    def test_missing_required(self, impl: Serializer) -> None:
        data = b"{}"
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[str], data)
        assert exc.value.messages == {"value": ["Missing data for required field."]}

    # Metadata: strip whitespace
    def test_strip_whitespace(self, impl: Serializer) -> None:
        data = b'{"name":"  Alice  ","email":"  alice@example.com  "}'
        result = impl.load(WithStripWhitespace, data)
        assert result == WithStripWhitespace(name="Alice", email="alice@example.com")

    # Metadata: post_load
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


class TestStrDumpInvalidType:
    """Test that invalid types in str fields raise ValidationError on dump."""

    def test_int(self, impl: Serializer) -> None:
        obj = ValueOf[str](**{"value": 123})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(ValueOf[str], obj)

    def test_list(self, impl: Serializer) -> None:
        obj = ValueOf[str](**{"value": ["a", "b"]})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(ValueOf[str], obj)
