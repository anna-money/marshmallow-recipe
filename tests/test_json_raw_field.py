import dataclasses
import datetime
import decimal
import uuid
from typing import Any

import marshmallow as m
import pytest

import marshmallow_recipe as mr


def test_json_raw_field_with_valid_primitives() -> None:
    @dataclasses.dataclass
    class Holder:
        value: Any

    assert mr.load(Holder, {"value": None}) == Holder(value=None)
    assert mr.load(Holder, {"value": True}) == Holder(value=True)
    assert mr.load(Holder, {"value": False}) == Holder(value=False)
    assert mr.load(Holder, {"value": "string"}) == Holder(value="string")
    assert mr.load(Holder, {"value": 42}) == Holder(value=42)
    assert mr.load(Holder, {"value": 3.14}) == Holder(value=3.14)

    assert mr.dump(Holder(value=None)) == {}
    assert mr.dump(Holder(value=True)) == {"value": True}
    assert mr.dump(Holder(value=False)) == {"value": False}
    assert mr.dump(Holder(value="string")) == {"value": "string"}
    assert mr.dump(Holder(value=42)) == {"value": 42}
    assert mr.dump(Holder(value=3.14)) == {"value": 3.14}


def test_json_raw_field_with_valid_list() -> None:
    @dataclasses.dataclass
    class Holder:
        value: Any

    assert mr.load(Holder, {"value": []}) == Holder(value=[])
    assert mr.load(Holder, {"value": [1, 2, 3]}) == Holder(value=[1, 2, 3])
    assert mr.load(Holder, {"value": ["a", "b"]}) == Holder(value=["a", "b"])
    assert mr.load(Holder, {"value": [None, True, 1, "str"]}) == Holder(value=[None, True, 1, "str"])

    assert mr.dump(Holder(value=[])) == {"value": []}
    assert mr.dump(Holder(value=[1, 2, 3])) == {"value": [1, 2, 3]}
    assert mr.dump(Holder(value=["a", "b"])) == {"value": ["a", "b"]}
    assert mr.dump(Holder(value=[None, True, 1, "str"])) == {"value": [None, True, 1, "str"]}


def test_json_raw_field_with_valid_dict() -> None:
    @dataclasses.dataclass
    class Holder:
        value: Any

    assert mr.load(Holder, {"value": {}}) == Holder(value={})
    assert mr.load(Holder, {"value": {"key": "value"}}) == Holder(value={"key": "value"})
    assert mr.load(Holder, {"value": {"a": 1, "b": 2}}) == Holder(value={"a": 1, "b": 2})
    assert mr.load(Holder, {"value": {"key": None}}) == Holder(value={"key": None})

    assert mr.dump(Holder(value={})) == {"value": {}}
    assert mr.dump(Holder(value={"key": "value"})) == {"value": {"key": "value"}}
    assert mr.dump(Holder(value={"a": 1, "b": 2})) == {"value": {"a": 1, "b": 2}}


def test_json_raw_field_with_nested_structures() -> None:
    @dataclasses.dataclass
    class Holder:
        value: Any

    nested = {"users": [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}], "count": 2}
    assert mr.load(Holder, {"value": nested}) == Holder(value=nested)
    assert mr.dump(Holder(value=nested)) == {"value": nested}

    deeply_nested = {"a": {"b": {"c": [1, 2, {"d": "value"}]}}}
    assert mr.load(Holder, {"value": deeply_nested}) == Holder(value=deeply_nested)
    assert mr.dump(Holder(value=deeply_nested)) == {"value": deeply_nested}


def test_json_raw_field_rejects_datetime() -> None:
    @dataclasses.dataclass
    class Holder:
        value: Any

    with pytest.raises(m.ValidationError) as exc_info:
        mr.dump(Holder(value=datetime.datetime.now()))
    assert exc_info.value.messages == {"value": ["Not a valid JSON-serializable value."]}


def test_json_raw_field_rejects_date() -> None:
    @dataclasses.dataclass
    class Holder:
        value: Any

    with pytest.raises(m.ValidationError) as exc_info:
        mr.dump(Holder(value=datetime.date.today()))
    assert exc_info.value.messages == {"value": ["Not a valid JSON-serializable value."]}


def test_json_raw_field_rejects_uuid() -> None:
    @dataclasses.dataclass
    class Holder:
        value: Any

    with pytest.raises(m.ValidationError) as exc_info:
        mr.dump(Holder(value=uuid.uuid4()))
    assert exc_info.value.messages == {"value": ["Not a valid JSON-serializable value."]}


def test_json_raw_field_rejects_decimal() -> None:
    @dataclasses.dataclass
    class Holder:
        value: Any

    with pytest.raises(m.ValidationError) as exc_info:
        mr.dump(Holder(value=decimal.Decimal("3.14")))
    assert exc_info.value.messages == {"value": ["Not a valid JSON-serializable value."]}


def test_json_raw_field_rejects_custom_object() -> None:
    @dataclasses.dataclass
    class CustomObject:
        field: str

    @dataclasses.dataclass
    class Holder:
        value: Any

    with pytest.raises(m.ValidationError) as exc_info:
        mr.dump(Holder(value=CustomObject(field="test")))
    assert exc_info.value.messages == {"value": ["Not a valid JSON-serializable value."]}


def test_json_raw_field_rejects_dict_with_non_string_keys_load() -> None:
    @dataclasses.dataclass
    class Holder:
        value: Any

    with pytest.raises(m.ValidationError) as exc_info:
        mr.load(Holder, {"value": {1: "value"}})
    assert exc_info.value.messages == {"value": ["Not a valid JSON-serializable value."]}


def test_json_raw_field_rejects_dict_with_non_string_keys_dump() -> None:
    @dataclasses.dataclass
    class Holder:
        value: Any

    with pytest.raises(m.ValidationError):
        mr.dump(Holder(value={1: "value"}))

    with pytest.raises(m.ValidationError):
        mr.dump(Holder(value={(1, 2): "value"}))


def test_json_raw_field_rejects_list_with_invalid_items() -> None:
    @dataclasses.dataclass
    class Holder:
        value: Any

    with pytest.raises(m.ValidationError):
        mr.dump(Holder(value=[1, 2, datetime.datetime.now()]))

    with pytest.raises(m.ValidationError):
        mr.dump(Holder(value=[{"key": datetime.date.today()}]))


def test_json_raw_field_rejects_nested_invalid_structures() -> None:
    @dataclasses.dataclass
    class Holder:
        value: Any

    with pytest.raises(m.ValidationError):
        mr.dump(Holder(value={"nested": {"deeply": {"invalid": uuid.uuid4()}}}))

    with pytest.raises(m.ValidationError):
        mr.dump(Holder(value={"list": [1, 2, [3, {"bad": decimal.Decimal("1.5")}]]}))


def test_json_raw_field_rejects_set() -> None:
    @dataclasses.dataclass
    class Holder:
        value: Any

    with pytest.raises(m.ValidationError):
        mr.dump(Holder(value={1, 2, 3}))


def test_json_raw_field_rejects_tuple() -> None:
    @dataclasses.dataclass
    class Holder:
        value: Any

    with pytest.raises(m.ValidationError):
        mr.dump(Holder(value=(1, 2, 3)))


def test_json_raw_field_rejects_bytes() -> None:
    @dataclasses.dataclass
    class Holder:
        value: Any

    with pytest.raises(m.ValidationError):
        mr.dump(Holder(value=b"bytes"))
