import dataclasses
from typing import Optional

import marshmallow_recipe as mr


def test_simple_types() -> None:
    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class SimpleTypesContainers:
        bool_field: bool
        str_field: Optional[str]

    raw = dict(bool_field=True, str_field="42")

    loaded = mr.load(SimpleTypesContainers, raw)
    dumped = mr.dump(loaded)

    assert loaded == SimpleTypesContainers(bool_field=True, str_field="42")
    assert dumped == raw
    assert mr.schema(SimpleTypesContainers) is mr.schema(SimpleTypesContainers)


def test_nested() -> None:
    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class BoolContainer:
        bool_field: bool

    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class Container:
        str_field: str | None
        bool_container_field: BoolContainer

    raw = dict(str_field="42", bool_container_field=dict(bool_field=True))
    loaded = mr.load(Container, raw)
    dumped = mr.dump(loaded)

    assert loaded == Container(str_field="42", bool_container_field=BoolContainer(bool_field=True))
    assert dumped == raw

    assert mr.schema(Container) is mr.schema(Container)


def test_custom_name() -> None:
    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class BoolContainer:
        bool_field: bool = dataclasses.field(metadata=mr.metadata(name="BoolField"))

    raw = dict(BoolField=False)

    loaded = mr.load(BoolContainer, raw)
    dumped = mr.dump(loaded)

    assert loaded == BoolContainer(bool_field=False)
    assert dumped == raw

    assert mr.schema(BoolContainer) is mr.schema(BoolContainer)
