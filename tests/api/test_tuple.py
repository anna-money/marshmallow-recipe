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
    def test_str(self, impl: Serializer) -> None:
        obj = TupleOf[str](items=("a", "b", "c"))
        result = impl.dump(TupleOf[str], obj)
        assert result == b'{"items":["a","b","c"]}'

    def test_int(self, impl: Serializer) -> None:
        obj = TupleOf[int](items=(1, 2, 3))
        result = impl.dump(TupleOf[int], obj)
        assert result == b'{"items":[1,2,3]}'

    def test_float(self, impl: Serializer) -> None:
        obj = TupleOf[float](items=(1.5, 2.5, 3.5))
        result = impl.dump(TupleOf[float], obj)
        assert result == b'{"items":[1.5,2.5,3.5]}'

    def test_bool(self, impl: Serializer) -> None:
        obj = TupleOf[bool](items=(True, False, True))
        result = impl.dump(TupleOf[bool], obj)
        assert result == b'{"items":[true,false,true]}'

    def test_decimal(self, impl: Serializer) -> None:
        obj = TupleOf[decimal.Decimal](items=(decimal.Decimal("1.23"), decimal.Decimal("4.56")))
        result = impl.dump(TupleOf[decimal.Decimal], obj)
        assert result == b'{"items":["1.23","4.56"]}'

    def test_uuid(self, impl: Serializer) -> None:
        u1 = uuid.UUID("12345678-1234-5678-1234-567812345678")
        u2 = uuid.UUID("87654321-4321-8765-4321-876543218765")
        obj = TupleOf[uuid.UUID](items=(u1, u2))
        result = impl.dump(TupleOf[uuid.UUID], obj)
        assert result == b'{"items":["12345678-1234-5678-1234-567812345678","87654321-4321-8765-4321-876543218765"]}'

    def test_datetime(self, impl: Serializer) -> None:
        dt = datetime.datetime(2024, 1, 15, 10, 30, 0, tzinfo=datetime.UTC)
        obj = TupleOf[datetime.datetime](items=(dt,))
        result = impl.dump(TupleOf[datetime.datetime], obj)
        assert result == b'{"items":["2024-01-15T10:30:00+00:00"]}'

    def test_date(self, impl: Serializer) -> None:
        d = datetime.date(2024, 1, 15)
        obj = TupleOf[datetime.date](items=(d,))
        result = impl.dump(TupleOf[datetime.date], obj)
        assert result == b'{"items":["2024-01-15"]}'

    def test_time(self, impl: Serializer) -> None:
        t = datetime.time(10, 30, 0)
        obj = TupleOf[datetime.time](items=(t,))
        result = impl.dump(TupleOf[datetime.time], obj)
        assert result == b'{"items":["10:30:00"]}'

    def test_str_enum(self, impl: Serializer) -> None:
        obj = TupleOf[Status](items=(Status.ACTIVE, Status.PENDING))
        result = impl.dump(TupleOf[Status], obj)
        assert result == b'{"items":["active","pending"]}'

    def test_int_enum(self, impl: Serializer) -> None:
        obj = TupleOf[Priority](items=(Priority.LOW, Priority.HIGH))
        result = impl.dump(TupleOf[Priority], obj)
        assert result == b'{"items":[1,3]}'

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

    def test_optional_none(self, impl: Serializer) -> None:
        obj = OptionalTupleOf[int](items=None)
        result = impl.dump(OptionalTupleOf[int], obj)
        assert result == b"{}"

    def test_optional_value(self, impl: Serializer) -> None:
        obj = OptionalTupleOf[int](items=(1, 2, 3))
        result = impl.dump(OptionalTupleOf[int], obj)
        assert result == b'{"items":[1,2,3]}'

    def test_none_handling_ignore_default(self, impl: Serializer) -> None:
        obj = OptionalTupleOf[int](items=None)
        result = impl.dump(OptionalTupleOf[int], obj)
        assert result == b"{}"

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
    def test_str(self, impl: Serializer) -> None:
        data = b'{"items":["a","b","c"]}'
        result = impl.load(TupleOf[str], data)
        assert result == TupleOf[str](items=("a", "b", "c"))

    def test_int(self, impl: Serializer) -> None:
        data = b'{"items":[1,2,3]}'
        result = impl.load(TupleOf[int], data)
        assert result == TupleOf[int](items=(1, 2, 3))

    def test_float(self, impl: Serializer) -> None:
        data = b'{"items":[1.5,2.5,3.5]}'
        result = impl.load(TupleOf[float], data)
        assert result == TupleOf[float](items=(1.5, 2.5, 3.5))

    def test_bool(self, impl: Serializer) -> None:
        data = b'{"items":[true,false,true]}'
        result = impl.load(TupleOf[bool], data)
        assert result == TupleOf[bool](items=(True, False, True))

    def test_decimal(self, impl: Serializer) -> None:
        data = b'{"items":["1.23","4.56"]}'
        result = impl.load(TupleOf[decimal.Decimal], data)
        assert result == TupleOf[decimal.Decimal](items=(decimal.Decimal("1.23"), decimal.Decimal("4.56")))

    def test_uuid(self, impl: Serializer) -> None:
        u1 = uuid.UUID("12345678-1234-5678-1234-567812345678")
        u2 = uuid.UUID("87654321-4321-8765-4321-876543218765")
        data = b'{"items":["12345678-1234-5678-1234-567812345678","87654321-4321-8765-4321-876543218765"]}'
        result = impl.load(TupleOf[uuid.UUID], data)
        assert result == TupleOf[uuid.UUID](items=(u1, u2))

    def test_datetime(self, impl: Serializer) -> None:
        dt = datetime.datetime(2024, 1, 15, 10, 30, 0, tzinfo=datetime.UTC)
        data = b'{"items":["2024-01-15T10:30:00+00:00"]}'
        result = impl.load(TupleOf[datetime.datetime], data)
        assert result == TupleOf[datetime.datetime](items=(dt,))

    def test_date(self, impl: Serializer) -> None:
        d = datetime.date(2024, 1, 15)
        data = b'{"items":["2024-01-15"]}'
        result = impl.load(TupleOf[datetime.date], data)
        assert result == TupleOf[datetime.date](items=(d,))

    def test_time(self, impl: Serializer) -> None:
        t = datetime.time(10, 30, 0)
        data = b'{"items":["10:30:00"]}'
        result = impl.load(TupleOf[datetime.time], data)
        assert result == TupleOf[datetime.time](items=(t,))

    def test_str_enum(self, impl: Serializer) -> None:
        data = b'{"items":["active","pending"]}'
        result = impl.load(TupleOf[Status], data)
        assert result == TupleOf[Status](items=(Status.ACTIVE, Status.PENDING))

    def test_int_enum(self, impl: Serializer) -> None:
        data = b'{"items":[1,3]}'
        result = impl.load(TupleOf[Priority], data)
        assert result == TupleOf[Priority](items=(Priority.LOW, Priority.HIGH))

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

    def test_item_two_validators_first_fails(self, impl: Serializer) -> None:
        data = b'{"values":[1,0,50]}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithTupleItemTwoValidators, data)
        assert exc.value.messages == {"values": {1: ["Invalid value."]}}

    def test_item_two_validators_second_fails(self, impl: Serializer) -> None:
        data = b'{"values":[1,150,50]}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithTupleItemTwoValidators, data)
        assert exc.value.messages == {"values": {1: ["Invalid value."]}}

    def test_item_wrong_type(self, impl: Serializer) -> None:
        data = b'{"items":[1,"not_int",3]}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(TupleOf[int], data)
        assert exc.value.messages == {"items": {1: ["Not a valid integer."]}}

    def test_wrong_type_string(self, impl: Serializer) -> None:
        data = b'{"items":"not_a_tuple"}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(TupleOf[int], data)
        assert exc.value.messages == {"items": ["Not a valid tuple."]}

    def test_wrong_type_object(self, impl: Serializer) -> None:
        data = b'{"items":{"key":1}}'
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


class TestTupleDumpInvalidType:
    """Test that invalid types in tuple fields raise ValidationError on dump."""

    def test_string(self, impl: Serializer) -> None:
        obj = TupleOf[int](**{"items": "not a tuple"})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(TupleOf[int], obj)

    def test_list(self, impl: Serializer) -> None:
        obj = TupleOf[int](**{"items": [1, 2, 3]})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(TupleOf[int], obj)

    def test_int(self, impl: Serializer) -> None:
        obj = TupleOf[int](**{"items": 123})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(TupleOf[int], obj)

    def test_dict(self, impl: Serializer) -> None:
        obj = TupleOf[int](**{"items": {"a": 1}})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(TupleOf[int], obj)
