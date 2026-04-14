from __future__ import annotations

import dataclasses
import json
from typing import Any

import pytest

from .conftest import Serializer


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


class TestDirectSlotsDump:
    def test_basic(self, impl: Serializer) -> None:
        obj = BasicSlots(name="test", value=123)
        result = json.loads(impl.dump(BasicSlots, obj))
        assert result == {"name": "test", "value": 123}

    def test_with_post_init(self, impl: Serializer) -> None:
        obj = WithPostInit(name="test", value=5)
        result = json.loads(impl.dump(WithPostInit, obj))
        assert result == {"name": "test", "value": 5}

    def test_with_field_init_false(self, impl: Serializer) -> None:
        obj = WithFieldInitFalse(name="test", value=123)
        result = json.loads(impl.dump(WithFieldInitFalse, obj))
        assert result == {"name": "test", "value": 123}

    def test_with_custom_init(self, impl: Serializer) -> None:
        obj = WithCustomInit(name="test", value=5)
        result = json.loads(impl.dump(WithCustomInit, obj))
        assert result == {"name": "TEST", "value": 10}

    def test_with_default_factory(self, impl: Serializer) -> None:
        obj = WithDefaultFactory(name="test", tags=["a", "b"])
        result = json.loads(impl.dump(WithDefaultFactory, obj))
        assert result == {"name": "test", "tags": ["a", "b"]}

    def test_with_default_value(self, impl: Serializer) -> None:
        obj = WithDefaultValue(name="test", count=99)
        result = json.loads(impl.dump(WithDefaultValue, obj))
        assert result == {"name": "test", "count": 99}

    def test_frozen(self, impl: Serializer) -> None:
        obj = FrozenSlots(name="test", value=123)
        result = json.loads(impl.dump(FrozenSlots, obj))
        assert result == {"name": "test", "value": 123}

    def test_without_slots(self, impl: Serializer) -> None:
        obj = WithoutSlots(name="test", value=123)
        result = json.loads(impl.dump(WithoutSlots, obj))
        assert result == {"name": "test", "value": 123}

    def test_nested_list(self, impl: Serializer) -> None:
        obj = WithNestedList(
            name="container", items=[NestedItem(id=1, label="first"), NestedItem(id=2, label="second")]
        )
        result = json.loads(impl.dump(WithNestedList, obj))
        assert result == {"name": "container", "items": [{"id": 1, "label": "first"}, {"id": 2, "label": "second"}]}


class TestDirectSlotsLoad:
    def test_basic(self, impl: Serializer) -> None:
        data = b'{"name":"test","value":123}'
        result = impl.load(BasicSlots, data)
        assert result == BasicSlots(name="test", value=123)

    def test_with_post_init(self, impl: Serializer) -> None:
        data = b'{"name":"test","value":5}'
        result = impl.load(WithPostInit, data)
        assert result == WithPostInit(name="test", value=5)

    def test_with_custom_init(self, impl: Serializer) -> None:
        data = b'{"name":"test","value":5}'
        result = impl.load(WithCustomInit, data)
        assert result == WithCustomInit(name="test", value=5)

    def test_with_field_init_false(self, impl: Serializer) -> None:
        data = b'{"name":"test","value":123}'
        result = impl.load(WithFieldInitFalse, data)
        assert result == WithFieldInitFalse(name="test", value=123)

    def test_with_default_factory_with_value(self, impl: Serializer) -> None:
        data = b'{"name":"test","tags":["x","y"]}'
        result = impl.load(WithDefaultFactory, data)
        assert result == WithDefaultFactory(name="test", tags=["x", "y"])

    def test_with_default_factory_without_value(self, impl: Serializer) -> None:
        data = b'{"name":"test"}'
        result = impl.load(WithDefaultFactory, data)
        assert result == WithDefaultFactory(name="test")

    def test_with_default_factory_independence(self, impl: Serializer) -> None:
        data = b'{"name":"test"}'
        result1 = impl.load(WithDefaultFactory, data)
        result2 = impl.load(WithDefaultFactory, data)
        result1.tags.append("modified")
        assert result2.tags == []

    def test_with_default_value_with_value(self, impl: Serializer) -> None:
        data = b'{"name":"test","count":99}'
        result = impl.load(WithDefaultValue, data)
        assert result == WithDefaultValue(name="test", count=99)

    def test_with_default_value_without_value(self, impl: Serializer) -> None:
        data = b'{"name":"test"}'
        result = impl.load(WithDefaultValue, data)
        assert result == WithDefaultValue(name="test", count=42)

    def test_frozen(self, impl: Serializer) -> None:
        data = b'{"name":"test","value":123}'
        result = impl.load(FrozenSlots, data)
        assert result == FrozenSlots(name="test", value=123)

    def test_without_slots(self, impl: Serializer) -> None:
        data = b'{"name":"test","value":123}'
        result = impl.load(WithoutSlots, data)
        assert result == WithoutSlots(name="test", value=123)

    def test_nested_list(self, impl: Serializer) -> None:
        data = b'{"name":"container","items":[{"id":1,"label":"first"},{"id":2,"label":"second"}]}'
        result = impl.load(WithNestedList, data)
        assert result == WithNestedList(
            name="container", items=[NestedItem(id=1, label="first"), NestedItem(id=2, label="second")]
        )

    def test_nested_list_empty(self, impl: Serializer) -> None:
        data = b'{"name":"empty","items":[]}'
        result = impl.load(WithNestedList, data)
        assert result == WithNestedList(name="empty", items=[])

    def test_optional_fields_all_present(self, impl: Serializer) -> None:
        data = b'{"required":"test","optional_str":"hello","optional_int":42}'
        result = impl.load(WithOptionalFields, data)
        assert result == WithOptionalFields(required="test", optional_str="hello", optional_int=42)

    def test_optional_fields_none_present(self, impl: Serializer) -> None:
        data = b'{"required":"test"}'
        result = impl.load(WithOptionalFields, data)
        assert result == WithOptionalFields(required="test", optional_str=None, optional_int=None)

    def test_optional_fields_explicit_null(self, impl: Serializer) -> None:
        data = b'{"required":"test","optional_str":null,"optional_int":null}'
        result = impl.load(WithOptionalFields, data)
        assert result == WithOptionalFields(required="test", optional_str=None, optional_int=None)

    def test_optional_fields_partial(self, impl: Serializer) -> None:
        data = b'{"required":"test","optional_str":"hello"}'
        result = impl.load(WithOptionalFields, data)
        assert result == WithOptionalFields(required="test", optional_str="hello", optional_int=None)

    def test_mixed_defaults_all_provided(self, impl: Serializer) -> None:
        data = b'{"name":"test","count":10,"tags":["a"],"description":"desc"}'
        result = impl.load(WithMixedDefaults, data)
        assert result == WithMixedDefaults(name="test", count=10, tags=["a"], description="desc")

    def test_mixed_defaults_none_provided(self, impl: Serializer) -> None:
        data = b'{"name":"test"}'
        result = impl.load(WithMixedDefaults, data)
        assert result == WithMixedDefaults(name="test")

    def test_mixed_defaults_partial(self, impl: Serializer) -> None:
        data = b'{"name":"test","count":5}'
        result = impl.load(WithMixedDefaults, data)
        assert result == WithMixedDefaults(name="test", count=5)


@dataclasses.dataclass
class PlainBasic:
    name: str
    value: int


@dataclasses.dataclass(frozen=True)
class FrozenNoSlots:
    name: str
    value: int


@dataclasses.dataclass
class PlainWithDefaults:
    name: str
    count: int = 42
    tags: list[str] = dataclasses.field(default_factory=list)
    description: str | None = None


@dataclasses.dataclass
class PlainNestedItem:
    id: int
    label: str


@dataclasses.dataclass
class PlainWithNestedList:
    name: str
    items: list[PlainNestedItem]


@dataclasses.dataclass(slots=True)
class MixedParentSlots:
    x: int


@dataclasses.dataclass
class MixedChildNoSlots(MixedParentSlots):
    y: int = 0


@dataclasses.dataclass
class MixedParentNoSlots:
    x: int


@dataclasses.dataclass(slots=True)
class MixedChildSlots(MixedParentNoSlots):
    y: int = 0


@dataclasses.dataclass
class PlainWithPostInit:
    name: str
    value: int
    computed: str = dataclasses.field(init=False, default="")

    def __post_init__(self) -> None:
        self.computed = f"{self.name}_{self.value}"


@dataclasses.dataclass
class PlainWithFieldInitFalse:
    name: str
    value: int
    auto_field: str = dataclasses.field(init=False, default="auto")


class TestDirectDictDump:
    @pytest.mark.parametrize(
        ("cls", "obj", "expected"),
        [
            (PlainBasic, PlainBasic(name="test", value=123), {"name": "test", "value": 123}),
            (FrozenNoSlots, FrozenNoSlots(name="test", value=123), {"name": "test", "value": 123}),
            (
                PlainWithDefaults,
                PlainWithDefaults(name="t", count=5, tags=["a"], description="d"),
                {"name": "t", "count": 5, "tags": ["a"], "description": "d"},
            ),
            (PlainWithDefaults, PlainWithDefaults(name="t"), {"name": "t", "count": 42, "tags": []}),
            (
                PlainWithNestedList,
                PlainWithNestedList(name="c", items=[PlainNestedItem(id=1, label="a")]),
                {"name": "c", "items": [{"id": 1, "label": "a"}]},
            ),
            (PlainWithNestedList, PlainWithNestedList(name="e", items=[]), {"name": "e", "items": []}),
            (MixedChildNoSlots, MixedChildNoSlots(x=1, y=2), {"x": 1, "y": 2}),
            (MixedChildSlots, MixedChildSlots(x=1, y=2), {"x": 1, "y": 2}),
            (PlainWithPostInit, PlainWithPostInit(name="a", value=1), {"name": "a", "value": 1}),
            (PlainWithFieldInitFalse, PlainWithFieldInitFalse(name="a", value=1), {"name": "a", "value": 1}),
        ],
        ids=[
            "plain_basic",
            "frozen_no_slots",
            "plain_defaults_all",
            "plain_defaults_only_required",
            "plain_nested",
            "plain_nested_empty",
            "mixed_parent_slots",
            "mixed_parent_no_slots",
            "plain_post_init",
            "plain_init_false",
        ],
    )
    def test_dump(self, impl: Serializer, cls: type, obj: Any, expected: dict) -> None:
        result = json.loads(impl.dump(cls, obj))
        assert result == expected


class TestDirectDictLoad:
    @pytest.mark.parametrize(
        ("cls", "data", "expected"),
        [
            (PlainBasic, b'{"name":"test","value":123}', PlainBasic(name="test", value=123)),
            (FrozenNoSlots, b'{"name":"test","value":123}', FrozenNoSlots(name="test", value=123)),
            (
                PlainWithDefaults,
                b'{"name":"t","count":10,"tags":["a"],"description":"d"}',
                PlainWithDefaults(name="t", count=10, tags=["a"], description="d"),
            ),
            (PlainWithDefaults, b'{"name":"t"}', PlainWithDefaults(name="t")),
            (PlainWithDefaults, b'{"name":"t","count":5}', PlainWithDefaults(name="t", count=5)),
            (PlainWithDefaults, b'{"name":"t","tags":["x"]}', PlainWithDefaults(name="t", tags=["x"])),
            (PlainWithDefaults, b'{"name":"t","description":null}', PlainWithDefaults(name="t", description=None)),
            (
                PlainWithNestedList,
                b'{"name":"c","items":[{"id":1,"label":"a"},{"id":2,"label":"b"}]}',
                PlainWithNestedList(
                    name="c", items=[PlainNestedItem(id=1, label="a"), PlainNestedItem(id=2, label="b")]
                ),
            ),
            (PlainWithNestedList, b'{"name":"e","items":[]}', PlainWithNestedList(name="e", items=[])),
            (MixedChildNoSlots, b'{"x":1,"y":2}', MixedChildNoSlots(x=1, y=2)),
            (MixedChildNoSlots, b'{"x":1}', MixedChildNoSlots(x=1)),
            (MixedChildSlots, b'{"x":1,"y":2}', MixedChildSlots(x=1, y=2)),
            (MixedChildSlots, b'{"x":1}', MixedChildSlots(x=1)),
            (PlainWithPostInit, b'{"name":"a","value":1}', PlainWithPostInit(name="a", value=1)),
            (PlainWithFieldInitFalse, b'{"name":"a","value":1}', PlainWithFieldInitFalse(name="a", value=1)),
        ],
        ids=[
            "plain_basic",
            "frozen_no_slots",
            "defaults_all_provided",
            "defaults_none_provided",
            "defaults_partial_count",
            "defaults_partial_tags",
            "defaults_explicit_null",
            "nested_list",
            "nested_list_empty",
            "mixed_parent_slots",
            "mixed_parent_slots_default",
            "mixed_parent_no_slots",
            "mixed_parent_no_slots_default",
            "post_init",
            "init_false",
        ],
    )
    def test_load(self, impl: Serializer, cls: type, data: bytes, expected: Any) -> None:
        result = impl.load(cls, data)
        assert result == expected

    def test_frozen_no_slots_immutability(self, impl: Serializer) -> None:
        result = impl.load(FrozenNoSlots, b'{"name":"test","value":123}')
        with pytest.raises(dataclasses.FrozenInstanceError):
            result.name = "changed"  # type: ignore[misc]

    def test_default_factory_independence(self, impl: Serializer) -> None:
        r1 = impl.load(PlainWithDefaults, b'{"name":"a"}')
        r2 = impl.load(PlainWithDefaults, b'{"name":"b"}')
        r1.tags.append("modified")
        assert r2.tags == []
