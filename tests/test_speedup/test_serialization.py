import datetime
import enum
import json
import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Annotated

import pytest
from marshmallow import ValidationError

from marshmallow_recipe import speedup


@dataclass
class SimpleTypes:
    name: str
    age: int
    score: float
    active: bool


def test_simple_types_dump() -> None:
    obj = SimpleTypes(name="John", age=30, score=9.5, active=True)
    result = speedup.dump(SimpleTypes, obj)
    assert result == b'{"active":true,"age":30,"name":"John","score":9.5}'


def test_simple_types_load() -> None:
    data = b'{"name":"John","age":30,"score":9.5,"active":true}'
    result = speedup.load(SimpleTypes, data)
    assert result == SimpleTypes(name="John", age=30, score=9.5, active=True)


def test_simple_types_roundtrip() -> None:
    obj = SimpleTypes(name="John", age=30, score=9.5, active=True)
    json_bytes = speedup.dump(SimpleTypes, obj)
    loaded = speedup.load(SimpleTypes, json_bytes)
    assert loaded == obj


@dataclass
class WithOptional:
    name: str
    nickname: str | None = None


def test_optional_none_ignored() -> None:
    obj = WithOptional(name="John")
    result = speedup.dump(WithOptional, obj)
    assert result == b'{"name":"John"}'


def test_optional_none_included() -> None:
    obj = WithOptional(name="John")
    result = speedup.dump(WithOptional, obj, none_value_handling="include")
    assert result == b'{"name":"John","nickname":null}'


def test_optional_with_value() -> None:
    obj = WithOptional(name="John", nickname="Johnny")
    result = speedup.dump(WithOptional, obj)
    assert result == b'{"name":"John","nickname":"Johnny"}'


def test_optional_load_missing() -> None:
    data = b'{"name":"John"}'
    result = speedup.load(WithOptional, data)
    assert result == WithOptional(name="John", nickname=None)


def test_optional_load_null() -> None:
    data = b'{"name":"John","nickname":null}'
    result = speedup.load(WithOptional, data)
    assert result == WithOptional(name="John", nickname=None)


@dataclass
class WithList:
    tags: list[str]


def test_list_dump() -> None:
    obj = WithList(tags=["a", "b", "c"])
    result = speedup.dump(WithList, obj)
    assert result == b'{"tags":["a","b","c"]}'


def test_list_load() -> None:
    data = b'{"tags":["a","b","c"]}'
    result = speedup.load(WithList, data)
    assert result == WithList(tags=["a", "b", "c"])


def test_list_roundtrip() -> None:
    obj = WithList(tags=["x", "y", "z"])
    json_bytes = speedup.dump(WithList, obj)
    loaded = speedup.load(WithList, json_bytes)
    assert loaded == obj


@dataclass
class WithDict:
    scores: dict[str, int]


def test_dict_dump() -> None:
    obj = WithDict(scores={"x": 1, "y": 2})
    result = speedup.dump(WithDict, obj)
    assert result == b'{"scores":{"x":1,"y":2}}'


def test_dict_load() -> None:
    data = b'{"scores":{"x":1,"y":2}}'
    result = speedup.load(WithDict, data)
    assert result == WithDict(scores={"x": 1, "y": 2})


def test_dict_roundtrip() -> None:
    obj = WithDict(scores={"a": 10, "b": 20})
    json_bytes = speedup.dump(WithDict, obj)
    loaded = speedup.load(WithDict, json_bytes)
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
    result = speedup.dump(UserWithAddress, obj)
    assert result == b'{"address":{"city":"NY","country":"USA"},"name":"John"}'


def test_nested_load() -> None:
    data = b'{"name":"John","address":{"city":"NY","country":"USA"}}'
    result = speedup.load(UserWithAddress, data)
    assert result == UserWithAddress(name="John", address=Address(city="NY", country="USA"))


def test_nested_roundtrip() -> None:
    obj = UserWithAddress(name="John", address=Address(city="NY", country="USA"))
    json_bytes = speedup.dump(UserWithAddress, obj)
    loaded = speedup.load(UserWithAddress, json_bytes)
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
    result = speedup.dump(UserForNaming, obj, naming_case=_to_camel_case)
    assert result == b'{"userId":123,"userName":"John"}'


def test_naming_case_load() -> None:
    data = b'{"userName":"John","userId":123}'
    result = speedup.load(UserForNaming, data, naming_case=_to_camel_case)
    assert result == UserForNaming(user_name="John", user_id=123)


def test_naming_case_roundtrip() -> None:
    obj = UserForNaming(user_name="John", user_id=123)
    json_bytes = speedup.dump(UserForNaming, obj, naming_case=_to_camel_case)
    loaded = speedup.load(UserForNaming, json_bytes, naming_case=_to_camel_case)
    assert loaded == obj


def test_custom_naming_case() -> None:
    def custom_converter(name: str) -> str:
        if name == "user_id":
            return "id"
        return _to_camel_case(name)

    obj = UserForNaming(user_name="John", user_id=123)
    result = speedup.dump(UserForNaming, obj, naming_case=custom_converter)
    assert result == b'{"id":123,"userName":"John"}'


@dataclass
class UserWithMetadata:
    name: str = field(metadata={"name": "userName"})
    age: int = field(metadata={"name": "userAge"})


def test_metadata_dump() -> None:
    obj = UserWithMetadata(name="John", age=30)
    result = speedup.dump(UserWithMetadata, obj)
    assert result == b'{"userAge":30,"userName":"John"}'


def test_metadata_load() -> None:
    data = b'{"userName":"John","userAge":30}'
    result = speedup.load(UserWithMetadata, data)
    assert result == UserWithMetadata(name="John", age=30)


def test_metadata_roundtrip() -> None:
    obj = UserWithMetadata(name="John", age=30)
    json_bytes = speedup.dump(UserWithMetadata, obj)
    loaded = speedup.load(UserWithMetadata, json_bytes)
    assert loaded == obj


@dataclass
class SimpleUser:
    name: str
    age: int


def test_dump_list_of_dataclasses() -> None:
    users = [SimpleUser("John", 30), SimpleUser("Jane", 25)]
    result = speedup.dump(list[SimpleUser], users)
    assert result == b'[{"age":30,"name":"John"},{"age":25,"name":"Jane"}]'


def test_load_list_of_dataclasses() -> None:
    data = b'[{"name":"John","age":30},{"name":"Jane","age":25}]'
    result = speedup.load(list[SimpleUser], data)
    assert result == [SimpleUser("John", 30), SimpleUser("Jane", 25)]


def test_list_dataclass_roundtrip() -> None:
    users = [SimpleUser("John", 30), SimpleUser("Jane", 25)]
    json_bytes = speedup.dump(list[SimpleUser], users)
    loaded = speedup.load(list[SimpleUser], json_bytes)
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
    json_bytes = speedup.dump(ComplexType, obj)
    loaded = speedup.load(ComplexType, json_bytes)
    assert loaded == obj


def test_complex_without_optional() -> None:
    obj = ComplexType(name="John", tags=["dev"], scores={"x": 1})
    json_bytes = speedup.dump(ComplexType, obj)
    loaded = speedup.load(ComplexType, json_bytes)
    assert loaded == obj


def test_primitive_str() -> None:
    result = speedup.dump(str, "hello")
    assert result == b'"hello"'
    assert speedup.load(str, result) == "hello"


def test_primitive_int() -> None:
    result = speedup.dump(int, 42)
    assert result == b"42"
    assert speedup.load(int, result) == 42


def test_primitive_float() -> None:
    result = speedup.dump(float, 3.14)
    assert result == b"3.14"
    assert speedup.load(float, result) == 3.14


def test_primitive_bool() -> None:
    result = speedup.dump(bool, True)
    assert result == b"true"
    assert speedup.load(bool, result) is True


def test_list_of_primitives() -> None:
    result = speedup.dump(list[str], ["a", "b", "c"])
    assert result == b'["a","b","c"]'
    assert speedup.load(list[str], result) == ["a", "b", "c"]


def test_list_of_ints() -> None:
    result = speedup.dump(list[int], [1, 2, 3])
    assert result == b"[1,2,3]"
    assert speedup.load(list[int], result) == [1, 2, 3]


def test_dict_str_int() -> None:
    data = {"x": 1, "y": 2}
    result = speedup.dump(dict[str, int], data)
    assert result == b'{"x":1,"y":2}'
    assert speedup.load(dict[str, int], result) == data


def test_optional_str_none() -> None:
    result = speedup.dump(str | None, None)  # type: ignore[arg-type]
    assert result == b"null"
    assert speedup.load(str | None, result) is None  # type: ignore[arg-type]


def test_optional_str_value() -> None:
    result = speedup.dump(str | None, "hello")  # type: ignore[arg-type]
    assert result == b'"hello"'
    assert speedup.load(str | None, result) == "hello"  # type: ignore[arg-type]


def test_nested_list() -> None:
    data = [["a", "b"], ["c", "d", "e"]]
    result = speedup.dump(list[list[str]], data)
    assert result == b'[["a","b"],["c","d","e"]]'
    assert speedup.load(list[list[str]], result) == data


def test_dict_with_dataclass_values() -> None:
    data = {"u1": SimpleUser("John", 30), "u2": SimpleUser("Jane", 25)}
    result = speedup.dump(dict[str, SimpleUser], data)
    assert result == b'{"u1":{"age":30,"name":"John"},"u2":{"age":25,"name":"Jane"}}'
    assert speedup.load(dict[str, SimpleUser], result) == data


def test_missing_required_field_error() -> None:
    @dataclass
    class User:
        name: str
        age: int

    with pytest.raises(ValidationError) as exc:
        speedup.load(User, b'{"age":30}')

    errors = exc.value.normalized_messages()
    assert errors == {"name": ["Missing data for required field."]}


def test_nested_missing_field_error() -> None:
    with pytest.raises(ValidationError) as exc:
        speedup.load(UserWithAddress, b'{"name":"John","address":{"country":"USA"}}')

    errors = exc.value.normalized_messages()
    assert errors == {"address": {"city": ["Missing data for required field."]}}


def test_list_item_error() -> None:
    with pytest.raises(ValidationError) as exc:
        speedup.load(list[SimpleUser], b'[{"name":"John","age":30},{"age":25}]')

    errors = exc.value.normalized_messages()
    assert errors == {"1": {"name": ["Missing data for required field."]}}


def test_dict_value_error() -> None:
    with pytest.raises(ValidationError) as exc:
        speedup.load(dict[str, SimpleUser], b'{"u1":{"name":"John","age":30},"u2":{"age":25}}')

    errors = exc.value.normalized_messages()
    assert errors == {"u2": {"name": ["Missing data for required field."]}}


@dataclass
class WithDecimal:
    amount: Decimal


def test_decimal_dump() -> None:
    obj = WithDecimal(amount=Decimal("123.45"))
    result = speedup.dump(WithDecimal, obj)
    assert result == b'{"amount":"123.45"}'


def test_decimal_load() -> None:
    data = b'{"amount":"123.45"}'
    result = speedup.load(WithDecimal, data)
    assert result == WithDecimal(amount=Decimal("123.45"))


def test_decimal_roundtrip() -> None:
    obj = WithDecimal(amount=Decimal("999.99"))
    json_bytes = speedup.dump(WithDecimal, obj)
    loaded = speedup.load(WithDecimal, json_bytes)
    assert loaded == obj


@dataclass
class WithDecimalPlaces:
    amount: Annotated[Decimal, {"places": 2}]


def test_decimal_places_load() -> None:
    data = b'{"amount":"123.456789"}'
    result = speedup.load(WithDecimalPlaces, data)
    assert result == WithDecimalPlaces(amount=Decimal("123.46"))


@dataclass
class WithUuid:
    id: uuid.UUID


def test_uuid_dump() -> None:
    obj = WithUuid(id=uuid.UUID("550e8400-e29b-41d4-a716-446655440000"))
    result = speedup.dump(WithUuid, obj)
    assert result == b'{"id":"550e8400-e29b-41d4-a716-446655440000"}'


def test_uuid_load() -> None:
    data = b'{"id":"550e8400-e29b-41d4-a716-446655440000"}'
    result = speedup.load(WithUuid, data)
    assert result == WithUuid(id=uuid.UUID("550e8400-e29b-41d4-a716-446655440000"))


def test_uuid_roundtrip() -> None:
    obj = WithUuid(id=uuid.UUID("550e8400-e29b-41d4-a716-446655440000"))
    json_bytes = speedup.dump(WithUuid, obj)
    loaded = speedup.load(WithUuid, json_bytes)
    assert loaded == obj


@dataclass
class WithDateTime:
    created_at: datetime.datetime


def test_datetime_dump() -> None:
    obj = WithDateTime(created_at=datetime.datetime(2024, 1, 15, 12, 30, 45))
    result = speedup.dump(WithDateTime, obj)
    assert result == b'{"created_at":"2024-01-15T12:30:45"}'


def test_datetime_load() -> None:
    data = b'{"created_at":"2024-01-15T12:30:45"}'
    result = speedup.load(WithDateTime, data)
    assert result == WithDateTime(created_at=datetime.datetime(2024, 1, 15, 12, 30, 45))


def test_datetime_roundtrip() -> None:
    obj = WithDateTime(created_at=datetime.datetime(2024, 1, 15, 12, 30, 45))
    json_bytes = speedup.dump(WithDateTime, obj)
    loaded = speedup.load(WithDateTime, json_bytes)
    assert loaded == obj


@dataclass
class WithDateTimeFormat:
    created_at: Annotated[datetime.datetime, {"format": "%Y-%m-%d %H:%M:%S"}]


def test_datetime_custom_format_dump() -> None:
    obj = WithDateTimeFormat(created_at=datetime.datetime(2024, 1, 15, 12, 30, 45))
    result = speedup.dump(WithDateTimeFormat, obj)
    assert result == b'{"created_at":"2024-01-15 12:30:45"}'


def test_datetime_custom_format_load() -> None:
    data = b'{"created_at":"2024-01-15 12:30:45"}'
    result = speedup.load(WithDateTimeFormat, data)
    assert result == WithDateTimeFormat(created_at=datetime.datetime(2024, 1, 15, 12, 30, 45))


@dataclass
class WithDate:
    date_field: datetime.date


def test_date_dump() -> None:
    obj = WithDate(date_field=datetime.date(2024, 1, 15))
    result = speedup.dump(WithDate, obj)
    assert result == b'{"date_field":"2024-01-15"}'


def test_date_load() -> None:
    data = b'{"date_field":"2024-01-15"}'
    result = speedup.load(WithDate, data)
    assert result == WithDate(date_field=datetime.date(2024, 1, 15))


def test_date_roundtrip() -> None:
    obj = WithDate(date_field=datetime.date(2024, 1, 15))
    json_bytes = speedup.dump(WithDate, obj)
    loaded = speedup.load(WithDate, json_bytes)
    assert loaded == obj


@dataclass
class WithTime:
    time_field: datetime.time


def test_time_dump() -> None:
    obj = WithTime(time_field=datetime.time(12, 30, 45))
    result = speedup.dump(WithTime, obj)
    assert result == b'{"time_field":"12:30:45"}'


def test_time_load() -> None:
    data = b'{"time_field":"12:30:45"}'
    result = speedup.load(WithTime, data)
    assert result == WithTime(time_field=datetime.time(12, 30, 45))


def test_time_roundtrip() -> None:
    obj = WithTime(time_field=datetime.time(12, 30, 45))
    json_bytes = speedup.dump(WithTime, obj)
    loaded = speedup.load(WithTime, json_bytes)
    assert loaded == obj


@dataclass
class WithStripWhitespaces:
    name: Annotated[str, {"strip_whitespaces": True}]


def test_str_strip_whitespaces_dump() -> None:
    obj = WithStripWhitespaces(name="  hello  ")
    result = speedup.dump(WithStripWhitespaces, obj)
    assert result == b'{"name":"hello"}'


def test_str_strip_whitespaces_load() -> None:
    data = b'{"name":"  world  "}'
    result = speedup.load(WithStripWhitespaces, data)
    assert result == WithStripWhitespaces(name="world")


@dataclass
class WithAllNewTypes:
    amount: Decimal
    id: uuid.UUID
    created_at: datetime.datetime
    date_field: datetime.date
    time_field: datetime.time


def test_all_new_types_roundtrip() -> None:
    obj = WithAllNewTypes(
        amount=Decimal("123.45"),
        id=uuid.UUID("550e8400-e29b-41d4-a716-446655440000"),
        created_at=datetime.datetime(2024, 1, 15, 12, 30, 45),
        date_field=datetime.date(2024, 1, 15),
        time_field=datetime.time(12, 30, 45),
    )
    json_bytes = speedup.dump(WithAllNewTypes, obj)
    loaded = speedup.load(WithAllNewTypes, json_bytes)
    assert loaded == obj


class Status(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"


class Priority(int, enum.Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3


@dataclass
class WithStrEnum:
    name: str
    status: Status


@dataclass
class WithIntEnum:
    name: str
    priority: Priority


@dataclass
class WithOptionalEnum:
    name: str
    status: Status | None = None


def test_str_enum_dump() -> None:
    obj = WithStrEnum(name="Task 1", status=Status.ACTIVE)
    result = speedup.dump(WithStrEnum, obj)
    assert result == b'{"name":"Task 1","status":"active"}'


def test_str_enum_load() -> None:
    data = b'{"name":"Task 1","status":"pending"}'
    result = speedup.load(WithStrEnum, data)
    assert result == WithStrEnum(name="Task 1", status=Status.PENDING)


def test_str_enum_roundtrip() -> None:
    obj = WithStrEnum(name="Task 1", status=Status.INACTIVE)
    json_bytes = speedup.dump(WithStrEnum, obj)
    loaded = speedup.load(WithStrEnum, json_bytes)
    assert loaded == obj


def test_int_enum_dump() -> None:
    obj = WithIntEnum(name="Task 1", priority=Priority.HIGH)
    result = speedup.dump(WithIntEnum, obj)
    assert result == b'{"name":"Task 1","priority":3}'


def test_int_enum_load() -> None:
    data = b'{"name":"Task 1","priority":2}'
    result = speedup.load(WithIntEnum, data)
    assert result == WithIntEnum(name="Task 1", priority=Priority.MEDIUM)


def test_int_enum_roundtrip() -> None:
    obj = WithIntEnum(name="Task 1", priority=Priority.LOW)
    json_bytes = speedup.dump(WithIntEnum, obj)
    loaded = speedup.load(WithIntEnum, json_bytes)
    assert loaded == obj


def test_optional_enum_none() -> None:
    obj = WithOptionalEnum(name="Task 1")
    result = speedup.dump(WithOptionalEnum, obj)
    assert result == b'{"name":"Task 1"}'
    loaded = speedup.load(WithOptionalEnum, b'{"name":"Task 1"}')
    assert loaded == WithOptionalEnum(name="Task 1", status=None)


def test_optional_enum_with_value() -> None:
    obj = WithOptionalEnum(name="Task 1", status=Status.ACTIVE)
    json_bytes = speedup.dump(WithOptionalEnum, obj)
    loaded = speedup.load(WithOptionalEnum, json_bytes)
    assert loaded == obj


@dataclass
class WithSet:
    tags: set[str]


def test_set_dump() -> None:
    obj = WithSet(tags={"a", "b", "c"})
    result = speedup.dump(WithSet, obj)
    parsed = json.loads(result)
    assert parsed == {"tags": ["a", "b", "c"]} or set(parsed["tags"]) == {"a", "b", "c"}


def test_set_load() -> None:
    data = b'{"tags":["a","b","c"]}'
    result = speedup.load(WithSet, data)
    assert result == WithSet(tags={"a", "b", "c"})


def test_set_roundtrip() -> None:
    obj = WithSet(tags={"x", "y", "z"})
    json_bytes = speedup.dump(WithSet, obj)
    loaded = speedup.load(WithSet, json_bytes)
    assert loaded == obj


def test_set_of_ints() -> None:
    result = speedup.dump(set[int], {1, 2, 3})
    parsed = json.loads(result)
    assert set(parsed) == {1, 2, 3}
    loaded = speedup.load(set[int], b"[1,2,3]")
    assert loaded == {1, 2, 3}


@dataclass
class WithFrozenSet:
    tags: frozenset[str]


def test_frozenset_dump() -> None:
    obj = WithFrozenSet(tags=frozenset({"a", "b", "c"}))
    result = speedup.dump(WithFrozenSet, obj)
    parsed = json.loads(result)
    assert set(parsed["tags"]) == {"a", "b", "c"}


def test_frozenset_load() -> None:
    data = b'{"tags":["a","b","c"]}'
    result = speedup.load(WithFrozenSet, data)
    assert result == WithFrozenSet(tags=frozenset({"a", "b", "c"}))


def test_frozenset_roundtrip() -> None:
    obj = WithFrozenSet(tags=frozenset({"x", "y", "z"}))
    json_bytes = speedup.dump(WithFrozenSet, obj)
    loaded = speedup.load(WithFrozenSet, json_bytes)
    assert loaded == obj


def test_frozenset_of_ints() -> None:
    result = speedup.dump(frozenset[int], frozenset({1, 2, 3}))
    parsed = json.loads(result)
    assert set(parsed) == {1, 2, 3}
    loaded = speedup.load(frozenset[int], b"[1,2,3]")
    assert loaded == frozenset({1, 2, 3})


@dataclass
class WithTuple:
    items: tuple[int, ...]


def test_tuple_dump() -> None:
    obj = WithTuple(items=(1, 2, 3))
    result = speedup.dump(WithTuple, obj)
    assert result == b'{"items":[1,2,3]}'


def test_tuple_load() -> None:
    data = b'{"items":[1,2,3]}'
    result = speedup.load(WithTuple, data)
    assert result == WithTuple(items=(1, 2, 3))


def test_tuple_roundtrip() -> None:
    obj = WithTuple(items=(4, 5, 6))
    json_bytes = speedup.dump(WithTuple, obj)
    loaded = speedup.load(WithTuple, json_bytes)
    assert loaded == obj


def test_tuple_of_strings() -> None:
    result = speedup.dump(tuple[str, ...], ("a", "b", "c"))
    assert result == b'["a","b","c"]'
    loaded = speedup.load(tuple[str, ...], result)
    assert loaded == ("a", "b", "c")


@dataclass
class WithOptionalSet:
    tags: set[str] | None = None


def test_optional_set_none() -> None:
    obj = WithOptionalSet()
    result = speedup.dump(WithOptionalSet, obj)
    assert result == b"{}"
    loaded = speedup.load(WithOptionalSet, b"{}")
    assert loaded == WithOptionalSet(tags=None)


def test_optional_set_with_value() -> None:
    obj = WithOptionalSet(tags={"a", "b"})
    json_bytes = speedup.dump(WithOptionalSet, obj)
    loaded = speedup.load(WithOptionalSet, json_bytes)
    assert loaded == obj


def test_encoding_utf8_default() -> None:
    obj = SimpleTypes(name="Привет", age=30, score=9.5, active=True)
    result = speedup.dump(SimpleTypes, obj)
    assert result == b'{"active":true,"age":30,"name":"\xd0\x9f\xd1\x80\xd0\xb8\xd0\xb2\xd0\xb5\xd1\x82","score":9.5}'
    loaded = speedup.load(SimpleTypes, result)
    assert loaded == obj


def test_encoding_utf8_explicit() -> None:
    obj = SimpleTypes(name="Привет", age=30, score=9.5, active=True)
    result = speedup.dump(SimpleTypes, obj, encoding="utf-8")
    loaded = speedup.load(SimpleTypes, result, encoding="utf-8")
    assert loaded == obj


def test_encoding_latin1_roundtrip() -> None:
    obj = SimpleTypes(name="café", age=30, score=9.5, active=True)
    result = speedup.dump(SimpleTypes, obj, encoding="latin-1")
    loaded = speedup.load(SimpleTypes, result, encoding="latin-1")
    assert loaded == obj


def test_encoding_latin1_with_extended_chars() -> None:
    obj = SimpleTypes(name="naïve", age=25, score=8.0, active=False)
    result = speedup.dump(SimpleTypes, obj, encoding="latin-1")
    loaded = speedup.load(SimpleTypes, result, encoding="latin-1")
    assert loaded == obj


def test_encoding_ascii() -> None:
    obj = SimpleTypes(name="hello", age=30, score=9.5, active=True)
    result = speedup.dump(SimpleTypes, obj, encoding="ascii")
    loaded = speedup.load(SimpleTypes, result, encoding="ascii")
    assert loaded == obj


def test_encoding_ascii_error_on_non_ascii() -> None:
    obj = SimpleTypes(name="Привет", age=30, score=9.5, active=True)
    with pytest.raises(ValueError):
        speedup.dump(SimpleTypes, obj, encoding="ascii")


def test_encoding_windows1251_cyrillic() -> None:
    obj = SimpleTypes(name="Привет", age=30, score=9.5, active=True)
    result = speedup.dump(SimpleTypes, obj, encoding="windows-1251")
    loaded = speedup.load(SimpleTypes, result, encoding="windows-1251")
    assert loaded == obj


def test_encoding_unknown_raises_error() -> None:
    obj = SimpleTypes(name="test", age=30, score=9.5, active=True)
    with pytest.raises(ValueError, match="Unknown encoding"):
        speedup.dump(SimpleTypes, obj, encoding="unknown-encoding-xyz")


def test_float_nan_raises_error() -> None:
    obj = SimpleTypes(name="test", age=30, score=float("nan"), active=True)
    with pytest.raises(ValueError, match="Cannot serialize NaN"):
        speedup.dump(SimpleTypes, obj)


def test_float_inf_raises_error() -> None:
    obj = SimpleTypes(name="test", age=30, score=float("inf"), active=True)
    with pytest.raises(ValueError, match="Cannot serialize infinite"):
        speedup.dump(SimpleTypes, obj)


def test_float_neg_inf_raises_error() -> None:
    obj = SimpleTypes(name="test", age=30, score=float("-inf"), active=True)
    with pytest.raises(ValueError, match="Cannot serialize infinite"):
        speedup.dump(SimpleTypes, obj)


@dataclass
class DecimalOnly:
    amount: Decimal


def test_decimal_load_from_string() -> None:
    data = b'{"amount":"123.45"}'
    result = speedup.load(DecimalOnly, data)
    assert result == DecimalOnly(amount=Decimal("123.45"))


def test_decimal_load_from_int() -> None:
    data = b'{"amount":123}'
    result = speedup.load(DecimalOnly, data)
    assert result == DecimalOnly(amount=Decimal("123"))


def test_decimal_load_from_float() -> None:
    data = b'{"amount":123.45}'
    result = speedup.load(DecimalOnly, data)
    assert result == DecimalOnly(amount=Decimal("123.45"))


@dataclass
class WithEmptyCollections:
    items: list[str]
    tags: set[str]
    mapping: dict[str, int]
    coords: tuple[int, ...]


def test_empty_list_roundtrip() -> None:
    obj = WithEmptyCollections(items=[], tags=set(), mapping={}, coords=())
    json_bytes = speedup.dump(WithEmptyCollections, obj)
    loaded = speedup.load(WithEmptyCollections, json_bytes)
    assert loaded.items == []
    assert loaded.tags == set()
    assert loaded.mapping == {}
    assert loaded.coords == ()


@dataclass
class WithNullBytes:
    text: str


def test_string_with_null_bytes() -> None:
    obj = WithNullBytes(text="hello\x00world")
    json_bytes = speedup.dump(WithNullBytes, obj)
    loaded = speedup.load(WithNullBytes, json_bytes)
    assert loaded == obj


def test_large_integer() -> None:
    obj = SimpleTypes(name="test", age=2**62, score=1.0, active=True)
    json_bytes = speedup.dump(SimpleTypes, obj)
    loaded = speedup.load(SimpleTypes, json_bytes)
    assert loaded == obj


@dataclass
class Level3:
    value: int


@dataclass
class Level2:
    nested: Level3


@dataclass
class Level1:
    nested: Level2


def test_deep_nesting() -> None:
    obj = Level1(nested=Level2(nested=Level3(value=42)))
    json_bytes = speedup.dump(Level1, obj)
    loaded = speedup.load(Level1, json_bytes)
    assert loaded == obj


@dataclass(frozen=True)
class FrozenData:
    name: str
    value: int


def test_frozen_dataclass_roundtrip() -> None:
    obj = FrozenData(name="test", value=123)
    json_bytes = speedup.dump(FrozenData, obj)
    loaded = speedup.load(FrozenData, json_bytes)
    assert loaded == obj


@dataclass
class WithDefaultFactory:
    name: str
    tags: list[str] = field(default_factory=list)


def test_default_factory_with_value() -> None:
    obj = WithDefaultFactory(name="test", tags=["a", "b"])
    json_bytes = speedup.dump(WithDefaultFactory, obj)
    loaded = speedup.load(WithDefaultFactory, json_bytes)
    assert loaded == obj


def test_default_factory_with_empty_list() -> None:
    obj = WithDefaultFactory(name="test", tags=[])
    json_bytes = speedup.dump(WithDefaultFactory, obj)
    loaded = speedup.load(WithDefaultFactory, json_bytes)
    assert loaded == obj


@dataclass
class WithUnicode:
    text: str


def test_unicode_normalization() -> None:
    obj = WithUnicode(text="café")
    json_bytes = speedup.dump(WithUnicode, obj)
    loaded = speedup.load(WithUnicode, json_bytes)
    assert loaded == obj


def test_emoji_in_string() -> None:
    obj = WithUnicode(text="Hello 👋 World 🌍")
    json_bytes = speedup.dump(WithUnicode, obj)
    loaded = speedup.load(WithUnicode, json_bytes)
    assert loaded == obj
