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
    OptionalSequenceOf,
    Priority,
    SequenceOf,
    Serializer,
    Status,
    WithSequenceInvalidError,
    WithSequenceMissing,
    WithSequenceNoneError,
    WithSequenceRequiredError,
    WithSequenceTwoValidators,
    WithSequenceValidation,
)


class TestSequenceDump:
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
        obj = SequenceOf[item_type](items=value)
        result = impl.dump(SequenceOf[item_type], obj)
        assert result == expected

    def test_dataclass(self, impl: Serializer) -> None:
        addr = Address(street="Main St", city="NYC", zip_code="10001")
        obj = SequenceOf[Address](items=[addr])
        result = impl.dump(SequenceOf[Address], obj)
        assert json.loads(result) == {"items": [{"street": "Main St", "city": "NYC", "zip_code": "10001"}]}

    def test_nested_list(self, impl: Serializer) -> None:
        obj = SequenceOf[list[int]](items=[[1, 2], [3, 4]])
        result = impl.dump(SequenceOf[list[int]], obj)
        assert result == b'{"items":[[1,2],[3,4]]}'

    def test_nested_dict(self, impl: Serializer) -> None:
        obj = SequenceOf[dict[str, int]](items=[{"a": 1}, {"b": 2}])
        result = impl.dump(SequenceOf[dict[str, int]], obj)
        assert result == b'{"items":[{"a":1},{"b":2}]}'

    def test_sequence(self, impl: Serializer) -> None:
        obj = SequenceOf[Sequence[int]](items=[[1, 2], [3, 4]])
        result = impl.dump(SequenceOf[Sequence[int]], obj)
        assert result == b'{"items":[[1,2],[3,4]]}'

    def test_mapping(self, impl: Serializer) -> None:
        obj = SequenceOf[Mapping[str, int]](items=[{"a": 1}, {"b": 2}])
        result = impl.dump(SequenceOf[Mapping[str, int]], obj)
        assert result == b'{"items":[{"a":1},{"b":2}]}'

    def test_optional_element(self, impl: Serializer) -> None:
        obj = SequenceOf[int | None](items=[1, None, 3])
        result = impl.dump(SequenceOf[int | None], obj)
        assert result == b'{"items":[1,null,3]}'

    def test_any(self, impl: Serializer) -> None:
        obj = SequenceOf[Any](items=[1, "two", 3.0, True, None])
        result = impl.dump(SequenceOf[Any], obj)
        assert result == b'{"items":[1,"two",3.0,true,null]}'

    def test_empty(self, impl: Serializer) -> None:
        obj = SequenceOf[int](items=[])
        result = impl.dump(SequenceOf[int], obj)
        assert result == b'{"items":[]}'

    def test_single_element(self, impl: Serializer) -> None:
        obj = SequenceOf[int](items=[42])
        result = impl.dump(SequenceOf[int], obj)
        assert result == b'{"items":[42]}'

    def test_large_sequence(self, impl: Serializer) -> None:
        items = list(range(500))
        obj = SequenceOf[int](items=items)
        result = impl.dump(SequenceOf[int], obj)
        parsed = json.loads(result)
        assert parsed["items"] == items

    def test_deeply_nested(self, impl: Serializer) -> None:
        obj = SequenceOf[Sequence[Sequence[int]]](items=[[[1, 2], [3, 4]], [[5, 6], [7, 8]]])
        result = impl.dump(SequenceOf[Sequence[Sequence[int]]], obj)
        assert result == b'{"items":[[[1,2],[3,4]],[[5,6],[7,8]]]}'

    def test_optional_none(self, impl: Serializer) -> None:
        obj = OptionalSequenceOf[int](items=None)
        result = impl.dump(OptionalSequenceOf[int], obj)
        assert result == b"{}"

    def test_optional_value(self, impl: Serializer) -> None:
        obj = OptionalSequenceOf[int](items=[1, 2, 3])
        result = impl.dump(OptionalSequenceOf[int], obj)
        assert result == b'{"items":[1,2,3]}'

    def test_none_handling_ignore_explicit(self, impl: Serializer) -> None:
        obj = OptionalSequenceOf[int](items=None)
        result = impl.dump(OptionalSequenceOf[int], obj, none_value_handling=mr.NoneValueHandling.IGNORE)
        assert result == b"{}"

    def test_none_handling_include(self, impl: Serializer) -> None:
        obj = OptionalSequenceOf[int](items=None)
        result = impl.dump(OptionalSequenceOf[int], obj, none_value_handling=mr.NoneValueHandling.INCLUDE)
        assert result == b'{"items":null}'

    def test_none_handling_include_with_value(self, impl: Serializer) -> None:
        obj = OptionalSequenceOf[int](items=[1, 2, 3])
        result = impl.dump(OptionalSequenceOf[int], obj, none_value_handling=mr.NoneValueHandling.INCLUDE)
        assert result == b'{"items":[1,2,3]}'

    def test_item_validation(self, impl: Serializer) -> None:
        obj = WithSequenceValidation(items=[5, 10, 15])
        result = impl.dump(WithSequenceValidation, obj)
        assert result == b'{"items":[5,10,15]}'

    def test_missing(self, impl: Serializer) -> None:
        obj = WithSequenceMissing()
        result = impl.dump(WithSequenceMissing, obj)
        assert result == b"{}"

    def test_missing_with_value(self, impl: Serializer) -> None:
        obj = WithSequenceMissing(items=[1, 2, 3])
        result = impl.dump(WithSequenceMissing, obj)
        assert result == b'{"items":[1,2,3]}'


class TestSequenceLoad:
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
        result = impl.load(SequenceOf[item_type], data)
        assert result == SequenceOf[item_type](items=expected_items)

    def test_dataclass(self, impl: Serializer) -> None:
        addr = Address(street="Main St", city="NYC", zip_code="10001")
        data = b'{"items":[{"street":"Main St","city":"NYC","zip_code":"10001"}]}'
        result = impl.load(SequenceOf[Address], data)
        assert result == SequenceOf[Address](items=[addr])

    def test_nested_list(self, impl: Serializer) -> None:
        data = b'{"items":[[1,2],[3,4]]}'
        result = impl.load(SequenceOf[list[int]], data)
        assert result == SequenceOf[list[int]](items=[[1, 2], [3, 4]])

    def test_nested_dict(self, impl: Serializer) -> None:
        data = b'{"items":[{"a":1},{"b":2}]}'
        result = impl.load(SequenceOf[dict[str, int]], data)
        assert result == SequenceOf[dict[str, int]](items=[{"a": 1}, {"b": 2}])

    def test_sequence(self, impl: Serializer) -> None:
        data = b'{"items":[[1,2],[3,4]]}'
        result = impl.load(SequenceOf[Sequence[int]], data)
        assert result == SequenceOf[Sequence[int]](items=[[1, 2], [3, 4]])

    def test_mapping(self, impl: Serializer) -> None:
        data = b'{"items":[{"a":1},{"b":2}]}'
        result = impl.load(SequenceOf[Mapping[str, int]], data)
        assert result == SequenceOf[Mapping[str, int]](items=[{"a": 1}, {"b": 2}])

    def test_optional_element(self, impl: Serializer) -> None:
        data = b'{"items":[1,null,3]}'
        result = impl.load(SequenceOf[int | None], data)
        assert result == SequenceOf[int | None](items=[1, None, 3])

    def test_any(self, impl: Serializer) -> None:
        data = b'{"items":[1,"two",3.0,true,null]}'
        result = impl.load(SequenceOf[Any], data)
        assert result == SequenceOf[Any](items=[1, "two", 3.0, True, None])

    def test_empty(self, impl: Serializer) -> None:
        data = b'{"items":[]}'
        result = impl.load(SequenceOf[int], data)
        assert result == SequenceOf[int](items=[])

    def test_single_element(self, impl: Serializer) -> None:
        data = b'{"items":[42]}'
        result = impl.load(SequenceOf[int], data)
        assert result == SequenceOf[int](items=[42])

    def test_large_sequence(self, impl: Serializer) -> None:
        items = list(range(500))
        data = json.dumps({"items": items}).encode()
        result = impl.load(SequenceOf[int], data)
        assert result == SequenceOf[int](items=items)

    def test_deeply_nested(self, impl: Serializer) -> None:
        data = b'{"items":[[[1,2],[3,4]],[[5,6],[7,8]]]}'
        result = impl.load(SequenceOf[Sequence[Sequence[int]]], data)
        assert result == SequenceOf[Sequence[Sequence[int]]](items=[[[1, 2], [3, 4]], [[5, 6], [7, 8]]])

    def test_optional_none(self, impl: Serializer) -> None:
        data = b"{}"
        result = impl.load(OptionalSequenceOf[int], data)
        assert result == OptionalSequenceOf[int](items=None)

    def test_optional_value(self, impl: Serializer) -> None:
        data = b'{"items":[1,2,3]}'
        result = impl.load(OptionalSequenceOf[int], data)
        assert result == OptionalSequenceOf[int](items=[1, 2, 3])

    def test_item_validation_pass(self, impl: Serializer) -> None:
        data = b'{"items":[1,2,3]}'
        result = impl.load(WithSequenceValidation, data)
        assert result == WithSequenceValidation(items=[1, 2, 3])

    def test_item_validation_negative_fail(self, impl: Serializer) -> None:
        data = b'{"items":[1,-1,3]}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithSequenceValidation, data)
        assert exc.value.messages == {"items": {1: ["Invalid value."]}}

    def test_item_two_validators_pass(self, impl: Serializer) -> None:
        data = b'{"items":[1,50,99]}'
        result = impl.load(WithSequenceTwoValidators, data)
        assert result == WithSequenceTwoValidators(items=[1, 50, 99])

    @pytest.mark.parametrize("data", [b'{"items":[1,0,50]}', b'{"items":[1,150,50]}'])
    def test_item_two_validators_fail(self, impl: Serializer, data: bytes) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithSequenceTwoValidators, data)
        assert exc.value.messages == {"items": {1: ["Invalid value."]}}

    def test_item_wrong_type(self, impl: Serializer) -> None:
        data = b'{"items":[1,"not_int",3]}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(SequenceOf[int], data)
        assert exc.value.messages == {"items": {1: ["Not a valid integer."]}}

    @pytest.mark.parametrize("data", [b'{"items":"not_a_sequence"}', b'{"items":{"key":1}}'])
    def test_wrong_type(self, impl: Serializer, data: bytes) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(SequenceOf[int], data)
        assert exc.value.messages == {"items": ["Not a valid list."]}

    def test_missing_required(self, impl: Serializer) -> None:
        data = b"{}"
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(SequenceOf[int], data)
        assert exc.value.messages == {"items": ["Missing data for required field."]}

    def test_custom_required_error(self, impl: Serializer) -> None:
        data = b"{}"
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithSequenceRequiredError, data)
        assert exc.value.messages == {"items": ["Custom required message"]}

    def test_custom_none_error(self, impl: Serializer) -> None:
        data = b'{"items":null}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithSequenceNoneError, data)
        assert exc.value.messages == {"items": ["Custom none message"]}

    def test_custom_invalid_error(self, impl: Serializer) -> None:
        data = b'{"items":"not_a_sequence"}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithSequenceInvalidError, data)
        assert exc.value.messages == {"items": ["Custom invalid message"]}

    def test_missing(self, impl: Serializer) -> None:
        data = b"{}"
        result = impl.load(WithSequenceMissing, data)
        assert result == WithSequenceMissing()

    def test_missing_with_value(self, impl: Serializer) -> None:
        data = b'{"items":[1,2,3]}'
        result = impl.load(WithSequenceMissing, data)
        assert result == WithSequenceMissing(items=[1, 2, 3])


class TestSequenceEdgeCases:
    """Test sequence edge cases with multiple nulls, big ints, and special scenarios."""

    def test_multiple_nulls(self, impl: Serializer) -> None:
        obj = SequenceOf[int | None](items=[None, None, 1, None, 2, None])
        result = impl.dump(SequenceOf[int | None], obj)
        assert result == b'{"items":[null,null,1,null,2,null]}'

    def test_all_nulls(self, impl: Serializer) -> None:
        obj = SequenceOf[int | None](items=[None, None, None, None])
        result = impl.dump(SequenceOf[int | None], obj)
        assert result == b'{"items":[null,null,null,null]}'

    def test_big_int_values(self, impl: Serializer) -> None:
        big_vals = [9223372036854775808, -9223372036854775809, 2**100, -(2**100)]
        obj = SequenceOf[int](items=big_vals)
        result = impl.dump(SequenceOf[int], obj)
        loaded = impl.load(SequenceOf[int], result)
        assert loaded.items == big_vals

    def test_unicode_strings(self, impl: Serializer) -> None:
        unicode_vals = ["Привет", "你好", "🎉🎊🎁", "مرحبا"]
        obj = SequenceOf[str](items=unicode_vals)
        result = impl.dump(SequenceOf[str], obj)
        loaded = impl.load(SequenceOf[str], result)
        assert loaded.items == unicode_vals

    def test_4_level_nesting(self, impl: Serializer) -> None:
        obj = SequenceOf[Sequence[Sequence[Sequence[int]]]](items=[[[[1, 2], [3, 4]], [[5, 6], [7, 8]]]])
        result = impl.dump(SequenceOf[Sequence[Sequence[Sequence[int]]]], obj)
        loaded = impl.load(SequenceOf[Sequence[Sequence[Sequence[int]]]], result)
        assert loaded == obj

    def test_mixed_types_in_any(self, impl: Serializer) -> None:
        obj = SequenceOf[Any](items=[1, "two", 3.14, True, None, {"a": 1}, [1, 2, 3]])
        result = impl.dump(SequenceOf[Any], obj)
        loaded = impl.load(SequenceOf[Any], result)
        assert loaded == obj

    def test_1000_elements(self, impl: Serializer) -> None:
        items = list(range(1000))
        obj = SequenceOf[int](items=items)
        result = impl.dump(SequenceOf[int], obj)
        loaded = impl.load(SequenceOf[int], result)
        assert loaded.items == items

    def test_special_chars_in_strings(self, impl: Serializer) -> None:
        special_vals = ['"quoted"', "back\\slash", "new\nline", "tab\there"]
        obj = SequenceOf[str](items=special_vals)
        result = impl.dump(SequenceOf[str], obj)
        loaded = impl.load(SequenceOf[str], result)
        assert loaded.items == special_vals

    def test_empty_strings(self, impl: Serializer) -> None:
        obj = SequenceOf[str](items=["", "", "a", ""])
        result = impl.dump(SequenceOf[str], obj)
        loaded = impl.load(SequenceOf[str], result)
        assert loaded.items == ["", "", "a", ""]
