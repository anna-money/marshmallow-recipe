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
    OptionalTupleOf,
    Priority,
    Serializer,
    Status,
    TupleOf,
    WithTupleInvalidError,
    WithTupleItemTwoValidators,
    WithTupleItemValidation,
    WithTupleMissing,
    WithTupleNoneError,
    WithTupleRequiredError,
)


class TestTupleDump:
    @pytest.mark.parametrize(
        ("item_type", "value", "expected"),
        [
            pytest.param(str, ("a", "b", "c"), b'{"items":["a","b","c"]}', id="str"),
            pytest.param(int, (1, 2, 3), b'{"items":[1,2,3]}', id="int"),
            pytest.param(float, (1.5, 2.5, 3.5), b'{"items":[1.5,2.5,3.5]}', id="float"),
            pytest.param(bool, (True, False, True), b'{"items":[true,false,true]}', id="bool"),
            pytest.param(
                decimal.Decimal,
                (decimal.Decimal("1.23"), decimal.Decimal("4.56")),
                b'{"items":["1.23","4.56"]}',
                id="decimal",
            ),
            pytest.param(
                uuid.UUID,
                (uuid.UUID("12345678-1234-5678-1234-567812345678"), uuid.UUID("87654321-4321-8765-4321-876543218765")),
                b'{"items":["12345678-1234-5678-1234-567812345678","87654321-4321-8765-4321-876543218765"]}',
                id="uuid",
            ),
            pytest.param(
                datetime.datetime,
                (datetime.datetime(2024, 1, 15, 10, 30, 0, tzinfo=datetime.UTC),),
                b'{"items":["2024-01-15T10:30:00+00:00"]}',
                id="datetime",
            ),
            pytest.param(datetime.date, (datetime.date(2024, 1, 15),), b'{"items":["2024-01-15"]}', id="date"),
            pytest.param(datetime.time, (datetime.time(10, 30, 0),), b'{"items":["10:30:00"]}', id="time"),
            pytest.param(Status, (Status.ACTIVE, Status.PENDING), b'{"items":["active","pending"]}', id="str_enum"),
            pytest.param(Priority, (Priority.LOW, Priority.HIGH), b'{"items":[1,3]}', id="int_enum"),
        ],
    )
    def test_value(self, impl: Serializer, item_type: type, value: tuple, expected: bytes) -> None:
        obj = TupleOf[item_type](items=value)
        result = impl.dump(TupleOf[item_type], obj)
        assert result == expected

    def test_dataclass(self, impl: Serializer) -> None:
        addr = Address(street="Main St", city="NYC", zip_code="10001")
        obj = TupleOf[Address](items=(addr,))
        result = impl.dump(TupleOf[Address], obj)
        assert json.loads(result) == {"items": [{"street": "Main St", "city": "NYC", "zip_code": "10001"}]}

    def test_nested_list(self, impl: Serializer) -> None:
        obj = TupleOf[list[int]](items=([1, 2], [3, 4]))
        result = impl.dump(TupleOf[list[int]], obj)
        assert result == b'{"items":[[1,2],[3,4]]}'

    def test_nested_dict(self, impl: Serializer) -> None:
        obj = TupleOf[dict[str, int]](items=({"a": 1}, {"b": 2}))
        result = impl.dump(TupleOf[dict[str, int]], obj)
        assert result == b'{"items":[{"a":1},{"b":2}]}'

    def test_sequence(self, impl: Serializer) -> None:
        obj = TupleOf[Sequence[int]](items=([1, 2], [3, 4]))
        result = impl.dump(TupleOf[Sequence[int]], obj)
        assert result == b'{"items":[[1,2],[3,4]]}'

    def test_mapping(self, impl: Serializer) -> None:
        obj = TupleOf[Mapping[str, int]](items=({"a": 1}, {"b": 2}))
        result = impl.dump(TupleOf[Mapping[str, int]], obj)
        assert result == b'{"items":[{"a":1},{"b":2}]}'

    def test_optional_element(self, impl: Serializer) -> None:
        obj = TupleOf[int | None](items=(1, None, 3))
        result = impl.dump(TupleOf[int | None], obj)
        assert result == b'{"items":[1,null,3]}'

    def test_any(self, impl: Serializer) -> None:
        obj = TupleOf[Any](items=(1, "two", 3.0, True, None))
        result = impl.dump(TupleOf[Any], obj)
        assert result == b'{"items":[1,"two",3.0,true,null]}'

    def test_empty(self, impl: Serializer) -> None:
        obj = TupleOf[int](items=())
        result = impl.dump(TupleOf[int], obj)
        assert result == b'{"items":[]}'

    def test_single_element(self, impl: Serializer) -> None:
        obj = TupleOf[int](items=(42,))
        result = impl.dump(TupleOf[int], obj)
        assert result == b'{"items":[42]}'

    def test_many_elements(self, impl: Serializer) -> None:
        items = tuple(range(100))
        obj = TupleOf[int](items=items)
        result = impl.dump(TupleOf[int], obj)
        parsed = json.loads(result)
        assert tuple(parsed["items"]) == items

    def test_optional_none(self, impl: Serializer) -> None:
        obj = OptionalTupleOf[int](items=None)
        result = impl.dump(OptionalTupleOf[int], obj)
        assert result == b"{}"

    def test_optional_value(self, impl: Serializer) -> None:
        obj = OptionalTupleOf[int](items=(1, 2, 3))
        result = impl.dump(OptionalTupleOf[int], obj)
        assert result == b'{"items":[1,2,3]}'

    def test_none_handling_ignore_explicit(self, impl: Serializer) -> None:
        obj = OptionalTupleOf[int](items=None)
        result = impl.dump(OptionalTupleOf[int], obj, none_value_handling=mr.NoneValueHandling.IGNORE)
        assert result == b"{}"

    def test_none_handling_include(self, impl: Serializer) -> None:
        obj = OptionalTupleOf[int](items=None)
        result = impl.dump(OptionalTupleOf[int], obj, none_value_handling=mr.NoneValueHandling.INCLUDE)
        assert result == b'{"items":null}'

    def test_none_handling_include_with_value(self, impl: Serializer) -> None:
        obj = OptionalTupleOf[int](items=(1, 2, 3))
        result = impl.dump(OptionalTupleOf[int], obj, none_value_handling=mr.NoneValueHandling.INCLUDE)
        assert result == b'{"items":[1,2,3]}'

    def test_missing(self, impl: Serializer) -> None:
        obj = WithTupleMissing()
        result = impl.dump(WithTupleMissing, obj)
        assert result == b"{}"

    def test_missing_with_value(self, impl: Serializer) -> None:
        obj = WithTupleMissing(items=(1, 2, 3))
        result = impl.dump(WithTupleMissing, obj)
        assert result == b'{"items":[1,2,3]}'

    def test_unsubscripted(self, impl: Serializer) -> None:
        obj = CollectionHolder[tuple](items=(99, "xx"))
        result = impl.dump(CollectionHolder[tuple], obj)
        assert result == b'{"items":[99,"xx"]}'


class TestTupleLoad:
    @pytest.mark.parametrize(
        ("item_type", "data", "expected_items"),
        [
            pytest.param(str, b'{"items":["a","b","c"]}', ("a", "b", "c"), id="str"),
            pytest.param(int, b'{"items":[1,2,3]}', (1, 2, 3), id="int"),
            pytest.param(float, b'{"items":[1.5,2.5,3.5]}', (1.5, 2.5, 3.5), id="float"),
            pytest.param(bool, b'{"items":[true,false,true]}', (True, False, True), id="bool"),
            pytest.param(
                decimal.Decimal,
                b'{"items":["1.23","4.56"]}',
                (decimal.Decimal("1.23"), decimal.Decimal("4.56")),
                id="decimal",
            ),
            pytest.param(
                uuid.UUID,
                b'{"items":["12345678-1234-5678-1234-567812345678","87654321-4321-8765-4321-876543218765"]}',
                (uuid.UUID("12345678-1234-5678-1234-567812345678"), uuid.UUID("87654321-4321-8765-4321-876543218765")),
                id="uuid",
            ),
            pytest.param(
                datetime.datetime,
                b'{"items":["2024-01-15T10:30:00+00:00"]}',
                (datetime.datetime(2024, 1, 15, 10, 30, 0, tzinfo=datetime.UTC),),
                id="datetime",
            ),
            pytest.param(datetime.date, b'{"items":["2024-01-15"]}', (datetime.date(2024, 1, 15),), id="date"),
            pytest.param(datetime.time, b'{"items":["10:30:00"]}', (datetime.time(10, 30, 0),), id="time"),
            pytest.param(Status, b'{"items":["active","pending"]}', (Status.ACTIVE, Status.PENDING), id="str_enum"),
            pytest.param(Priority, b'{"items":[1,3]}', (Priority.LOW, Priority.HIGH), id="int_enum"),
        ],
    )
    def test_value(self, impl: Serializer, item_type: type, data: bytes, expected_items: tuple) -> None:
        result = impl.load(TupleOf[item_type], data)
        assert result == TupleOf[item_type](items=expected_items)

    def test_dataclass(self, impl: Serializer) -> None:
        addr = Address(street="Main St", city="NYC", zip_code="10001")
        data = b'{"items":[{"street":"Main St","city":"NYC","zip_code":"10001"}]}'
        result = impl.load(TupleOf[Address], data)
        assert result == TupleOf[Address](items=(addr,))

    def test_nested_list(self, impl: Serializer) -> None:
        data = b'{"items":[[1,2],[3,4]]}'
        result = impl.load(TupleOf[list[int]], data)
        assert result == TupleOf[list[int]](items=([1, 2], [3, 4]))

    def test_nested_dict(self, impl: Serializer) -> None:
        data = b'{"items":[{"a":1},{"b":2}]}'
        result = impl.load(TupleOf[dict[str, int]], data)
        assert result == TupleOf[dict[str, int]](items=({"a": 1}, {"b": 2}))

    def test_sequence(self, impl: Serializer) -> None:
        data = b'{"items":[[1,2],[3,4]]}'
        result = impl.load(TupleOf[Sequence[int]], data)
        assert result == TupleOf[Sequence[int]](items=([1, 2], [3, 4]))

    def test_mapping(self, impl: Serializer) -> None:
        data = b'{"items":[{"a":1},{"b":2}]}'
        result = impl.load(TupleOf[Mapping[str, int]], data)
        assert result == TupleOf[Mapping[str, int]](items=({"a": 1}, {"b": 2}))

    def test_optional_element(self, impl: Serializer) -> None:
        data = b'{"items":[1,null,3]}'
        result = impl.load(TupleOf[int | None], data)
        assert result == TupleOf[int | None](items=(1, None, 3))

    def test_any(self, impl: Serializer) -> None:
        data = b'{"items":[1,"two",3.0,true,null]}'
        result = impl.load(TupleOf[Any], data)
        assert result == TupleOf[Any](items=(1, "two", 3.0, True, None))

    def test_empty(self, impl: Serializer) -> None:
        data = b'{"items":[]}'
        result = impl.load(TupleOf[int], data)
        assert result == TupleOf[int](items=())

    def test_single_element(self, impl: Serializer) -> None:
        data = b'{"items":[42]}'
        result = impl.load(TupleOf[int], data)
        assert result == TupleOf[int](items=(42,))

    def test_many_elements(self, impl: Serializer) -> None:
        items = list(range(100))
        data = json.dumps({"items": items}).encode()
        result = impl.load(TupleOf[int], data)
        assert result == TupleOf[int](items=tuple(items))

    def test_optional_none(self, impl: Serializer) -> None:
        data = b"{}"
        result = impl.load(OptionalTupleOf[int], data)
        assert result == OptionalTupleOf[int](items=None)

    def test_optional_value(self, impl: Serializer) -> None:
        data = b'{"items":[1,2,3]}'
        result = impl.load(OptionalTupleOf[int], data)
        assert result == OptionalTupleOf[int](items=(1, 2, 3))

    def test_item_validation_pass(self, impl: Serializer) -> None:
        data = b'{"values":[1,2,3]}'
        result = impl.load(WithTupleItemValidation, data)
        assert result == WithTupleItemValidation(values=(1, 2, 3))

    def test_item_validation_zero_fail(self, impl: Serializer) -> None:
        data = b'{"values":[1,0,3]}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithTupleItemValidation, data)
        assert exc.value.messages == {"values": {1: ["Invalid value."]}}

    def test_item_two_validators_pass(self, impl: Serializer) -> None:
        data = b'{"values":[1,50,99]}'
        result = impl.load(WithTupleItemTwoValidators, data)
        assert result == WithTupleItemTwoValidators(values=(1, 50, 99))

    @pytest.mark.parametrize("data", [b'{"values":[1,0,50]}', b'{"values":[1,150,50]}'])
    def test_item_two_validators_fail(self, impl: Serializer, data: bytes) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithTupleItemTwoValidators, data)
        assert exc.value.messages == {"values": {1: ["Invalid value."]}}

    def test_item_wrong_type(self, impl: Serializer) -> None:
        data = b'{"items":[1,"not_int",3]}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(TupleOf[int], data)
        assert exc.value.messages == {"items": {1: ["Not a valid integer."]}}

    @pytest.mark.parametrize("data", [b'{"items":"not_a_tuple"}', b'{"items":{"key":1}}'])
    def test_wrong_type(self, impl: Serializer, data: bytes) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(TupleOf[int], data)
        assert exc.value.messages == {"items": ["Not a valid tuple."]}

    def test_missing_required(self, impl: Serializer) -> None:
        data = b"{}"
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(TupleOf[int], data)
        assert exc.value.messages == {"items": ["Missing data for required field."]}

    def test_custom_required_error(self, impl: Serializer) -> None:
        data = b"{}"
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithTupleRequiredError, data)
        assert exc.value.messages == {"items": ["Custom required message"]}

    def test_custom_none_error(self, impl: Serializer) -> None:
        data = b'{"items":null}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithTupleNoneError, data)
        assert exc.value.messages == {"items": ["Custom none message"]}

    def test_custom_invalid_error(self, impl: Serializer) -> None:
        data = b'{"items":"not_a_tuple"}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithTupleInvalidError, data)
        assert exc.value.messages == {"items": ["Custom invalid message"]}

    def test_missing(self, impl: Serializer) -> None:
        data = b"{}"
        result = impl.load(WithTupleMissing, data)
        assert result == WithTupleMissing()

    def test_missing_with_value(self, impl: Serializer) -> None:
        data = b'{"items":[1,2,3]}'
        result = impl.load(WithTupleMissing, data)
        assert result == WithTupleMissing(items=(1, 2, 3))


class TestTupleEdgeCases:
    """Test tuple edge cases with multiple nulls, deep nesting, and boundaries."""

    def test_multiple_nulls(self, impl: Serializer) -> None:
        obj = TupleOf[int | None](items=(None, None, 1, None, 2))
        result = impl.dump(TupleOf[int | None], obj)
        assert result == b'{"items":[null,null,1,null,2]}'

    def test_multiple_nulls_load(self, impl: Serializer) -> None:
        data = b'{"items":[null,null,1,null,2]}'
        result = impl.load(TupleOf[int | None], data)
        assert result == TupleOf[int | None](items=(None, None, 1, None, 2))

    def test_all_nulls(self, impl: Serializer) -> None:
        obj = TupleOf[int | None](items=(None, None, None))
        result = impl.dump(TupleOf[int | None], obj)
        assert result == b'{"items":[null,null,null]}'

    def test_deeply_nested_tuple(self, impl: Serializer) -> None:
        obj = TupleOf[list[list[int]]](items=([[1, 2], [3, 4]], [[5, 6], [7, 8]]))
        result = impl.dump(TupleOf[list[list[int]]], obj)
        loaded = impl.load(TupleOf[list[list[int]]], result)
        assert loaded == obj

    def test_big_int_values(self, impl: Serializer) -> None:
        big_vals = (9223372036854775808, -9223372036854775809, 2**100)
        obj = TupleOf[int](items=big_vals)
        result = impl.dump(TupleOf[int], obj)
        loaded = impl.load(TupleOf[int], result)
        assert loaded.items == big_vals

    def test_unicode_string_values(self, impl: Serializer) -> None:
        unicode_vals = ("Привет", "你好", "🎉")
        obj = TupleOf[str](items=unicode_vals)
        result = impl.dump(TupleOf[str], obj)
        loaded = impl.load(TupleOf[str], result)
        assert loaded.items == unicode_vals

    def test_preserves_order(self, impl: Serializer) -> None:
        items = tuple(range(50, 0, -1))
        obj = TupleOf[int](items=items)
        result = impl.dump(TupleOf[int], obj)
        loaded = impl.load(TupleOf[int], result)
        assert loaded.items == items

    def test_duplicate_values_preserved(self, impl: Serializer) -> None:
        items = (1, 1, 2, 2, 3, 3, 1)
        obj = TupleOf[int](items=items)
        result = impl.dump(TupleOf[int], obj)
        loaded = impl.load(TupleOf[int], result)
        assert loaded.items == items


class TestTupleDumpInvalidType:
    """Test that invalid types in tuple fields raise ValidationError on dump."""

    @pytest.mark.parametrize("value", ["not a tuple", [1, 2, 3], 123, {"a": 1}])
    def test_invalid_type(self, impl: Serializer, value: object) -> None:
        obj = TupleOf[int](**{"items": value})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(TupleOf[int], obj)
