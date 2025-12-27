from __future__ import annotations

import dataclasses
import json
from typing import Any


@dataclasses.dataclass(slots=True, kw_only=True)
class BasicSlots:
    name: str
    value: int


@dataclasses.dataclass(slots=True, kw_only=True)
class WithPostInit:
    name: str
    value: int
    computed: str = dataclasses.field(init=False, default="")

    def __post_init__(self) -> None:
        self.computed = f"{self.name}_{self.value}"


@dataclasses.dataclass(slots=True, kw_only=True, init=False)
class WithCustomInit:
    name: str
    value: int

    def __init__(self, name: str, value: int) -> None:
        self.name = name.upper()
        self.value = value * 2


@dataclasses.dataclass(slots=True, kw_only=True)
class WithFieldInitFalse:
    name: str
    value: int
    auto_field: str = dataclasses.field(init=False, default="auto")


@dataclasses.dataclass(slots=True, kw_only=True)
class WithDefaultFactory:
    name: str
    tags: list[str] = dataclasses.field(default_factory=list)


@dataclasses.dataclass(slots=True, kw_only=True)
class WithDefaultValue:
    name: str
    count: int = 42


@dataclasses.dataclass(slots=True, kw_only=True, frozen=True)
class FrozenSlots:
    name: str
    value: int


@dataclasses.dataclass(kw_only=True)
class WithoutSlots:
    name: str
    value: int


@dataclasses.dataclass(slots=True, kw_only=True)
class NestedItem:
    id: int
    label: str


@dataclasses.dataclass(slots=True, kw_only=True)
class WithNestedList:
    name: str
    items: list[NestedItem]


@dataclasses.dataclass(slots=True, kw_only=True)
class WithOptionalFields:
    required: str
    optional_str: str | None = None
    optional_int: int | None = None


@dataclasses.dataclass(slots=True, kw_only=True)
class WithMixedDefaults:
    name: str
    count: int = 0
    tags: list[str] = dataclasses.field(default_factory=list)
    description: str | None = None


def test_basic_slots_dump(impl: Any) -> None:
    obj = BasicSlots(name="test", value=123)
    result = json.loads(impl.dump(BasicSlots, obj))
    assert result == {"name": "test", "value": 123}


def test_basic_slots_load(impl: Any) -> None:
    data = b'{"name": "test", "value": 123}'
    result = impl.load(BasicSlots, data)
    assert result == BasicSlots(name="test", value=123)


def test_with_post_init_load(impl: Any) -> None:
    data = b'{"name": "test", "value": 5}'
    result = impl.load(WithPostInit, data)
    assert result.name == "test"
    assert result.value == 5
    assert result.computed == "test_5"


def test_with_custom_init_dump(impl: Any) -> None:
    obj = WithCustomInit(name="test", value=5)
    result = json.loads(impl.dump(WithCustomInit, obj))
    assert result == {"name": "TEST", "value": 10}


def test_with_custom_init_load(impl: Any) -> None:
    data = b'{"name": "test", "value": 5}'
    result = impl.load(WithCustomInit, data)
    assert result.name == "TEST"
    assert result.value == 10


def test_with_field_init_false_load(impl: Any) -> None:
    data = b'{"name": "test", "value": 123}'
    result = impl.load(WithFieldInitFalse, data)
    assert result.name == "test"
    assert result.value == 123
    assert result.auto_field == "auto"


def test_with_default_factory_dump(impl: Any) -> None:
    obj = WithDefaultFactory(name="test", tags=["a", "b"])
    result = json.loads(impl.dump(WithDefaultFactory, obj))
    assert result == {"name": "test", "tags": ["a", "b"]}


def test_with_default_factory_load_with_value(impl: Any) -> None:
    data = b'{"name": "test", "tags": ["x", "y"]}'
    result = impl.load(WithDefaultFactory, data)
    assert result == WithDefaultFactory(name="test", tags=["x", "y"])


def test_with_default_factory_load_without_value(impl: Any) -> None:
    data = b'{"name": "test"}'
    result = impl.load(WithDefaultFactory, data)
    assert result.name == "test"
    assert result.tags == []


def test_with_default_factory_independence(impl: Any) -> None:
    data = b'{"name": "test"}'
    result1 = impl.load(WithDefaultFactory, data)
    result2 = impl.load(WithDefaultFactory, data)
    result1.tags.append("modified")
    assert result2.tags == []


def test_with_default_value_dump(impl: Any) -> None:
    obj = WithDefaultValue(name="test", count=99)
    result = json.loads(impl.dump(WithDefaultValue, obj))
    assert result == {"name": "test", "count": 99}


def test_with_default_value_load_with_value(impl: Any) -> None:
    data = b'{"name": "test", "count": 99}'
    result = impl.load(WithDefaultValue, data)
    assert result == WithDefaultValue(name="test", count=99)


def test_with_default_value_load_without_value(impl: Any) -> None:
    data = b'{"name": "test"}'
    result = impl.load(WithDefaultValue, data)
    assert result == WithDefaultValue(name="test", count=42)


def test_frozen_slots_dump(impl: Any) -> None:
    obj = FrozenSlots(name="test", value=123)
    result = json.loads(impl.dump(FrozenSlots, obj))
    assert result == {"name": "test", "value": 123}


def test_frozen_slots_load(impl: Any) -> None:
    data = b'{"name": "test", "value": 123}'
    result = impl.load(FrozenSlots, data)
    assert result == FrozenSlots(name="test", value=123)


def test_without_slots_dump(impl: Any) -> None:
    obj = WithoutSlots(name="test", value=123)
    result = json.loads(impl.dump(WithoutSlots, obj))
    assert result == {"name": "test", "value": 123}


def test_without_slots_load(impl: Any) -> None:
    data = b'{"name": "test", "value": 123}'
    result = impl.load(WithoutSlots, data)
    assert result == WithoutSlots(name="test", value=123)


def test_nested_list_dump(impl: Any) -> None:
    obj = WithNestedList(name="container", items=[NestedItem(id=1, label="first"), NestedItem(id=2, label="second")])
    result = json.loads(impl.dump(WithNestedList, obj))
    assert result == {"name": "container", "items": [{"id": 1, "label": "first"}, {"id": 2, "label": "second"}]}


def test_nested_list_load(impl: Any) -> None:
    data = b'{"name": "container", "items": [{"id": 1, "label": "first"}, {"id": 2, "label": "second"}]}'
    result = impl.load(WithNestedList, data)
    assert result == WithNestedList(
        name="container", items=[NestedItem(id=1, label="first"), NestedItem(id=2, label="second")]
    )


def test_nested_list_empty(impl: Any) -> None:
    data = b'{"name": "empty", "items": []}'
    result = impl.load(WithNestedList, data)
    assert result == WithNestedList(name="empty", items=[])


def test_optional_fields_all_present(impl: Any) -> None:
    data = b'{"required": "test", "optional_str": "hello", "optional_int": 42}'
    result = impl.load(WithOptionalFields, data)
    assert result == WithOptionalFields(required="test", optional_str="hello", optional_int=42)


def test_optional_fields_none_present(impl: Any) -> None:
    data = b'{"required": "test"}'
    result = impl.load(WithOptionalFields, data)
    assert result == WithOptionalFields(required="test", optional_str=None, optional_int=None)


def test_optional_fields_explicit_null(impl: Any) -> None:
    data = b'{"required": "test", "optional_str": null, "optional_int": null}'
    result = impl.load(WithOptionalFields, data)
    assert result == WithOptionalFields(required="test", optional_str=None, optional_int=None)


def test_optional_fields_partial(impl: Any) -> None:
    data = b'{"required": "test", "optional_str": "hello"}'
    result = impl.load(WithOptionalFields, data)
    assert result == WithOptionalFields(required="test", optional_str="hello", optional_int=None)


def test_mixed_defaults_all_provided(impl: Any) -> None:
    data = b'{"name": "test", "count": 10, "tags": ["a"], "description": "desc"}'
    result = impl.load(WithMixedDefaults, data)
    assert result == WithMixedDefaults(name="test", count=10, tags=["a"], description="desc")


def test_mixed_defaults_none_provided(impl: Any) -> None:
    data = b'{"name": "test"}'
    result = impl.load(WithMixedDefaults, data)
    assert result.name == "test"
    assert result.count == 0
    assert result.tags == []
    assert result.description is None


def test_mixed_defaults_partial(impl: Any) -> None:
    data = b'{"name": "test", "count": 5}'
    result = impl.load(WithMixedDefaults, data)
    assert result.name == "test"
    assert result.count == 5
    assert result.tags == []
    assert result.description is None


def test_roundtrip_basic_slots(impl: Any) -> None:
    original = BasicSlots(name="roundtrip", value=999)
    dumped = impl.dump(BasicSlots, original)
    loaded = impl.load(BasicSlots, dumped.encode())
    assert loaded == original


def test_roundtrip_nested_list(impl: Any) -> None:
    original = WithNestedList(name="roundtrip", items=[NestedItem(id=i, label=f"item_{i}") for i in range(10)])
    dumped = impl.dump(WithNestedList, original)
    loaded = impl.load(WithNestedList, dumped.encode())
    assert loaded == original


def test_roundtrip_with_defaults(impl: Any) -> None:
    original = WithMixedDefaults(name="test")
    dumped = impl.dump(WithMixedDefaults, original)
    loaded = impl.load(WithMixedDefaults, dumped.encode())
    assert loaded == original
