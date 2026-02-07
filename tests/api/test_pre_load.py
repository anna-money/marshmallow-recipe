import dataclasses
from typing import Annotated, Any

import marshmallow_recipe as mr
import pytest

from .conftest import Serializer


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithPreLoad:
    value: str

    @staticmethod
    @mr.pre_load
    def pre_load(data: dict[str, Any]) -> dict[str, Any]:
        data["value"] = data["value"].upper()
        return data


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithMultiplePreLoads:
    value: str

    @staticmethod
    @mr.pre_load
    def pre_load1(data: dict[str, Any]) -> dict[str, Any]:
        data["value"] = data["value"] + "_1"
        return data

    @staticmethod
    @mr.pre_load
    def pre_load2(data: dict[str, Any]) -> dict[str, Any]:
        data["value"] = data["value"] + "_2"
        return data


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithClassMethodPreLoad:
    value: str

    @classmethod
    @mr.pre_load
    def pre_load(cls, data: dict[str, Any]) -> dict[str, Any]:
        data["value"] = data["value"].lower()
        return data


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithFieldNameNormalization:
    """Field named 'x-id' but we want to accept 'id' too via pre_load"""

    value: Annotated[str | None, mr.meta(name="x-id")] = None

    @staticmethod
    @mr.pre_load
    def normalize(data: dict[str, Any]) -> dict[str, Any]:
        """Map 'id' to 'x-id'"""
        if "id" in data and "x-id" not in data:
            data = {**data, "x-id": data["id"]}
        return data


class TestPreLoadLoad:
    def test_transforms_data(self, impl: Serializer) -> None:
        if not impl.supports_pre_load:
            pytest.skip("pre_load not supported")

        result = impl.load(WithPreLoad, b'{"value":"hello"}')
        assert result == WithPreLoad(value="HELLO")

    def test_multiple(self, impl: Serializer) -> None:
        if not impl.supports_pre_load:
            pytest.skip("pre_load not supported")

        result = impl.load(WithMultiplePreLoads, b'{"value":"x"}')
        assert result == WithMultiplePreLoads(value="x_1_2")

    def test_classmethod(self, impl: Serializer) -> None:
        if not impl.supports_pre_load:
            pytest.skip("pre_load not supported")

        result = impl.load(WithClassMethodPreLoad, b'{"value":"HELLO"}')
        assert result == WithClassMethodPreLoad(value="hello")

    def test_programmatic_add(self, impl: Serializer) -> None:
        if not impl.supports_pre_load:
            pytest.skip("pre_load not supported")

        @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
        class WithAddedPreLoad:
            value: str

        mr.add_pre_load(WithAddedPreLoad, lambda data: {**data, "value": data["value"] + "_added"})

        result = impl.load(WithAddedPreLoad, b'{"value":"test"}')
        assert result == WithAddedPreLoad(value="test_added")

    def test_normalizes_unknown_field_names(self, impl: Serializer) -> None:
        if not impl.supports_pre_load:
            pytest.skip("pre_load not supported")

        result = impl.load(WithFieldNameNormalization, b'{"id":"test123"}')
        assert result == WithFieldNameNormalization(value="test123")


class TestPreLoadNukedError:
    def test_raises_on_pre_load(self, impl: Serializer) -> None:
        if impl.supports_pre_load:
            result = impl.load(WithPreLoad, b'{"value":"hello"}')
            assert result == WithPreLoad(value="HELLO")
        else:
            with pytest.raises(TypeError, match="pre_load hooks are not supported in nuked"):
                impl.load(WithPreLoad, b'{"value":"hello"}')

    def test_raises_on_nested_pre_load(self, impl: Serializer) -> None:
        @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
        class Outer:
            inner: WithPreLoad

        if impl.supports_pre_load:
            result = impl.load(Outer, b'{"inner":{"value":"hello"}}')
            assert result == Outer(inner=WithPreLoad(value="HELLO"))
        else:
            with pytest.raises(TypeError, match="pre_load hooks are not supported in nuked: WithPreLoad"):
                impl.load(Outer, b'{"inner":{"value":"hello"}}')


class TestGetPreLoads:
    def test_returns_methods(self) -> None:
        pre_loads = mr.hooks.get_pre_loads(WithPreLoad)
        assert len(pre_loads) == 1
        assert pre_loads[0]({"value": "test"}) == {"value": "TEST"}

    def test_multiple(self) -> None:
        pre_loads = mr.hooks.get_pre_loads(WithMultiplePreLoads)
        assert len(pre_loads) == 2
