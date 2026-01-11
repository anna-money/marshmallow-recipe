import dataclasses
import json
from typing import NewType

import marshmallow
import pytest

from .conftest import (
    NewInt as ConfTestNewInt,
    Serializer,
    WithNewTypeMissing,
    WithNewTypeTwoValidators,
    WithNewTypeValidation,
)

NewInt = NewType("NewInt", int)
NewStr = NewType("NewStr", str)


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithNewType:
    int_value: NewInt
    str_value: NewStr


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithOptionalNewType:
    value: NewInt | None = None


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithNewTypeList:
    items: list[NewInt]


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithNewTypeDict:
    data: dict[str, NewInt]


class TestNewTypeDump:
    def test_value(self, impl: Serializer) -> None:
        obj = WithNewType(int_value=NewInt(42), str_value=NewStr("hello"))
        result = impl.dump(WithNewType, obj)
        assert result == b'{"int_value":42,"str_value":"hello"}'

    def test_optional_value(self, impl: Serializer) -> None:
        obj = WithOptionalNewType(value=NewInt(42))
        result = impl.dump(WithOptionalNewType, obj)
        assert result == b'{"value":42}'

    def test_optional_none(self, impl: Serializer) -> None:
        obj = WithOptionalNewType(value=None)
        result = impl.dump(WithOptionalNewType, obj)
        assert result == b"{}"

    def test_list(self, impl: Serializer) -> None:
        obj = WithNewTypeList(items=[NewInt(1), NewInt(2), NewInt(3)])
        result = impl.dump(WithNewTypeList, obj)
        assert result == b'{"items":[1,2,3]}'

    def test_dict(self, impl: Serializer) -> None:
        obj = WithNewTypeDict(data={"a": NewInt(1), "b": NewInt(2)})
        result = impl.dump(WithNewTypeDict, obj)
        assert result == b'{"data":{"a":1,"b":2}}'

    def test_empty_list(self, impl: Serializer) -> None:
        obj = WithNewTypeList(items=[])
        result = impl.dump(WithNewTypeList, obj)
        assert result == b'{"items":[]}'

    def test_empty_dict(self, impl: Serializer) -> None:
        obj = WithNewTypeDict(data={})
        result = impl.dump(WithNewTypeDict, obj)
        assert result == b'{"data":{}}'

    def test_large_list(self, impl: Serializer) -> None:
        items = [NewInt(i) for i in range(100)]
        obj = WithNewTypeList(items=items)
        result = impl.dump(WithNewTypeList, obj)
        parsed = json.loads(result)
        assert parsed["items"] == list(range(100))

    def test_missing(self, impl: Serializer) -> None:
        obj = WithNewTypeMissing()
        result = impl.dump(WithNewTypeMissing, obj)
        assert result == b"{}"

    def test_missing_with_value(self, impl: Serializer) -> None:
        obj = WithNewTypeMissing(value=ConfTestNewInt(42))
        result = impl.dump(WithNewTypeMissing, obj)
        assert result == b'{"value":42}'


class TestNewTypeLoad:
    def test_value(self, impl: Serializer) -> None:
        data = b'{"int_value":100,"str_value":"world"}'
        result = impl.load(WithNewType, data)
        assert result == WithNewType(int_value=NewInt(100), str_value=NewStr("world"))

    def test_optional_value(self, impl: Serializer) -> None:
        data = b'{"value":123}'
        result = impl.load(WithOptionalNewType, data)
        assert result == WithOptionalNewType(value=NewInt(123))

    def test_optional_missing(self, impl: Serializer) -> None:
        data = b"{}"
        result = impl.load(WithOptionalNewType, data)
        assert result == WithOptionalNewType(value=None)

    def test_list(self, impl: Serializer) -> None:
        data = b'{"items":[10,20,30]}'
        result = impl.load(WithNewTypeList, data)
        assert result == WithNewTypeList(items=[NewInt(10), NewInt(20), NewInt(30)])

    def test_dict(self, impl: Serializer) -> None:
        data = b'{"data":{"x":100,"y":200}}'
        result = impl.load(WithNewTypeDict, data)
        assert result == WithNewTypeDict(data={"x": NewInt(100), "y": NewInt(200)})

    def test_empty_list(self, impl: Serializer) -> None:
        data = b'{"items":[]}'
        result = impl.load(WithNewTypeList, data)
        assert result == WithNewTypeList(items=[])

    def test_empty_dict(self, impl: Serializer) -> None:
        data = b'{"data":{}}'
        result = impl.load(WithNewTypeDict, data)
        assert result == WithNewTypeDict(data={})

    def test_large_list(self, impl: Serializer) -> None:
        items = list(range(100))
        data = json.dumps({"items": items}).encode()
        result = impl.load(WithNewTypeList, data)
        assert result == WithNewTypeList(items=[NewInt(i) for i in range(100)])

    def test_validation_pass(self, impl: Serializer) -> None:
        data = b'{"value":10}'
        result = impl.load(WithNewTypeValidation, data)
        assert result == WithNewTypeValidation(value=ConfTestNewInt(10))

    def test_validation_fail(self, impl: Serializer) -> None:
        data = b'{"value":0}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithNewTypeValidation, data)
        assert exc.value.messages == {"value": ["Invalid value."]}

    def test_two_validators_pass(self, impl: Serializer) -> None:
        data = b'{"value":50}'
        result = impl.load(WithNewTypeTwoValidators, data)
        assert result == WithNewTypeTwoValidators(value=ConfTestNewInt(50))

    @pytest.mark.parametrize("data", [b'{"value":0}', b'{"value":150}'])
    def test_two_validators_fail(self, impl: Serializer, data: bytes) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithNewTypeTwoValidators, data)
        assert exc.value.messages == {"value": ["Invalid value."]}

    def test_missing(self, impl: Serializer) -> None:
        data = b"{}"
        result = impl.load(WithNewTypeMissing, data)
        assert result == WithNewTypeMissing()

    def test_missing_with_value(self, impl: Serializer) -> None:
        data = b'{"value":42}'
        result = impl.load(WithNewTypeMissing, data)
        assert result == WithNewTypeMissing(value=ConfTestNewInt(42))


class TestNewTypeEdgeCases:
    """Test NewType edge cases with boundary values, unicode, and nested collections."""

    def test_big_int_newtype(self, impl: Serializer) -> None:
        big_val = 9223372036854775808  # > int64 max
        obj = WithNewType(int_value=NewInt(big_val), str_value=NewStr("test"))
        result = impl.dump(WithNewType, obj)
        loaded = impl.load(WithNewType, result)
        assert loaded.int_value == big_val

    def test_very_big_int_newtype(self, impl: Serializer) -> None:
        very_big = 2**100
        obj = WithNewType(int_value=NewInt(very_big), str_value=NewStr("test"))
        result = impl.dump(WithNewType, obj)
        loaded = impl.load(WithNewType, result)
        assert loaded.int_value == very_big

    def test_negative_big_int_newtype(self, impl: Serializer) -> None:
        neg_big = -(2**63) - 1
        obj = WithNewType(int_value=NewInt(neg_big), str_value=NewStr("test"))
        result = impl.dump(WithNewType, obj)
        loaded = impl.load(WithNewType, result)
        assert loaded.int_value == neg_big

    def test_unicode_newstr(self, impl: Serializer) -> None:
        unicode_val = "Привет 你好 🎉 مرحبا"
        obj = WithNewType(int_value=NewInt(42), str_value=NewStr(unicode_val))
        result = impl.dump(WithNewType, obj)
        loaded = impl.load(WithNewType, result)
        assert loaded.str_value == unicode_val

    def test_special_chars_newstr(self, impl: Serializer) -> None:
        special_val = '"quoted" back\\slash new\nline tab\there'
        obj = WithNewType(int_value=NewInt(42), str_value=NewStr(special_val))
        result = impl.dump(WithNewType, obj)
        loaded = impl.load(WithNewType, result)
        assert loaded.str_value == special_val

    def test_empty_string_newstr(self, impl: Serializer) -> None:
        obj = WithNewType(int_value=NewInt(0), str_value=NewStr(""))
        result = impl.dump(WithNewType, obj)
        loaded = impl.load(WithNewType, result)
        assert loaded.str_value == ""

    def test_whitespace_newstr(self, impl: Serializer) -> None:
        obj = WithNewType(int_value=NewInt(0), str_value=NewStr("   \t\n   "))
        result = impl.dump(WithNewType, obj)
        loaded = impl.load(WithNewType, result)
        assert loaded.str_value == "   \t\n   "

    def test_list_with_big_ints(self, impl: Serializer) -> None:
        big_vals = [NewInt(2**63), NewInt(2**100), NewInt(-(2**63) - 1)]
        obj = WithNewTypeList(items=big_vals)
        result = impl.dump(WithNewTypeList, obj)
        loaded = impl.load(WithNewTypeList, result)
        assert loaded.items == [2**63, 2**100, -(2**63) - 1]

    def test_dict_with_big_ints(self, impl: Serializer) -> None:
        obj = WithNewTypeDict(data={"big": NewInt(2**100), "neg": NewInt(-(2**63))})
        result = impl.dump(WithNewTypeDict, obj)
        loaded = impl.load(WithNewTypeDict, result)
        assert loaded.data == {"big": 2**100, "neg": -(2**63)}

    def test_dict_with_unicode_keys(self, impl: Serializer) -> None:
        obj = WithNewTypeDict(data={"ключ": NewInt(1), "键": NewInt(2), "🔑": NewInt(3)})
        result = impl.dump(WithNewTypeDict, obj)
        loaded = impl.load(WithNewTypeDict, result)
        assert loaded.data == {"ключ": 1, "键": 2, "🔑": 3}

    def test_dict_with_empty_key(self, impl: Serializer) -> None:
        obj = WithNewTypeDict(data={"": NewInt(42), "a": NewInt(1)})
        result = impl.dump(WithNewTypeDict, obj)
        loaded = impl.load(WithNewTypeDict, result)
        assert loaded.data == {"": 42, "a": 1}

    def test_1000_element_list(self, impl: Serializer) -> None:
        items = [NewInt(i) for i in range(1000)]
        obj = WithNewTypeList(items=items)
        result = impl.dump(WithNewTypeList, obj)
        loaded = impl.load(WithNewTypeList, result)
        assert loaded.items == list(range(1000))

    def test_zero_value(self, impl: Serializer) -> None:
        obj = WithNewType(int_value=NewInt(0), str_value=NewStr("zero"))
        result = impl.dump(WithNewType, obj)
        loaded = impl.load(WithNewType, result)
        assert loaded.int_value == 0

    def test_int32_boundaries(self, impl: Serializer) -> None:
        int32_max = 2147483647
        int32_min = -2147483648
        obj = WithNewTypeList(items=[NewInt(int32_min), NewInt(int32_max)])
        result = impl.dump(WithNewTypeList, obj)
        loaded = impl.load(WithNewTypeList, result)
        assert loaded.items == [int32_min, int32_max]

    def test_int64_boundaries(self, impl: Serializer) -> None:
        int64_max = 9223372036854775807
        int64_min = -9223372036854775808
        obj = WithNewTypeList(items=[NewInt(int64_min), NewInt(int64_max)])
        result = impl.dump(WithNewTypeList, obj)
        loaded = impl.load(WithNewTypeList, result)
        assert loaded.items == [int64_min, int64_max]
