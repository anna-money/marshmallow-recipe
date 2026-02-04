import marshmallow
import pytest

from .conftest import (
    Inner,
    Serializer,
    WithUnion,
    WithUnionDictDataclass,
    WithUnionDictStr,
    WithUnionFloatInt,
    WithUnionIntFloat,
    WithUnionMissing,
    WithUnionStrDict,
    WithUnionStrInt,
)


class TestUnionDump:
    def test_int(self, impl: Serializer) -> None:
        obj = WithUnion(value=42, optional_value=None)
        result = impl.dump(WithUnion, obj)
        assert result == b'{"value":42}'

    def test_str(self, impl: Serializer) -> None:
        obj = WithUnion(value="hello", optional_value=None)
        result = impl.dump(WithUnion, obj)
        assert result == b'{"value":"hello"}'

    def test_optional_with_int(self, impl: Serializer) -> None:
        obj = WithUnion(value="x", optional_value=999)
        result = impl.dump(WithUnion, obj)
        assert result == b'{"value":"x","optional_value":999}'

    def test_optional_with_str(self, impl: Serializer) -> None:
        obj = WithUnion(value=1, optional_value="optional")
        result = impl.dump(WithUnion, obj)
        assert result == b'{"value":1,"optional_value":"optional"}'

    def test_int_float_with_int(self, impl: Serializer) -> None:
        obj = WithUnionIntFloat(value=13)
        result = impl.dump(WithUnionIntFloat, obj)
        assert result == b'{"value":13}'

    def test_int_float_with_float(self, impl: Serializer) -> None:
        obj = WithUnionIntFloat(value=13.7)
        result = impl.dump(WithUnionIntFloat, obj)
        assert result == b'{"value":13.7}'

    def test_float_int_with_int(self, impl: Serializer) -> None:
        obj = WithUnionFloatInt(value=13)
        result = impl.dump(WithUnionFloatInt, obj)
        assert result in (b'{"value":13}', b'{"value":13.0}')

    def test_float_int_with_float(self, impl: Serializer) -> None:
        obj = WithUnionFloatInt(value=13.7)
        result = impl.dump(WithUnionFloatInt, obj)
        assert result == b'{"value":13.7}'

    def test_str_dict_with_str(self, impl: Serializer) -> None:
        obj = WithUnionStrDict(value="hello")
        result = impl.dump(WithUnionStrDict, obj)
        assert result == b'{"value":"hello"}'

    def test_str_dict_with_dict(self, impl: Serializer) -> None:
        obj = WithUnionStrDict(value={"key": "value"})
        result = impl.dump(WithUnionStrDict, obj)
        assert result == b'{"value":{"key":"value"}}'

    def test_dict_str_with_str(self, impl: Serializer) -> None:
        obj = WithUnionDictStr(value="hello")
        result = impl.dump(WithUnionDictStr, obj)
        assert result == b'{"value":"hello"}'

    def test_dict_str_with_dict(self, impl: Serializer) -> None:
        obj = WithUnionDictStr(value={"key": "value"})
        result = impl.dump(WithUnionDictStr, obj)
        assert result == b'{"value":{"key":"value"}}'

    def test_missing(self, impl: Serializer) -> None:
        obj = WithUnionMissing()
        result = impl.dump(WithUnionMissing, obj)
        assert result == b"{}"

    def test_missing_with_int(self, impl: Serializer) -> None:
        obj = WithUnionMissing(value=42)
        result = impl.dump(WithUnionMissing, obj)
        assert result == b'{"value":42}'

    def test_missing_with_str(self, impl: Serializer) -> None:
        obj = WithUnionMissing(value="hello")
        result = impl.dump(WithUnionMissing, obj)
        assert result == b'{"value":"hello"}'


class TestUnionLoad:
    def test_int(self, impl: Serializer) -> None:
        data = b'{"value":100}'
        result = impl.load(WithUnion, data)
        assert result == WithUnion(value=100, optional_value=None)

    def test_str(self, impl: Serializer) -> None:
        data = b'{"value":"test"}'
        result = impl.load(WithUnion, data)
        assert result == WithUnion(value="test", optional_value=None)

    def test_optional_with_int(self, impl: Serializer) -> None:
        data = b'{"value":"x","optional_value":999}'
        result = impl.load(WithUnion, data)
        assert result == WithUnion(value="x", optional_value=999)

    def test_optional_with_str(self, impl: Serializer) -> None:
        data = b'{"value":1,"optional_value":"optional"}'
        result = impl.load(WithUnion, data)
        assert result == WithUnion(value=1, optional_value="optional")

    def test_big_int(self, impl: Serializer) -> None:
        big_value = 9223372036854775808
        data = f'{{"value": {big_value}}}'.encode()
        result = impl.load(WithUnion, data)
        assert result == WithUnion(value=big_value, optional_value=None)

    def test_very_large_int(self, impl: Serializer) -> None:
        very_large = 2**100
        data = f'{{"value": {very_large}}}'.encode()
        result = impl.load(WithUnion, data)
        assert result == WithUnion(value=very_large, optional_value=None)

    def test_optional_with_big_int(self, impl: Serializer) -> None:
        big_value = 18446744073709551616
        data = f'{{"value": "x", "optional_value": {big_value}}}'.encode()
        result = impl.load(WithUnion, data)
        assert result == WithUnion(value="x", optional_value=big_value)

    def test_int_str_with_int(self, impl: Serializer) -> None:
        data = b'{"value":123}'
        result = impl.load(WithUnion, data)
        assert result == WithUnion(value=123, optional_value=None)
        assert isinstance(result.value, int)

    def test_int_str_with_str_number(self, impl: Serializer) -> None:
        data = b'{"value":"123"}'
        result = impl.load(WithUnion, data)
        assert result.value in (123, "123")

    def test_int_str_with_str(self, impl: Serializer) -> None:
        data = b'{"value":"abc"}'
        result = impl.load(WithUnion, data)
        assert result == WithUnion(value="abc", optional_value=None)

    def test_str_int_with_int(self, impl: Serializer) -> None:
        data = b'{"value":123}'
        result = impl.load(WithUnionStrInt, data)
        assert result == WithUnionStrInt(value=123)

    def test_str_int_with_str(self, impl: Serializer) -> None:
        data = b'{"value":"hello"}'
        result = impl.load(WithUnionStrInt, data)
        assert result == WithUnionStrInt(value="hello")

    def test_int_float_with_int(self, impl: Serializer) -> None:
        data = b'{"value":13}'
        result = impl.load(WithUnionIntFloat, data)
        assert result == WithUnionIntFloat(value=13)

    def test_int_float_with_float(self, impl: Serializer) -> None:
        data = b'{"value":13.7}'
        result = impl.load(WithUnionIntFloat, data)
        assert result == WithUnionIntFloat(value=13.7)

    def test_float_int_with_int(self, impl: Serializer) -> None:
        data = b'{"value":13}'
        result = impl.load(WithUnionFloatInt, data)
        assert result == WithUnionFloatInt(value=13)

    def test_float_int_with_float(self, impl: Serializer) -> None:
        data = b'{"value":13.7}'
        result = impl.load(WithUnionFloatInt, data)
        assert result == WithUnionFloatInt(value=13.7)

    def test_str_dict_with_str(self, impl: Serializer) -> None:
        data = b'{"value":"hello"}'
        result = impl.load(WithUnionStrDict, data)
        assert result == WithUnionStrDict(value="hello")

    def test_str_dict_with_dict(self, impl: Serializer) -> None:
        data = b'{"value":{"key":"value"}}'
        result = impl.load(WithUnionStrDict, data)
        assert result == WithUnionStrDict(value={"key": "value"})

    def test_dict_str_with_str(self, impl: Serializer) -> None:
        data = b'{"value":"hello"}'
        result = impl.load(WithUnionDictStr, data)
        assert result == WithUnionDictStr(value="hello")

    def test_dict_str_with_dict(self, impl: Serializer) -> None:
        data = b'{"value":{"key":"value"}}'
        result = impl.load(WithUnionDictStr, data)
        assert result == WithUnionDictStr(value={"key": "value"})

    def test_missing(self, impl: Serializer) -> None:
        data = b"{}"
        result = impl.load(WithUnionMissing, data)
        assert result == WithUnionMissing()

    def test_missing_with_int(self, impl: Serializer) -> None:
        data = b'{"value":42}'
        result = impl.load(WithUnionMissing, data)
        assert result == WithUnionMissing(value=42)

    def test_missing_with_str(self, impl: Serializer) -> None:
        data = b'{"value":"hello"}'
        result = impl.load(WithUnionMissing, data)
        assert result == WithUnionMissing(value="hello")


class TestUnionErrors:
    def test_dict_variant_with_invalid_nested_value(self, impl: Serializer) -> None:
        data = b'{"value": {"key": {"x": "not_int"}}}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithUnionDictDataclass, data)
        assert exc.value.messages == {
            "value": [{"key": {"value": {"x": ["Not a valid integer."]}}}, ["Not a valid string."]]
        }

    def test_dict_variant_with_missing_nested_field(self, impl: Serializer) -> None:
        data = b'{"value": {"key": {}}}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithUnionDictDataclass, data)
        assert exc.value.messages == {
            "value": [{"key": {"value": {"x": ["Missing data for required field."]}}}, ["Not a valid string."]]
        }

    def test_valid_dict_variant(self, impl: Serializer) -> None:
        data = b'{"value": {"key": {"x": 42}}}'
        result = impl.load(WithUnionDictDataclass, data)
        assert result == WithUnionDictDataclass(value={"key": Inner(x=42)})

    def test_valid_str_variant(self, impl: Serializer) -> None:
        data = b'{"value": "hello"}'
        result = impl.load(WithUnionDictDataclass, data)
        assert result == WithUnionDictDataclass(value="hello")
