import marshmallow
import pytest

import marshmallow_recipe as mr

from .conftest import (
    CatVariant,
    DogVariant,
    Inner,
    Serializer,
    StrDiscriminator,
    WithDiscriminatedUnion,
    WithUnion,
    WithUnionDictDataclass,
    WithUnionDictStr,
    WithUnionDictStrOptional,
    WithUnionFloatInt,
    WithUnionIntFloat,
    WithUnionIntStrOptional,
    WithUnionMissing,
    WithUnionStrDict,
    WithUnionStrDictOptional,
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

    def test_optional_with_none_include(self, impl: Serializer) -> None:
        obj = WithUnion(value=1, optional_value=None)
        result = impl.dump(WithUnion, obj, none_value_handling=mr.NoneValueHandling.INCLUDE)
        assert result == b'{"value":1,"optional_value":null}'

    @pytest.mark.parametrize(
        "cls, obj, expected",
        [
            pytest.param(
                WithUnionStrDictOptional,
                WithUnionStrDictOptional(value="hello"),
                b'{"value":"hello"}',
                id="str_dict-str",
            ),
            pytest.param(
                WithUnionStrDictOptional,
                WithUnionStrDictOptional(value={"key": "value"}),
                b'{"value":{"key":"value"}}',
                id="str_dict-dict",
            ),
            pytest.param(
                WithUnionDictStrOptional,
                WithUnionDictStrOptional(value="hello"),
                b'{"value":"hello"}',
                id="dict_str-str",
            ),
            pytest.param(
                WithUnionDictStrOptional,
                WithUnionDictStrOptional(value={"key": "value"}),
                b'{"value":{"key":"value"}}',
                id="dict_str-dict",
            ),
            pytest.param(WithUnionIntStrOptional, WithUnionIntStrOptional(value=42), b'{"value":42}', id="int_str-int"),
            pytest.param(
                WithUnionIntStrOptional, WithUnionIntStrOptional(value="hello"), b'{"value":"hello"}', id="int_str-str"
            ),
        ],
    )
    def test_optional_union_with_value(self, impl: Serializer, cls: type, obj: object, expected: bytes) -> None:
        result = impl.dump(cls, obj)
        assert result == expected

    @pytest.mark.parametrize(
        "cls, obj",
        [
            pytest.param(WithUnionStrDictOptional, WithUnionStrDictOptional(value=None), id="str_dict"),
            pytest.param(WithUnionDictStrOptional, WithUnionDictStrOptional(value=None), id="dict_str"),
            pytest.param(WithUnionIntStrOptional, WithUnionIntStrOptional(value=None), id="int_str"),
        ],
    )
    def test_optional_union_with_none(self, impl: Serializer, cls: type, obj: object) -> None:
        result = impl.dump(cls, obj)
        assert result == b"{}"

    @pytest.mark.parametrize(
        "cls, obj",
        [
            pytest.param(WithUnionStrDictOptional, WithUnionStrDictOptional(value=None), id="str_dict"),
            pytest.param(WithUnionDictStrOptional, WithUnionDictStrOptional(value=None), id="dict_str"),
            pytest.param(WithUnionIntStrOptional, WithUnionIntStrOptional(value=None), id="int_str"),
        ],
    )
    def test_optional_union_with_none_include(self, impl: Serializer, cls: type, obj: object) -> None:
        result = impl.dump(cls, obj, none_value_handling=mr.NoneValueHandling.INCLUDE)
        assert result == b'{"value":null}'


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

    def test_optional_with_null(self, impl: Serializer) -> None:
        data = b'{"value":1,"optional_value":null}'
        result = impl.load(WithUnion, data)
        assert result == WithUnion(value=1, optional_value=None)

    @pytest.mark.parametrize(
        "cls, data, expected",
        [
            pytest.param(
                WithUnionStrDictOptional,
                b'{"value":"hello"}',
                WithUnionStrDictOptional(value="hello"),
                id="str_dict-str",
            ),
            pytest.param(
                WithUnionStrDictOptional,
                b'{"value":{"key":"value"}}',
                WithUnionStrDictOptional(value={"key": "value"}),
                id="str_dict-dict",
            ),
            pytest.param(
                WithUnionDictStrOptional,
                b'{"value":"hello"}',
                WithUnionDictStrOptional(value="hello"),
                id="dict_str-str",
            ),
            pytest.param(
                WithUnionDictStrOptional,
                b'{"value":{"key":"value"}}',
                WithUnionDictStrOptional(value={"key": "value"}),
                id="dict_str-dict",
            ),
            pytest.param(WithUnionIntStrOptional, b'{"value":42}', WithUnionIntStrOptional(value=42), id="int_str-int"),
            pytest.param(
                WithUnionIntStrOptional, b'{"value":"hello"}', WithUnionIntStrOptional(value="hello"), id="int_str-str"
            ),
        ],
    )
    def test_optional_union_with_value(self, impl: Serializer, cls: type, data: bytes, expected: object) -> None:
        result = impl.load(cls, data)
        assert result == expected

    @pytest.mark.parametrize(
        "cls, expected",
        [
            pytest.param(WithUnionStrDictOptional, WithUnionStrDictOptional(value=None), id="str_dict"),
            pytest.param(WithUnionDictStrOptional, WithUnionDictStrOptional(value=None), id="dict_str"),
            pytest.param(WithUnionIntStrOptional, WithUnionIntStrOptional(value=None), id="int_str"),
        ],
    )
    def test_optional_union_with_null(self, impl: Serializer, cls: type, expected: object) -> None:
        data = b'{"value":null}'
        result = impl.load(cls, data)
        assert result == expected


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


class TestStrEnumLiteralDiscriminatedUnion:
    def test_load_dog_variant(self, impl: Serializer) -> None:
        data = b'{"field":{"disc":"DOG","value":42}}'
        result = impl.load(WithDiscriminatedUnion, data)
        assert result == WithDiscriminatedUnion(field=DogVariant(disc=StrDiscriminator.DOG, value=42))
        assert result.field.disc is StrDiscriminator.DOG

    def test_load_cat_variant(self, impl: Serializer) -> None:
        data = b'{"field":{"disc":"CAT","value":"lol"}}'
        result = impl.load(WithDiscriminatedUnion, data)
        assert result == WithDiscriminatedUnion(field=CatVariant(disc=StrDiscriminator.CAT, value="lol"))
        assert result.field.disc is StrDiscriminator.CAT

    def test_load_unknown_discriminator(self, impl: Serializer) -> None:
        data = b'{"field":{"disc":"BIRD","value":1}}'
        with pytest.raises(marshmallow.ValidationError):
            impl.load(WithDiscriminatedUnion, data)

    def test_dump_dog_variant(self, impl: Serializer) -> None:
        obj = WithDiscriminatedUnion(field=DogVariant(disc=StrDiscriminator.DOG, value=42))
        result = impl.dump(WithDiscriminatedUnion, obj)
        assert result == b'{"field":{"disc":"DOG","value":42}}'

    def test_dump_cat_variant(self, impl: Serializer) -> None:
        obj = WithDiscriminatedUnion(field=CatVariant(disc=StrDiscriminator.CAT, value="lol"))
        result = impl.dump(WithDiscriminatedUnion, obj)
        assert result == b'{"field":{"disc":"CAT","value":"lol"}}'

    def test_round_trip(self, impl: Serializer) -> None:
        original = WithDiscriminatedUnion(field=CatVariant(disc=StrDiscriminator.CAT, value="lol"))
        dumped = impl.dump(WithDiscriminatedUnion, original)
        loaded = impl.load(WithDiscriminatedUnion, dumped)
        assert loaded == original
        assert loaded.field.disc is StrDiscriminator.CAT
