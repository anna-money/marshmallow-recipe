import dataclasses
import types
from collections.abc import Iterator
from typing import Any

import marshmallow
import pytest

import marshmallow_recipe as mr

from .conftest import Address, DictOf, Person, SimpleTypes


class TestMappingInputLoad:
    def test_root_mapping_proxy_loads_dataclass(self) -> None:
        result = mr.nuked.load(SimpleTypes, types.MappingProxyType({"name": "alice", "age": 30}))
        assert result == SimpleTypes(name="alice", age=30)

    def test_root_mapping_proxy_missing_required_raises(self) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            mr.nuked.load(SimpleTypes, types.MappingProxyType({"name": "alice"}))
        assert exc.value.messages == {"age": ["Missing data for required field."]}

    @pytest.mark.parametrize(
        "data",
        [
            pytest.param("not a dict", id="str"),
            pytest.param([1, 2, 3], id="list"),
            pytest.param(42, id="int"),
            pytest.param((1, 2), id="tuple"),
        ],
    )
    def test_root_non_mapping_raises(self, data: object) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            mr.nuked.load(SimpleTypes, data)  # type: ignore[arg-type]
        assert exc.value.messages == {"_schema": ["Invalid input type."]}

    def test_root_dict_collection_with_mapping_proxy(self) -> None:
        result = mr.nuked.load(dict[str, int], types.MappingProxyType({"a": 1, "b": 2}))
        assert result == {"a": 1, "b": 2}

    def test_dict_field_with_mapping_proxy_value(self) -> None:
        result = mr.nuked.load(DictOf[str, int], {"data": types.MappingProxyType({"a": 1, "b": 2})})
        assert result == DictOf[str, int](data={"a": 1, "b": 2})

    def test_nested_dataclass_with_mapping_proxy(self) -> None:
        address = types.MappingProxyType({"street": "Main St", "city": "NYC", "zip_code": "10001"})
        result = mr.nuked.load(Person, types.MappingProxyType({"name": "Bob", "age": 40, "address": address}))
        assert result == Person(name="Bob", age=40, address=Address(street="Main St", city="NYC", zip_code="10001"))

    def test_load_many_via_schema_accepts_iterator(self) -> None:
        schema = mr.nuked.schema(SimpleTypes, many=True)

        def gen() -> Iterator[Any]:
            yield types.MappingProxyType({"name": "a", "age": 1})
            yield types.MappingProxyType({"name": "b", "age": 2})

        result = schema.load(gen())
        assert result == [SimpleTypes(name="a", age=1), SimpleTypes(name="b", age=2)]

    def test_pre_load_hook_still_works_with_mapping_proxy(self) -> None:
        @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
        class WithPreLoadLocal:
            value: str

            @staticmethod
            @mr.pre_load
            def pre_load(data: dict[str, Any]) -> dict[str, Any]:
                data["value"] = data["value"].upper()
                return data

        result = mr.nuked.load(WithPreLoadLocal, types.MappingProxyType({"value": "hello"}))
        assert result == WithPreLoadLocal(value="HELLO")
