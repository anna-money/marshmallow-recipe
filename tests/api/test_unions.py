import pytest

from .conftest import (
    Serializer,
    WithUnion,
    WithUnionDictStr,
    WithUnionFloatInt,
    WithUnionIntFloat,
    WithUnionMissing,
    WithUnionStrDict,
    WithUnionStrInt,
)


class TestUnionDump:
    @pytest.mark.parametrize(("value", "expected"), [(42, b'{"value":42}'), ("hello", b'{"value":"hello"}')])
    def test_value(self, impl: Serializer, value: int | str, expected: bytes) -> None:
        obj = WithUnion(value=value, optional_value=None)
        result = impl.dump(WithUnion, obj)
        assert result == expected

    @pytest.mark.parametrize(
        ("value", "optional_value", "expected"),
        [
            ("x", 999, b'{"value":"x","optional_value":999}'),
            (1, "optional", b'{"value":1,"optional_value":"optional"}'),
        ],
    )
    def test_optional_with_value(
        self, impl: Serializer, value: int | str, optional_value: int | str, expected: bytes
    ) -> None:
        obj = WithUnion(value=value, optional_value=optional_value)
        result = impl.dump(WithUnion, obj)
        assert result == expected

    @pytest.mark.parametrize(("value", "expected"), [(13, b'{"value":13}'), (13.7, b'{"value":13.7}')])
    def test_int_float(self, impl: Serializer, value: int | float, expected: bytes) -> None:
        obj = WithUnionIntFloat(value=value)
        result = impl.dump(WithUnionIntFloat, obj)
        assert result == expected

    def test_float_int_with_int(self, impl: Serializer) -> None:
        obj = WithUnionFloatInt(value=13)
        result = impl.dump(WithUnionFloatInt, obj)
        assert result in (b'{"value":13}', b'{"value":13.0}')

    def test_float_int_with_float(self, impl: Serializer) -> None:
        obj = WithUnionFloatInt(value=13.7)
        result = impl.dump(WithUnionFloatInt, obj)
        assert result == b'{"value":13.7}'

    @pytest.mark.parametrize(
        ("value", "expected"), [("hello", b'{"value":"hello"}'), ({"key": "value"}, b'{"value":{"key":"value"}}')]
    )
    def test_str_dict(self, impl: Serializer, value: str | dict[str, str], expected: bytes) -> None:
        obj = WithUnionStrDict(value=value)
        result = impl.dump(WithUnionStrDict, obj)
        assert result == expected

    @pytest.mark.parametrize(
        ("value", "expected"), [("hello", b'{"value":"hello"}'), ({"key": "value"}, b'{"value":{"key":"value"}}')]
    )
    def test_dict_str(self, impl: Serializer, value: str | dict[str, str], expected: bytes) -> None:
        obj = WithUnionDictStr(value=value)
        result = impl.dump(WithUnionDictStr, obj)
        assert result == expected

    def test_missing(self, impl: Serializer) -> None:
        obj = WithUnionMissing()
        result = impl.dump(WithUnionMissing, obj)
        assert result == b"{}"

    @pytest.mark.parametrize(("value", "expected"), [(42, b'{"value":42}'), ("hello", b'{"value":"hello"}')])
    def test_missing_with_value(self, impl: Serializer, value: int | str, expected: bytes) -> None:
        obj = WithUnionMissing(value=value)
        result = impl.dump(WithUnionMissing, obj)
        assert result == expected


class TestUnionLoad:
    @pytest.mark.parametrize(("data", "expected_value"), [(b'{"value":100}', 100), (b'{"value":"test"}', "test")])
    def test_value(self, impl: Serializer, data: bytes, expected_value: int | str) -> None:
        result = impl.load(WithUnion, data)
        assert result == WithUnion(value=expected_value, optional_value=None)

    def test_zero_int(self, impl: Serializer) -> None:
        data = b'{"value":0}'
        result = impl.load(WithUnion, data)
        assert result.value == 0
        assert isinstance(result.value, int)

    def test_empty_string(self, impl: Serializer) -> None:
        data = b'{"value":""}'
        result = impl.load(WithUnion, data)
        assert result.value == ""

    def test_negative_int(self, impl: Serializer) -> None:
        data = b'{"value":-42}'
        result = impl.load(WithUnion, data)
        assert result.value == -42

    def test_whitespace_string(self, impl: Serializer) -> None:
        data = b'{"value":"   "}'
        result = impl.load(WithUnion, data)
        assert result.value == "   "

    @pytest.mark.parametrize(
        ("data", "expected_optional"),
        [(b'{"value":"x","optional_value":999}', 999), (b'{"value":1,"optional_value":"optional"}', "optional")],
    )
    def test_optional_with_value(self, impl: Serializer, data: bytes, expected_optional: int | str) -> None:
        result = impl.load(WithUnion, data)
        assert result.optional_value == expected_optional

    @pytest.mark.parametrize(
        ("data", "expected_value"),
        [(b'{"value": 9223372036854775808}', 9223372036854775808), (f'{{"value": {2**100}}}'.encode(), 2**100)],
    )
    def test_big_int(self, impl: Serializer, data: bytes, expected_value: int) -> None:
        result = impl.load(WithUnion, data)
        assert result == WithUnion(value=expected_value, optional_value=None)

    def test_optional_with_big_int(self, impl: Serializer) -> None:
        big_value = 18446744073709551616
        data = f'{{"value": "x", "optional_value": {big_value}}}'.encode()
        result = impl.load(WithUnion, data)
        assert result.optional_value == big_value

    def test_int_str_with_int(self, impl: Serializer) -> None:
        data = b'{"value":123}'
        result = impl.load(WithUnion, data)
        assert result.value == 123
        assert isinstance(result.value, int)

    def test_int_str_with_str_number(self, impl: Serializer) -> None:
        data = b'{"value":"123"}'
        result = impl.load(WithUnion, data)
        assert result.value in (123, "123")

    def test_int_str_with_str(self, impl: Serializer) -> None:
        data = b'{"value":"abc"}'
        result = impl.load(WithUnion, data)
        assert result.value == "abc"

    @pytest.mark.parametrize(("data", "expected_value"), [(b'{"value":123}', 123), (b'{"value":"hello"}', "hello")])
    def test_str_int(self, impl: Serializer, data: bytes, expected_value: int | str) -> None:
        result = impl.load(WithUnionStrInt, data)
        assert result.value == expected_value

    @pytest.mark.parametrize(("data", "expected_value"), [(b'{"value":13}', 13), (b'{"value":13.7}', 13.7)])
    def test_int_float(self, impl: Serializer, data: bytes, expected_value: int | float) -> None:
        result = impl.load(WithUnionIntFloat, data)
        assert result == WithUnionIntFloat(value=expected_value)

    @pytest.mark.parametrize(("data", "expected_value"), [(b'{"value":13}', 13), (b'{"value":13.7}', 13.7)])
    def test_float_int(self, impl: Serializer, data: bytes, expected_value: int | float) -> None:
        result = impl.load(WithUnionFloatInt, data)
        assert result == WithUnionFloatInt(value=expected_value)

    @pytest.mark.parametrize(
        ("data", "expected_value"), [(b'{"value":"hello"}', "hello"), (b'{"value":{"key":"value"}}', {"key": "value"})]
    )
    def test_str_dict(self, impl: Serializer, data: bytes, expected_value: str | dict[str, str]) -> None:
        result = impl.load(WithUnionStrDict, data)
        assert result == WithUnionStrDict(value=expected_value)

    @pytest.mark.parametrize(
        ("data", "expected_value"), [(b'{"value":"hello"}', "hello"), (b'{"value":{"key":"value"}}', {"key": "value"})]
    )
    def test_dict_str(self, impl: Serializer, data: bytes, expected_value: str | dict[str, str]) -> None:
        result = impl.load(WithUnionDictStr, data)
        assert result == WithUnionDictStr(value=expected_value)

    def test_missing(self, impl: Serializer) -> None:
        data = b"{}"
        result = impl.load(WithUnionMissing, data)
        assert result == WithUnionMissing()

    @pytest.mark.parametrize(("data", "expected_value"), [(b'{"value":42}', 42), (b'{"value":"hello"}', "hello")])
    def test_missing_with_value(self, impl: Serializer, data: bytes, expected_value: int | str) -> None:
        result = impl.load(WithUnionMissing, data)
        assert result == WithUnionMissing(value=expected_value)


class TestUnionEdgeCases:
    """Test union edge cases with boundary values and special scenarios."""

    def test_big_int_in_union(self, impl: Serializer) -> None:
        big_val = 9223372036854775808
        obj = WithUnion(value=big_val, optional_value=None)
        result = impl.dump(WithUnion, obj)
        loaded = impl.load(WithUnion, result)
        assert loaded.value == big_val

    def test_very_big_int_in_union(self, impl: Serializer) -> None:
        very_big = 2**100
        obj = WithUnion(value=very_big, optional_value=None)
        result = impl.dump(WithUnion, obj)
        loaded = impl.load(WithUnion, result)
        assert loaded.value == very_big

    def test_unicode_string_in_union(self, impl: Serializer) -> None:
        unicode_val = "Привет 你好 🎉"
        obj = WithUnion(value=unicode_val, optional_value=None)
        result = impl.dump(WithUnion, obj)
        loaded = impl.load(WithUnion, result)
        assert loaded.value == unicode_val

    def test_special_chars_string_in_union(self, impl: Serializer) -> None:
        special_val = '"quoted" back\\slash new\nline'
        obj = WithUnion(value=special_val, optional_value=None)
        result = impl.dump(WithUnion, obj)
        loaded = impl.load(WithUnion, result)
        assert loaded.value == special_val

    def test_both_fields_with_big_ints(self, impl: Serializer) -> None:
        obj = WithUnion(value=2**63, optional_value=2**64)
        result = impl.dump(WithUnion, obj)
        loaded = impl.load(WithUnion, result)
        assert loaded.value == 2**63
        assert loaded.optional_value == 2**64

    def test_int_str_union_boundary(self, impl: Serializer) -> None:
        data = b'{"value":"9223372036854775808"}'
        result = impl.load(WithUnion, data)
        assert result.value in (9223372036854775808, "9223372036854775808")

    def test_float_precision_in_int_float_union(self, impl: Serializer) -> None:
        obj = WithUnionIntFloat(value=1.7976931348623157e308)
        result = impl.dump(WithUnionIntFloat, obj)
        loaded = impl.load(WithUnionIntFloat, result)
        assert loaded.value == 1.7976931348623157e308

    def test_very_small_float_in_float_int_union(self, impl: Serializer) -> None:
        obj = WithUnionFloatInt(value=5e-324)
        result = impl.dump(WithUnionFloatInt, obj)
        loaded = impl.load(WithUnionFloatInt, result)
        assert loaded.value == 5e-324

    def test_dict_with_empty_key_in_str_dict_union(self, impl: Serializer) -> None:
        obj = WithUnionStrDict(value={"": "empty_key", "a": "value"})
        result = impl.dump(WithUnionStrDict, obj)
        loaded = impl.load(WithUnionStrDict, result)
        assert loaded.value == {"": "empty_key", "a": "value"}

    def test_empty_dict_in_dict_str_union(self, impl: Serializer) -> None:
        obj = WithUnionDictStr(value={})
        result = impl.dump(WithUnionDictStr, obj)
        loaded = impl.load(WithUnionDictStr, result)
        assert loaded.value == {}
