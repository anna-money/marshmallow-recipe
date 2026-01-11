import datetime
import decimal
import json
import uuid
from collections.abc import Mapping, Sequence
from typing import Any

import marshmallow
import pytest

import marshmallow_recipe as mr

from .conftest import (
    Address,
    CollectionHolder,
    ListOf,
    OptionalListOf,
    Priority,
    Serializer,
    Status,
    WithListInvalidError,
    WithListItemTwoValidators,
    WithListItemValidation,
    WithListMissing,
    WithListNoneError,
    WithListRequiredError,
    WithListStripWhitespace,
)


class TestListDump:
    @pytest.mark.parametrize(
        ("item_type", "value", "expected"),
        [
            pytest.param(str, ["a", "b", "c"], b'{"items":["a","b","c"]}', id="str"),
            pytest.param(int, [1, 2, 3], b'{"items":[1,2,3]}', id="int"),
            pytest.param(float, [1.5, 2.5, 3.5], b'{"items":[1.5,2.5,3.5]}', id="float"),
            pytest.param(bool, [True, False, True], b'{"items":[true,false,true]}', id="bool"),
            pytest.param(
                decimal.Decimal,
                [decimal.Decimal("1.23"), decimal.Decimal("4.56")],
                b'{"items":["1.23","4.56"]}',
                id="decimal",
            ),
            pytest.param(
                uuid.UUID,
                [uuid.UUID("12345678-1234-5678-1234-567812345678"), uuid.UUID("87654321-4321-8765-4321-876543218765")],
                b'{"items":["12345678-1234-5678-1234-567812345678","87654321-4321-8765-4321-876543218765"]}',
                id="uuid",
            ),
            pytest.param(
                datetime.datetime,
                [datetime.datetime(2024, 1, 15, 10, 30, 0, tzinfo=datetime.UTC)],
                b'{"items":["2024-01-15T10:30:00+00:00"]}',
                id="datetime",
            ),
            pytest.param(datetime.date, [datetime.date(2024, 1, 15)], b'{"items":["2024-01-15"]}', id="date"),
            pytest.param(datetime.time, [datetime.time(10, 30, 0)], b'{"items":["10:30:00"]}', id="time"),
            pytest.param(Status, [Status.ACTIVE, Status.PENDING], b'{"items":["active","pending"]}', id="str_enum"),
            pytest.param(Priority, [Priority.LOW, Priority.HIGH], b'{"items":[1,3]}', id="int_enum"),
        ],
    )
    def test_value(self, impl: Serializer, item_type: type, value: list, expected: bytes) -> None:
        obj = ListOf[item_type](items=value)
        result = impl.dump(ListOf[item_type], obj)
        assert result == expected

    def test_dataclass(self, impl: Serializer) -> None:
        addr = Address(street="Main St", city="NYC", zip_code="10001")
        obj = ListOf[Address](items=[addr])
        result = impl.dump(ListOf[Address], obj)
        assert json.loads(result) == {"items": [{"street": "Main St", "city": "NYC", "zip_code": "10001"}]}

    def test_nested_list(self, impl: Serializer) -> None:
        obj = ListOf[list[int]](items=[[1, 2], [3, 4]])
        result = impl.dump(ListOf[list[int]], obj)
        assert result == b'{"items":[[1,2],[3,4]]}'

    def test_deeply_nested_list(self, impl: Serializer) -> None:
        obj = ListOf[list[list[int]]](items=[[[1, 2], [3, 4]], [[5, 6], [7, 8]]])
        result = impl.dump(ListOf[list[list[int]]], obj)
        assert result == b'{"items":[[[1,2],[3,4]],[[5,6],[7,8]]]}'

    def test_nested_dict(self, impl: Serializer) -> None:
        obj = ListOf[dict[str, int]](items=[{"a": 1}, {"b": 2}])
        result = impl.dump(ListOf[dict[str, int]], obj)
        assert result == b'{"items":[{"a":1},{"b":2}]}'

    def test_sequence(self, impl: Serializer) -> None:
        obj = ListOf[Sequence[int]](items=[[1, 2], [3, 4]])
        result = impl.dump(ListOf[Sequence[int]], obj)
        assert result == b'{"items":[[1,2],[3,4]]}'

    def test_mapping(self, impl: Serializer) -> None:
        obj = ListOf[Mapping[str, int]](items=[{"a": 1}, {"b": 2}])
        result = impl.dump(ListOf[Mapping[str, int]], obj)
        assert result == b'{"items":[{"a":1},{"b":2}]}'

    def test_optional_element(self, impl: Serializer) -> None:
        obj = ListOf[int | None](items=[1, None, 3])
        result = impl.dump(ListOf[int | None], obj)
        assert result == b'{"items":[1,null,3]}'

    def test_any(self, impl: Serializer) -> None:
        obj = ListOf[Any](items=[1, "two", 3.0, True, None])
        result = impl.dump(ListOf[Any], obj)
        assert result == b'{"items":[1,"two",3.0,true,null]}'

    def test_empty(self, impl: Serializer) -> None:
        obj = ListOf[int](items=[])
        result = impl.dump(ListOf[int], obj)
        assert result == b'{"items":[]}'

    def test_single_element(self, impl: Serializer) -> None:
        obj = ListOf[int](items=[42])
        result = impl.dump(ListOf[int], obj)
        assert result == b'{"items":[42]}'

    def test_large_list(self, impl: Serializer) -> None:
        items = list(range(1000))
        obj = ListOf[int](items=items)
        result = impl.dump(ListOf[int], obj)
        parsed = json.loads(result)
        assert parsed["items"] == items

    def test_optional_none(self, impl: Serializer) -> None:
        obj = OptionalListOf[int](items=None)
        result = impl.dump(OptionalListOf[int], obj)
        assert result == b"{}"

    def test_optional_value(self, impl: Serializer) -> None:
        obj = OptionalListOf[int](items=[1, 2, 3])
        result = impl.dump(OptionalListOf[int], obj)
        assert result == b'{"items":[1,2,3]}'

    def test_none_handling_ignore_explicit(self, impl: Serializer) -> None:
        obj = OptionalListOf[int](items=None)
        result = impl.dump(OptionalListOf[int], obj, none_value_handling=mr.NoneValueHandling.IGNORE)
        assert result == b"{}"

    def test_none_handling_include(self, impl: Serializer) -> None:
        obj = OptionalListOf[int](items=None)
        result = impl.dump(OptionalListOf[int], obj, none_value_handling=mr.NoneValueHandling.INCLUDE)
        assert result == b'{"items":null}'

    def test_none_handling_include_with_value(self, impl: Serializer) -> None:
        obj = OptionalListOf[int](items=[1, 2, 3])
        result = impl.dump(OptionalListOf[int], obj, none_value_handling=mr.NoneValueHandling.INCLUDE)
        assert result == b'{"items":[1,2,3]}'

    def test_item_validation(self, impl: Serializer) -> None:
        obj = WithListItemValidation(items=[5, 10, 15])
        result = impl.dump(WithListItemValidation, obj)
        assert result == b'{"items":[5,10,15]}'

    def test_missing(self, impl: Serializer) -> None:
        obj = WithListMissing()
        result = impl.dump(WithListMissing, obj)
        assert result == b"{}"

    def test_missing_with_value(self, impl: Serializer) -> None:
        obj = WithListMissing(items=[1, 2, 3])
        result = impl.dump(WithListMissing, obj)
        assert result == b'{"items":[1,2,3]}'

    def test_unsubscripted(self, impl: Serializer) -> None:
        obj = CollectionHolder[list](items=["str", 123, {"a": "s"}])
        result = impl.dump(CollectionHolder[list], obj)
        assert result == b'{"items":["str",123,{"a":"s"}]}'


class TestListLoad:
    @pytest.mark.parametrize(
        ("item_type", "data", "expected_items"),
        [
            pytest.param(str, b'{"items":["a","b","c"]}', ["a", "b", "c"], id="str"),
            pytest.param(int, b'{"items":[1,2,3]}', [1, 2, 3], id="int"),
            pytest.param(float, b'{"items":[1.5,2.5,3.5]}', [1.5, 2.5, 3.5], id="float"),
            pytest.param(bool, b'{"items":[true,false,true]}', [True, False, True], id="bool"),
            pytest.param(
                decimal.Decimal,
                b'{"items":["1.23","4.56"]}',
                [decimal.Decimal("1.23"), decimal.Decimal("4.56")],
                id="decimal",
            ),
            pytest.param(
                uuid.UUID,
                b'{"items":["12345678-1234-5678-1234-567812345678","87654321-4321-8765-4321-876543218765"]}',
                [uuid.UUID("12345678-1234-5678-1234-567812345678"), uuid.UUID("87654321-4321-8765-4321-876543218765")],
                id="uuid",
            ),
            pytest.param(
                datetime.datetime,
                b'{"items":["2024-01-15T10:30:00+00:00"]}',
                [datetime.datetime(2024, 1, 15, 10, 30, 0, tzinfo=datetime.UTC)],
                id="datetime",
            ),
            pytest.param(datetime.date, b'{"items":["2024-01-15"]}', [datetime.date(2024, 1, 15)], id="date"),
            pytest.param(datetime.time, b'{"items":["10:30:00"]}', [datetime.time(10, 30, 0)], id="time"),
            pytest.param(Status, b'{"items":["active","pending"]}', [Status.ACTIVE, Status.PENDING], id="str_enum"),
            pytest.param(Priority, b'{"items":[1,3]}', [Priority.LOW, Priority.HIGH], id="int_enum"),
        ],
    )
    def test_value(self, impl: Serializer, item_type: type, data: bytes, expected_items: list) -> None:
        result = impl.load(ListOf[item_type], data)
        assert result == ListOf[item_type](items=expected_items)

    def test_dataclass(self, impl: Serializer) -> None:
        addr = Address(street="Main St", city="NYC", zip_code="10001")
        data = b'{"items":[{"street":"Main St","city":"NYC","zip_code":"10001"}]}'
        result = impl.load(ListOf[Address], data)
        assert result == ListOf[Address](items=[addr])

    def test_nested_list(self, impl: Serializer) -> None:
        data = b'{"items":[[1,2],[3,4]]}'
        result = impl.load(ListOf[list[int]], data)
        assert result == ListOf[list[int]](items=[[1, 2], [3, 4]])

    def test_deeply_nested_list(self, impl: Serializer) -> None:
        data = b'{"items":[[[1,2],[3,4]],[[5,6],[7,8]]]}'
        result = impl.load(ListOf[list[list[int]]], data)
        assert result == ListOf[list[list[int]]](items=[[[1, 2], [3, 4]], [[5, 6], [7, 8]]])

    def test_nested_dict(self, impl: Serializer) -> None:
        data = b'{"items":[{"a":1},{"b":2}]}'
        result = impl.load(ListOf[dict[str, int]], data)
        assert result == ListOf[dict[str, int]](items=[{"a": 1}, {"b": 2}])

    def test_sequence(self, impl: Serializer) -> None:
        data = b'{"items":[[1,2],[3,4]]}'
        result = impl.load(ListOf[Sequence[int]], data)
        assert result == ListOf[Sequence[int]](items=[[1, 2], [3, 4]])

    def test_mapping(self, impl: Serializer) -> None:
        data = b'{"items":[{"a":1},{"b":2}]}'
        result = impl.load(ListOf[Mapping[str, int]], data)
        assert result == ListOf[Mapping[str, int]](items=[{"a": 1}, {"b": 2}])

    def test_optional_element(self, impl: Serializer) -> None:
        data = b'{"items":[1,null,3]}'
        result = impl.load(ListOf[int | None], data)
        assert result == ListOf[int | None](items=[1, None, 3])

    def test_any(self, impl: Serializer) -> None:
        data = b'{"items":[1,"two",3.0,true,null]}'
        result = impl.load(ListOf[Any], data)
        assert result == ListOf[Any](items=[1, "two", 3.0, True, None])

    def test_empty(self, impl: Serializer) -> None:
        data = b'{"items":[]}'
        result = impl.load(ListOf[int], data)
        assert result == ListOf[int](items=[])

    def test_single_element(self, impl: Serializer) -> None:
        data = b'{"items":[42]}'
        result = impl.load(ListOf[int], data)
        assert result == ListOf[int](items=[42])

    def test_large_list(self, impl: Serializer) -> None:
        items = list(range(1000))
        data = json.dumps({"items": items}).encode()
        result = impl.load(ListOf[int], data)
        assert result == ListOf[int](items=items)

    def test_optional_none(self, impl: Serializer) -> None:
        data = b"{}"
        result = impl.load(OptionalListOf[int], data)
        assert result == OptionalListOf[int](items=None)

    def test_optional_value(self, impl: Serializer) -> None:
        data = b'{"items":[1,2,3]}'
        result = impl.load(OptionalListOf[int], data)
        assert result == OptionalListOf[int](items=[1, 2, 3])

    def test_item_validation_pass(self, impl: Serializer) -> None:
        data = b'{"items":[1,2,3]}'
        result = impl.load(WithListItemValidation, data)
        assert result == WithListItemValidation(items=[1, 2, 3])

    @pytest.mark.parametrize("data", [b'{"items":[1,0,3]}', b'{"items":[1,-5,3]}'])
    def test_item_validation_fail(self, impl: Serializer, data: bytes) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithListItemValidation, data)
        assert exc.value.messages == {"items": {1: ["Invalid value."]}}

    def test_item_two_validators_pass(self, impl: Serializer) -> None:
        data = b'{"items":[1,50,99]}'
        result = impl.load(WithListItemTwoValidators, data)
        assert result == WithListItemTwoValidators(items=[1, 50, 99])

    @pytest.mark.parametrize("data", [b'{"items":[1,0,50]}', b'{"items":[1,150,50]}'])
    def test_item_two_validators_fail(self, impl: Serializer, data: bytes) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithListItemTwoValidators, data)
        assert exc.value.messages == {"items": {1: ["Invalid value."]}}

    def test_item_wrong_type(self, impl: Serializer) -> None:
        data = b'{"items":[1,"not_int",3]}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ListOf[int], data)
        assert exc.value.messages == {"items": {1: ["Not a valid integer."]}}

    @pytest.mark.parametrize("data", [b'{"items":"not_a_list"}', b'{"items":{"key":1}}'])
    def test_wrong_type(self, impl: Serializer, data: bytes) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ListOf[int], data)
        assert exc.value.messages == {"items": ["Not a valid list."]}

    def test_missing_required(self, impl: Serializer) -> None:
        data = b"{}"
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ListOf[int], data)
        assert exc.value.messages == {"items": ["Missing data for required field."]}

    def test_custom_required_error(self, impl: Serializer) -> None:
        data = b"{}"
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithListRequiredError, data)
        assert exc.value.messages == {"items": ["Custom required message"]}

    def test_custom_none_error(self, impl: Serializer) -> None:
        data = b'{"items":null}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithListNoneError, data)
        assert exc.value.messages == {"items": ["Custom none message"]}

    def test_custom_invalid_error(self, impl: Serializer) -> None:
        data = b'{"items":"not_a_list"}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithListInvalidError, data)
        assert exc.value.messages == {"items": ["Custom invalid message"]}

    def test_missing(self, impl: Serializer) -> None:
        data = b"{}"
        result = impl.load(WithListMissing, data)
        assert result == WithListMissing()

    def test_missing_with_value(self, impl: Serializer) -> None:
        data = b'{"items":[1,2,3]}'
        result = impl.load(WithListMissing, data)
        assert result == WithListMissing(items=[1, 2, 3])

    def test_strip_whitespace(self, impl: Serializer) -> None:
        data = b'{"items":[" hello "," world "]}'
        result = impl.load(WithListStripWhitespace, data)
        assert result == WithListStripWhitespace(items=["hello", "world"])


class TestListEdgeCases:
    """Test list edge cases like multiple nulls and deep nesting."""

    def test_multiple_nulls(self, impl: Serializer) -> None:
        obj = ListOf[int | None](items=[None, None, 1, None])
        result = impl.dump(ListOf[int | None], obj)
        assert result == b'{"items":[null,null,1,null]}'

    def test_multiple_nulls_load(self, impl: Serializer) -> None:
        data = b'{"items":[null,null,1,null]}'
        result = impl.load(ListOf[int | None], data)
        assert result == ListOf[int | None](items=[None, None, 1, None])

    def test_all_nulls(self, impl: Serializer) -> None:
        obj = ListOf[int | None](items=[None, None, None])
        result = impl.dump(ListOf[int | None], obj)
        assert result == b'{"items":[null,null,null]}'

    def test_all_nulls_load(self, impl: Serializer) -> None:
        data = b'{"items":[null,null,null]}'
        result = impl.load(ListOf[int | None], data)
        assert result == ListOf[int | None](items=[None, None, None])

    def test_4_levels_nested(self, impl: Serializer) -> None:
        obj = ListOf[list[list[list[int]]]](items=[[[[1, 2], [3, 4]], [[5, 6], [7, 8]]]])
        result = impl.dump(ListOf[list[list[list[int]]]], obj)
        assert result == b'{"items":[[[[1,2],[3,4]],[[5,6],[7,8]]]]}'

    def test_4_levels_nested_load(self, impl: Serializer) -> None:
        data = b'{"items":[[[[1,2],[3,4]],[[5,6],[7,8]]]]}'
        result = impl.load(ListOf[list[list[list[int]]]], data)
        assert result == ListOf[list[list[list[int]]]](items=[[[[1, 2], [3, 4]], [[5, 6], [7, 8]]]])

    def test_mixed_types_in_any(self, impl: Serializer) -> None:
        obj = ListOf[Any](items=[1, "two", 3.0, True, None, {"a": 1}, [1, 2, 3]])
        result = impl.dump(ListOf[Any], obj)
        assert result == b'{"items":[1,"two",3.0,true,null,{"a":1},[1,2,3]]}'


class TestListDumpInvalidType:
    """Test that invalid types in list fields raise ValidationError on dump."""

    @pytest.mark.parametrize("value", ["not a list", {"a": 1}, 123, (1, 2, 3)])
    def test_invalid_type(self, impl: Serializer, value: object) -> None:
        obj = ListOf[int](**{"items": value})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(ListOf[int], obj)
