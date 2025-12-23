from dataclasses import dataclass, field

import pytest
from marshmallow import ValidationError

from marshmallow_recipe import v2


@dataclass
class SimpleTypes:
    name: str
    age: int
    score: float
    active: bool


def test_simple_types_dump() -> None:
    obj = SimpleTypes(name="John", age=30, score=9.5, active=True)
    result = v2.dump(SimpleTypes, obj)
    assert b'"name":"John"' in result
    assert b'"age":30' in result
    assert b'"score":9.5' in result
    assert b'"active":true' in result


def test_simple_types_load() -> None:
    data = b'{"name":"John","age":30,"score":9.5,"active":true}'
    result = v2.load(SimpleTypes, data)
    assert result == SimpleTypes(name="John", age=30, score=9.5, active=True)


def test_simple_types_roundtrip() -> None:
    obj = SimpleTypes(name="John", age=30, score=9.5, active=True)
    json_bytes = v2.dump(SimpleTypes, obj)
    loaded = v2.load(SimpleTypes, json_bytes)
    assert loaded == obj


@dataclass
class WithOptional:
    name: str
    nickname: str | None = None


def test_optional_none_ignored() -> None:
    obj = WithOptional(name="John")
    result = v2.dump(WithOptional, obj)
    assert b"nickname" not in result


def test_optional_none_included() -> None:
    obj = WithOptional(name="John")
    result = v2.dump(WithOptional, obj, none_value_handling="include")
    assert b'"nickname":null' in result


def test_optional_with_value() -> None:
    obj = WithOptional(name="John", nickname="Johnny")
    result = v2.dump(WithOptional, obj)
    assert b'"nickname":"Johnny"' in result


def test_optional_load_missing() -> None:
    data = b'{"name":"John"}'
    result = v2.load(WithOptional, data)
    assert result == WithOptional(name="John", nickname=None)


def test_optional_load_null() -> None:
    data = b'{"name":"John","nickname":null}'
    result = v2.load(WithOptional, data)
    assert result == WithOptional(name="John", nickname=None)


@dataclass
class WithList:
    tags: list[str]


def test_list_dump() -> None:
    obj = WithList(tags=["a", "b", "c"])
    result = v2.dump(WithList, obj)
    assert b'"tags":["a","b","c"]' in result


def test_list_load() -> None:
    data = b'{"tags":["a","b","c"]}'
    result = v2.load(WithList, data)
    assert result == WithList(tags=["a", "b", "c"])


def test_list_roundtrip() -> None:
    obj = WithList(tags=["x", "y", "z"])
    json_bytes = v2.dump(WithList, obj)
    loaded = v2.load(WithList, json_bytes)
    assert loaded == obj


@dataclass
class WithDict:
    scores: dict[str, int]


def test_dict_dump() -> None:
    obj = WithDict(scores={"x": 1, "y": 2})
    result = v2.dump(WithDict, obj)
    assert b'"scores":{' in result
    assert b'"x":1' in result
    assert b'"y":2' in result


def test_dict_load() -> None:
    data = b'{"scores":{"x":1,"y":2}}'
    result = v2.load(WithDict, data)
    assert result == WithDict(scores={"x": 1, "y": 2})


def test_dict_roundtrip() -> None:
    obj = WithDict(scores={"a": 10, "b": 20})
    json_bytes = v2.dump(WithDict, obj)
    loaded = v2.load(WithDict, json_bytes)
    assert loaded == obj


@dataclass
class Address:
    city: str
    country: str


@dataclass
class UserWithAddress:
    name: str
    address: Address


def test_nested_dump() -> None:
    obj = UserWithAddress(name="John", address=Address(city="NY", country="USA"))
    result = v2.dump(UserWithAddress, obj)
    assert b'"address":{' in result
    assert b'"city":"NY"' in result
    assert b'"country":"USA"' in result


def test_nested_load() -> None:
    data = b'{"name":"John","address":{"city":"NY","country":"USA"}}'
    result = v2.load(UserWithAddress, data)
    assert result == UserWithAddress(name="John", address=Address(city="NY", country="USA"))


def test_nested_roundtrip() -> None:
    obj = UserWithAddress(name="John", address=Address(city="NY", country="USA"))
    json_bytes = v2.dump(UserWithAddress, obj)
    loaded = v2.load(UserWithAddress, json_bytes)
    assert loaded == obj


@dataclass
class UserForNaming:
    user_name: str
    user_id: int


def _to_camel_case(name: str) -> str:
    parts = name.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


def test_naming_case_dump() -> None:
    obj = UserForNaming(user_name="John", user_id=123)
    result = v2.dump(UserForNaming, obj, naming_case=_to_camel_case)
    assert b'"userName":"John"' in result
    assert b'"userId":123' in result


def test_naming_case_load() -> None:
    data = b'{"userName":"John","userId":123}'
    result = v2.load(UserForNaming, data, naming_case=_to_camel_case)
    assert result == UserForNaming(user_name="John", user_id=123)


def test_naming_case_roundtrip() -> None:
    obj = UserForNaming(user_name="John", user_id=123)
    json_bytes = v2.dump(UserForNaming, obj, naming_case=_to_camel_case)
    loaded = v2.load(UserForNaming, json_bytes, naming_case=_to_camel_case)
    assert loaded == obj


def test_custom_naming_case() -> None:
    def custom_converter(name: str) -> str:
        if name == "user_id":
            return "id"
        return _to_camel_case(name)

    obj = UserForNaming(user_name="John", user_id=123)
    result = v2.dump(UserForNaming, obj, naming_case=custom_converter)
    assert b'"userName":"John"' in result
    assert b'"id":123' in result


@dataclass
class UserWithMetadata:
    name: str = field(metadata={"name": "userName"})
    age: int = field(metadata={"name": "userAge"})


def test_metadata_dump() -> None:
    obj = UserWithMetadata(name="John", age=30)
    result = v2.dump(UserWithMetadata, obj)
    assert b'"userName":"John"' in result
    assert b'"userAge":30' in result


def test_metadata_load() -> None:
    data = b'{"userName":"John","userAge":30}'
    result = v2.load(UserWithMetadata, data)
    assert result == UserWithMetadata(name="John", age=30)


def test_metadata_roundtrip() -> None:
    obj = UserWithMetadata(name="John", age=30)
    json_bytes = v2.dump(UserWithMetadata, obj)
    loaded = v2.load(UserWithMetadata, json_bytes)
    assert loaded == obj


@dataclass
class SimpleUser:
    name: str
    age: int


def test_dump_list_of_dataclasses() -> None:
    users = [SimpleUser("John", 30), SimpleUser("Jane", 25)]
    result = v2.dump(list[SimpleUser], users)
    assert result.startswith(b"[")
    assert result.endswith(b"]")
    assert b'"name":"John"' in result
    assert b'"name":"Jane"' in result


def test_load_list_of_dataclasses() -> None:
    data = b'[{"name":"John","age":30},{"name":"Jane","age":25}]'
    result = v2.load(list[SimpleUser], data)
    assert result == [SimpleUser("John", 30), SimpleUser("Jane", 25)]


def test_list_dataclass_roundtrip() -> None:
    users = [SimpleUser("John", 30), SimpleUser("Jane", 25)]
    json_bytes = v2.dump(list[SimpleUser], users)
    loaded = v2.load(list[SimpleUser], json_bytes)
    assert loaded == users


@dataclass
class ComplexType:
    name: str
    tags: list[str]
    scores: dict[str, int]
    address: Address | None = None


def test_complex_roundtrip() -> None:
    obj = ComplexType(
        name="John", tags=["dev", "py"], scores={"a": 10, "b": 20}, address=Address(city="NY", country="USA")
    )
    json_bytes = v2.dump(ComplexType, obj)
    loaded = v2.load(ComplexType, json_bytes)
    assert loaded == obj


def test_complex_without_optional() -> None:
    obj = ComplexType(name="John", tags=["dev"], scores={"x": 1})
    json_bytes = v2.dump(ComplexType, obj)
    loaded = v2.load(ComplexType, json_bytes)
    assert loaded == obj


def test_primitive_str() -> None:
    result = v2.dump(str, "hello")
    assert result == b'"hello"'
    assert v2.load(str, result) == "hello"


def test_primitive_int() -> None:
    result = v2.dump(int, 42)
    assert result == b"42"
    assert v2.load(int, result) == 42


def test_primitive_float() -> None:
    result = v2.dump(float, 3.14)
    assert result == b"3.14"
    assert v2.load(float, result) == 3.14


def test_primitive_bool() -> None:
    result = v2.dump(bool, True)
    assert result == b"true"
    assert v2.load(bool, result) is True


def test_list_of_primitives() -> None:
    result = v2.dump(list[str], ["a", "b", "c"])
    assert result == b'["a","b","c"]'
    assert v2.load(list[str], result) == ["a", "b", "c"]


def test_list_of_ints() -> None:
    result = v2.dump(list[int], [1, 2, 3])
    assert result == b"[1,2,3]"
    assert v2.load(list[int], result) == [1, 2, 3]


def test_dict_str_int() -> None:
    data = {"x": 1, "y": 2}
    result = v2.dump(dict[str, int], data)
    assert b'"x":1' in result
    assert b'"y":2' in result
    loaded = v2.load(dict[str, int], result)
    assert loaded == data


def test_optional_str_none() -> None:
    result = v2.dump(str | None, None)  # type: ignore[arg-type]
    assert result == b"null"
    assert v2.load(str | None, result) is None  # type: ignore[arg-type]


def test_optional_str_value() -> None:
    result = v2.dump(str | None, "hello")  # type: ignore[arg-type]
    assert result == b'"hello"'
    assert v2.load(str | None, result) == "hello"  # type: ignore[arg-type]


def test_nested_list() -> None:
    data = [["a", "b"], ["c", "d", "e"]]
    result = v2.dump(list[list[str]], data)
    assert result == b'[["a","b"],["c","d","e"]]'
    assert v2.load(list[list[str]], result) == data


def test_dict_with_dataclass_values() -> None:
    data = {"u1": SimpleUser("John", 30), "u2": SimpleUser("Jane", 25)}
    result = v2.dump(dict[str, SimpleUser], data)
    loaded = v2.load(dict[str, SimpleUser], result)
    assert loaded["u1"] == SimpleUser("John", 30)
    assert loaded["u2"] == SimpleUser("Jane", 25)


def test_missing_required_field_error() -> None:
    @dataclass
    class User:
        name: str
        age: int

    with pytest.raises(ValidationError) as exc:
        v2.load(User, b'{"age":30}')

    errors = exc.value.normalized_messages()
    assert errors == {"name": ["Missing data for required field."]}


def test_nested_missing_field_error() -> None:
    with pytest.raises(ValidationError) as exc:
        v2.load(UserWithAddress, b'{"name":"John","address":{"country":"USA"}}')

    errors = exc.value.normalized_messages()
    assert errors == {"address": {"city": ["Missing data for required field."]}}


def test_list_item_error() -> None:
    with pytest.raises(ValidationError) as exc:
        v2.load(list[SimpleUser], b'[{"name":"John","age":30},{"age":25}]')

    errors = exc.value.normalized_messages()
    assert errors == {"1": {"name": ["Missing data for required field."]}}


def test_dict_value_error() -> None:
    with pytest.raises(ValidationError) as exc:
        v2.load(dict[str, SimpleUser], b'{"u1":{"name":"John","age":30},"u2":{"age":25}}')

    errors = exc.value.normalized_messages()
    assert errors == {"u2": {"name": ["Missing data for required field."]}}
