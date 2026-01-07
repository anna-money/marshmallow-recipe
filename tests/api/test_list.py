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
    def test_str(self, impl: Serializer) -> None:
        obj = ListOf[str](items=["a", "b", "c"])
        result = impl.dump(ListOf[str], obj)
        assert result == b'{"items":["a","b","c"]}'

    def test_int(self, impl: Serializer) -> None:
        obj = ListOf[int](items=[1, 2, 3])
        result = impl.dump(ListOf[int], obj)
        assert result == b'{"items":[1,2,3]}'

    def test_float(self, impl: Serializer) -> None:
        obj = ListOf[float](items=[1.5, 2.5, 3.5])
        result = impl.dump(ListOf[float], obj)
        assert result == b'{"items":[1.5,2.5,3.5]}'

    def test_bool(self, impl: Serializer) -> None:
        obj = ListOf[bool](items=[True, False, True])
        result = impl.dump(ListOf[bool], obj)
        assert result == b'{"items":[true,false,true]}'

    def test_decimal(self, impl: Serializer) -> None:
        obj = ListOf[decimal.Decimal](items=[decimal.Decimal("1.23"), decimal.Decimal("4.56")])
        result = impl.dump(ListOf[decimal.Decimal], obj)
        assert result == b'{"items":["1.23","4.56"]}'

    def test_uuid(self, impl: Serializer) -> None:
        u1 = uuid.UUID("12345678-1234-5678-1234-567812345678")
        u2 = uuid.UUID("87654321-4321-8765-4321-876543218765")
        obj = ListOf[uuid.UUID](items=[u1, u2])
        result = impl.dump(ListOf[uuid.UUID], obj)
        assert result == b'{"items":["12345678-1234-5678-1234-567812345678","87654321-4321-8765-4321-876543218765"]}'

    def test_datetime(self, impl: Serializer) -> None:
        dt = datetime.datetime(2024, 1, 15, 10, 30, 0, tzinfo=datetime.UTC)
        obj = ListOf[datetime.datetime](items=[dt])
        result = impl.dump(ListOf[datetime.datetime], obj)
        assert result == b'{"items":["2024-01-15T10:30:00+00:00"]}'

    def test_date(self, impl: Serializer) -> None:
        d = datetime.date(2024, 1, 15)
        obj = ListOf[datetime.date](items=[d])
        result = impl.dump(ListOf[datetime.date], obj)
        assert result == b'{"items":["2024-01-15"]}'

    def test_time(self, impl: Serializer) -> None:
        t = datetime.time(10, 30, 0)
        obj = ListOf[datetime.time](items=[t])
        result = impl.dump(ListOf[datetime.time], obj)
        assert result == b'{"items":["10:30:00"]}'

    def test_str_enum(self, impl: Serializer) -> None:
        obj = ListOf[Status](items=[Status.ACTIVE, Status.PENDING])
        result = impl.dump(ListOf[Status], obj)
        assert result == b'{"items":["active","pending"]}'

    def test_int_enum(self, impl: Serializer) -> None:
        obj = ListOf[Priority](items=[Priority.LOW, Priority.HIGH])
        result = impl.dump(ListOf[Priority], obj)
        assert result == b'{"items":[1,3]}'

    def test_dataclass(self, impl: Serializer) -> None:
        addr = Address(street="Main St", city="NYC", zip_code="10001")
        obj = ListOf[Address](items=[addr])
        result = impl.dump(ListOf[Address], obj)
        assert json.loads(result) == {"items": [{"street": "Main St", "city": "NYC", "zip_code": "10001"}]}

    def test_nested_list(self, impl: Serializer) -> None:
        obj = ListOf[list[int]](items=[[1, 2], [3, 4]])
        result = impl.dump(ListOf[list[int]], obj)
        assert result == b'{"items":[[1,2],[3,4]]}'

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

    def test_optional_none(self, impl: Serializer) -> None:
        obj = OptionalListOf[int](items=None)
        result = impl.dump(OptionalListOf[int], obj)
        assert result == b"{}"

    def test_optional_value(self, impl: Serializer) -> None:
        obj = OptionalListOf[int](items=[1, 2, 3])
        result = impl.dump(OptionalListOf[int], obj)
        assert result == b'{"items":[1,2,3]}'

    def test_none_handling_ignore_default(self, impl: Serializer) -> None:
        obj = OptionalListOf[int](items=None)
        result = impl.dump(OptionalListOf[int], obj)
        assert result == b"{}"

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
    def test_str(self, impl: Serializer) -> None:
        data = b'{"items":["a","b","c"]}'
        result = impl.load(ListOf[str], data)
        assert result == ListOf[str](items=["a", "b", "c"])

    def test_int(self, impl: Serializer) -> None:
        data = b'{"items":[1,2,3]}'
        result = impl.load(ListOf[int], data)
        assert result == ListOf[int](items=[1, 2, 3])

    def test_float(self, impl: Serializer) -> None:
        data = b'{"items":[1.5,2.5,3.5]}'
        result = impl.load(ListOf[float], data)
        assert result == ListOf[float](items=[1.5, 2.5, 3.5])

    def test_bool(self, impl: Serializer) -> None:
        data = b'{"items":[true,false,true]}'
        result = impl.load(ListOf[bool], data)
        assert result == ListOf[bool](items=[True, False, True])

    def test_decimal(self, impl: Serializer) -> None:
        data = b'{"items":["1.23","4.56"]}'
        result = impl.load(ListOf[decimal.Decimal], data)
        assert result == ListOf[decimal.Decimal](items=[decimal.Decimal("1.23"), decimal.Decimal("4.56")])

    def test_uuid(self, impl: Serializer) -> None:
        u1 = uuid.UUID("12345678-1234-5678-1234-567812345678")
        u2 = uuid.UUID("87654321-4321-8765-4321-876543218765")
        data = b'{"items":["12345678-1234-5678-1234-567812345678","87654321-4321-8765-4321-876543218765"]}'
        result = impl.load(ListOf[uuid.UUID], data)
        assert result == ListOf[uuid.UUID](items=[u1, u2])

    def test_datetime(self, impl: Serializer) -> None:
        dt = datetime.datetime(2024, 1, 15, 10, 30, 0, tzinfo=datetime.UTC)
        data = b'{"items":["2024-01-15T10:30:00+00:00"]}'
        result = impl.load(ListOf[datetime.datetime], data)
        assert result == ListOf[datetime.datetime](items=[dt])

    def test_date(self, impl: Serializer) -> None:
        d = datetime.date(2024, 1, 15)
        data = b'{"items":["2024-01-15"]}'
        result = impl.load(ListOf[datetime.date], data)
        assert result == ListOf[datetime.date](items=[d])

    def test_time(self, impl: Serializer) -> None:
        t = datetime.time(10, 30, 0)
        data = b'{"items":["10:30:00"]}'
        result = impl.load(ListOf[datetime.time], data)
        assert result == ListOf[datetime.time](items=[t])

    def test_str_enum(self, impl: Serializer) -> None:
        data = b'{"items":["active","pending"]}'
        result = impl.load(ListOf[Status], data)
        assert result == ListOf[Status](items=[Status.ACTIVE, Status.PENDING])

    def test_int_enum(self, impl: Serializer) -> None:
        data = b'{"items":[1,3]}'
        result = impl.load(ListOf[Priority], data)
        assert result == ListOf[Priority](items=[Priority.LOW, Priority.HIGH])

    def test_dataclass(self, impl: Serializer) -> None:
        addr = Address(street="Main St", city="NYC", zip_code="10001")
        data = b'{"items":[{"street":"Main St","city":"NYC","zip_code":"10001"}]}'
        result = impl.load(ListOf[Address], data)
        assert result == ListOf[Address](items=[addr])

    def test_nested_list(self, impl: Serializer) -> None:
        data = b'{"items":[[1,2],[3,4]]}'
        result = impl.load(ListOf[list[int]], data)
        assert result == ListOf[list[int]](items=[[1, 2], [3, 4]])

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

    def test_item_validation_zero_fail(self, impl: Serializer) -> None:
        data = b'{"items":[1,0,3]}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithListItemValidation, data)
        assert exc.value.messages == {"items": {1: ["Invalid value."]}}

    def test_item_validation_negative_fail(self, impl: Serializer) -> None:
        data = b'{"items":[1,-5,3]}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithListItemValidation, data)
        assert exc.value.messages == {"items": {1: ["Invalid value."]}}

    def test_item_two_validators_pass(self, impl: Serializer) -> None:
        data = b'{"items":[1,50,99]}'
        result = impl.load(WithListItemTwoValidators, data)
        assert result == WithListItemTwoValidators(items=[1, 50, 99])

    def test_item_two_validators_first_fails(self, impl: Serializer) -> None:
        data = b'{"items":[1,0,50]}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithListItemTwoValidators, data)
        assert exc.value.messages == {"items": {1: ["Invalid value."]}}

    def test_item_two_validators_second_fails(self, impl: Serializer) -> None:
        data = b'{"items":[1,150,50]}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithListItemTwoValidators, data)
        assert exc.value.messages == {"items": {1: ["Invalid value."]}}

    def test_item_wrong_type(self, impl: Serializer) -> None:
        data = b'{"items":[1,"not_int",3]}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ListOf[int], data)
        assert exc.value.messages == {"items": {1: ["Not a valid integer."]}}

    def test_wrong_type_string(self, impl: Serializer) -> None:
        data = b'{"items":"not_a_list"}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ListOf[int], data)
        assert exc.value.messages == {"items": ["Not a valid list."]}

    def test_wrong_type_object(self, impl: Serializer) -> None:
        data = b'{"items":{"key":1}}'
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


class TestListDumpInvalidType:
    """Test that invalid types in list fields raise ValidationError on dump."""

    def test_string(self, impl: Serializer) -> None:
        obj = ListOf[int](**{"items": "not a list"})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(ListOf[int], obj)

    def test_dict(self, impl: Serializer) -> None:
        obj = ListOf[int](**{"items": {"a": 1}})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(ListOf[int], obj)

    def test_int(self, impl: Serializer) -> None:
        obj = ListOf[int](**{"items": 123})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(ListOf[int], obj)

    def test_tuple(self, impl: Serializer) -> None:
        obj = ListOf[int](**{"items": (1, 2, 3)})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(ListOf[int], obj)
