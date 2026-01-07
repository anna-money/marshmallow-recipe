import dataclasses
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

    def test_two_validators_first_fails(self, impl: Serializer) -> None:
        data = b'{"value":0}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithNewTypeTwoValidators, data)
        assert exc.value.messages == {"value": ["Invalid value."]}

    def test_two_validators_second_fails(self, impl: Serializer) -> None:
        data = b'{"value":150}'
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
