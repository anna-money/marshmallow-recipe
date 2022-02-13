import dataclasses
from typing import Optional

import marshmallow_recipe as mr


def test_simple_types() -> None:
    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class SimpleTypesContainers:
        bool_field: bool
        str_field: Optional[str]

    raw = dict(bool_field=True, str_field="42")
    schema = mr.bake(SimpleTypesContainers)

    loaded = mr.load(schema(), raw)
    dumped = mr.dump(schema(), loaded)

    assert loaded == SimpleTypesContainers(bool_field=True, str_field="42")
    assert dumped == raw


def test_nested() -> None:
    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class BoolContainer:
        bool_field: bool

    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class Container:
        str_field: str | None
        bool_container_field: BoolContainer

    raw = dict(str_field="42", bool_container_field=dict(bool_field=True))
    schema = mr.bake(Container)

    loaded = mr.load(schema(), raw)
    dumped = mr.dump(schema(), loaded)

    assert loaded == Container(str_field="42", bool_container_field=BoolContainer(bool_field=True))
    assert dumped == raw


def test_custom_name() -> None:
    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class BoolContainer:
        bool_field: bool = dataclasses.field(metadata=dict(name="BoolField"))

    schema = mr.bake(BoolContainer)
    raw = dict(BoolField=False)

    loaded = mr.load(schema(), raw)
    dumped = mr.dump(schema(), loaded)

    assert loaded == BoolContainer(bool_field=False)
    assert dumped == raw
