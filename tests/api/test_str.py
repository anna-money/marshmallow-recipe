import marshmallow
import pytest

from .conftest import (
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
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            pytest.param("hello", b'{"value":"hello"}', id="simple"),
            pytest.param("", b'{"value":""}', id="empty"),
            pytest.param(" ", b'{"value":" "}', id="space"),
            pytest.param("a" * 10000, b'{"value":"' + b"a" * 10000 + b'"}', id="very_long"),
        ],
    )
    def test_values(self, impl: Serializer, value: str, expected: bytes) -> None:
        obj = ValueOf[str](value=value)
        result = impl.dump(ValueOf[str], obj)
        assert result == expected

    @pytest.mark.parametrize(
        ("value", "id_"),
        [
            pytest.param("Привет мир", "cyrillic"),
            pytest.param("你好世界", "chinese"),
            pytest.param("Hello 👋 World 🌍", "emoji"),
            pytest.param("  spaces  ", "spaces"),
            pytest.param("Line1\nLine2\tTab\r\nNewline\"Quote'", "escape_chars"),
            pytest.param("\x00\x01\x02", "control_chars"),
            pytest.param("\\n\\t\\r", "escaped_literals"),
            pytest.param('{"key": "value"}', "json_like"),
            pytest.param("<html>&amp;</html>", "html_entities"),
        ],
    )
    def test_roundtrip(self, impl: Serializer, value: str, id_: str) -> None:
        obj = ValueOf[str](value=value)
        result = impl.dump(ValueOf[str], obj)
        loaded = impl.load(ValueOf[str], result)
        assert loaded.value == value

    def test_default_provided(self, impl: Serializer) -> None:
        obj = WithStrDefault(value="custom")
        result = impl.dump(WithStrDefault, obj)
        assert result == b'{"value":"custom"}'

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
    @pytest.mark.parametrize(
        ("data", "expected"),
        [
            pytest.param(b'{"value":"hello"}', "hello", id="simple"),
            pytest.param(b'{"value":""}', "", id="empty"),
            pytest.param(b'{"value":" "}', " ", id="space"),
            pytest.param(b'{"value":"' + b"a" * 10000 + b'"}', "a" * 10000, id="very_long"),
        ],
    )
    def test_values(self, impl: Serializer, data: bytes, expected: str) -> None:
        result = impl.load(ValueOf[str], data)
        assert result == ValueOf[str](value=expected)

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

    @pytest.mark.parametrize("data", [b'{"value":""}', b'{"value":"' + b"x" * 150 + b'"}'])
    def test_two_validators_fail(self, impl: Serializer, data: bytes) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithStrTwoValidators, data)
        assert exc.value.messages == {"value": ["Invalid value."]}

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

    @pytest.mark.parametrize("data", [b'{"value":123}', b'{"value":["a","b"]}', b'{"value":{"key":"val"}}'])
    def test_wrong_type(self, impl: Serializer, data: bytes) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ValueOf[str], data)
        assert exc.value.messages == {"value": ["Not a valid string."]}

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


class TestStrEdgeCases:
    """Test string edge cases with boundary values and special characters."""

    @pytest.mark.parametrize(
        ("value", "id_"),
        [
            pytest.param("\x00", "null_byte"),
            pytest.param("\x00\x01\x02\x03", "control_chars_start"),
            pytest.param("\x1f\x7f", "control_chars_boundary"),
            pytest.param("before\x00after", "null_byte_middle"),
        ],
    )
    def test_null_byte_roundtrip(self, impl: Serializer, value: str, id_: str) -> None:
        obj = ValueOf[str](value=value)
        result = impl.dump(ValueOf[str], obj)
        loaded = impl.load(ValueOf[str], result)
        assert loaded.value == value

    @pytest.mark.parametrize(
        ("value", "id_"),
        [
            pytest.param("\U0001f600\U0001f601\U0001f602", "consecutive_emoji"),
            pytest.param("👨‍👩‍👧‍👦", "family_emoji_zwj"),
            pytest.param("🏳️‍🌈", "flag_emoji"),
            pytest.param("a\u0301", "combining_diacritical"),
            pytest.param("\u200b\u200c\u200d", "zero_width_chars"),
            pytest.param("\ufeff", "bom"),
        ],
    )
    def test_unicode_edge_cases(self, impl: Serializer, value: str, id_: str) -> None:
        obj = ValueOf[str](value=value)
        result = impl.dump(ValueOf[str], obj)
        loaded = impl.load(ValueOf[str], result)
        assert loaded.value == value

    @pytest.mark.parametrize(
        ("value", "id_"),
        [
            pytest.param("\\", "single_backslash"),
            pytest.param("\\\\", "double_backslash"),
            pytest.param('"', "double_quote"),
            pytest.param("\r\n", "crlf"),
            pytest.param("\r", "cr"),
            pytest.param("\n", "lf"),
            pytest.param("\t", "tab"),
            pytest.param("\\n\\t\\r", "escaped_literals"),
        ],
    )
    def test_escape_sequences(self, impl: Serializer, value: str, id_: str) -> None:
        obj = ValueOf[str](value=value)
        result = impl.dump(ValueOf[str], obj)
        loaded = impl.load(ValueOf[str], result)
        assert loaded.value == value

    def test_very_long_string_100k(self, impl: Serializer) -> None:
        value = "x" * 100000
        obj = ValueOf[str](value=value)
        result = impl.dump(ValueOf[str], obj)
        loaded = impl.load(ValueOf[str], result)
        assert loaded.value == value

    def test_all_ascii_printable(self, impl: Serializer) -> None:
        value = "".join(chr(i) for i in range(32, 127))
        obj = ValueOf[str](value=value)
        result = impl.dump(ValueOf[str], obj)
        loaded = impl.load(ValueOf[str], result)
        assert loaded.value == value


class TestStrDumpInvalidType:
    """Test that invalid types in str fields raise ValidationError on dump."""

    @pytest.mark.parametrize("value", [123, ["a", "b"]])
    def test_invalid_type(self, impl: Serializer, value: object) -> None:
        obj = ValueOf[str](**{"value": value})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(ValueOf[str], obj)
