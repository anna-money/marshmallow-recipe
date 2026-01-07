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
    def test_str(self, impl: Serializer) -> None:
        obj = SequenceOf[str](items=["a", "b", "c"])
        result = impl.dump(SequenceOf[str], obj)
        assert result == b'{"items":["a","b","c"]}'

    def test_int(self, impl: Serializer) -> None:
        obj = SequenceOf[int](items=[1, 2, 3])
        result = impl.dump(SequenceOf[int], obj)
        assert result == b'{"items":[1,2,3]}'

    def test_float(self, impl: Serializer) -> None:
        obj = SequenceOf[float](items=[1.5, 2.5, 3.5])
        result = impl.dump(SequenceOf[float], obj)
        assert result == b'{"items":[1.5,2.5,3.5]}'

    def test_bool(self, impl: Serializer) -> None:
        obj = SequenceOf[bool](items=[True, False, True])
        result = impl.dump(SequenceOf[bool], obj)
        assert result == b'{"items":[true,false,true]}'

    def test_decimal(self, impl: Serializer) -> None:
        obj = SequenceOf[decimal.Decimal](items=[decimal.Decimal("1.23"), decimal.Decimal("4.56")])
        result = impl.dump(SequenceOf[decimal.Decimal], obj)
        assert result == b'{"items":["1.23","4.56"]}'

    def test_uuid(self, impl: Serializer) -> None:
        u1 = uuid.UUID("12345678-1234-5678-1234-567812345678")
        u2 = uuid.UUID("87654321-4321-8765-4321-876543218765")
        obj = SequenceOf[uuid.UUID](items=[u1, u2])
        result = impl.dump(SequenceOf[uuid.UUID], obj)
        assert result == b'{"items":["12345678-1234-5678-1234-567812345678","87654321-4321-8765-4321-876543218765"]}'

    def test_datetime(self, impl: Serializer) -> None:
        dt = datetime.datetime(2024, 1, 15, 10, 30, 0, tzinfo=datetime.UTC)
        obj = SequenceOf[datetime.datetime](items=[dt])
        result = impl.dump(SequenceOf[datetime.datetime], obj)
        assert result == b'{"items":["2024-01-15T10:30:00+00:00"]}'

    def test_date(self, impl: Serializer) -> None:
        d = datetime.date(2024, 1, 15)
        obj = SequenceOf[datetime.date](items=[d])
        result = impl.dump(SequenceOf[datetime.date], obj)
        assert result == b'{"items":["2024-01-15"]}'

    def test_time(self, impl: Serializer) -> None:
        t = datetime.time(10, 30, 0)
        obj = SequenceOf[datetime.time](items=[t])
        result = impl.dump(SequenceOf[datetime.time], obj)
        assert result == b'{"items":["10:30:00"]}'

    def test_str_enum(self, impl: Serializer) -> None:
        obj = SequenceOf[Status](items=[Status.ACTIVE, Status.PENDING])
        result = impl.dump(SequenceOf[Status], obj)
        assert result == b'{"items":["active","pending"]}'

    def test_int_enum(self, impl: Serializer) -> None:
        obj = SequenceOf[Priority](items=[Priority.LOW, Priority.HIGH])
        result = impl.dump(SequenceOf[Priority], obj)
        assert result == b'{"items":[1,3]}'

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

    def test_optional_none(self, impl: Serializer) -> None:
        obj = OptionalSequenceOf[int](items=None)
        result = impl.dump(OptionalSequenceOf[int], obj)
        assert result == b"{}"

    def test_optional_value(self, impl: Serializer) -> None:
        obj = OptionalSequenceOf[int](items=[1, 2, 3])
        result = impl.dump(OptionalSequenceOf[int], obj)
        assert result == b'{"items":[1,2,3]}'

    def test_none_handling_ignore_default(self, impl: Serializer) -> None:
        obj = OptionalSequenceOf[int](items=None)
        result = impl.dump(OptionalSequenceOf[int], obj)
        assert result == b"{}"

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
    def test_str(self, impl: Serializer) -> None:
        data = b'{"items":["a","b","c"]}'
        result = impl.load(SequenceOf[str], data)
        assert result == SequenceOf[str](items=["a", "b", "c"])

    def test_int(self, impl: Serializer) -> None:
        data = b'{"items":[1,2,3]}'
        result = impl.load(SequenceOf[int], data)
        assert result == SequenceOf[int](items=[1, 2, 3])

    def test_float(self, impl: Serializer) -> None:
        data = b'{"items":[1.5,2.5,3.5]}'
        result = impl.load(SequenceOf[float], data)
        assert result == SequenceOf[float](items=[1.5, 2.5, 3.5])

    def test_bool(self, impl: Serializer) -> None:
        data = b'{"items":[true,false,true]}'
        result = impl.load(SequenceOf[bool], data)
        assert result == SequenceOf[bool](items=[True, False, True])

    def test_decimal(self, impl: Serializer) -> None:
        data = b'{"items":["1.23","4.56"]}'
        result = impl.load(SequenceOf[decimal.Decimal], data)
        assert result == SequenceOf[decimal.Decimal](items=[decimal.Decimal("1.23"), decimal.Decimal("4.56")])

    def test_uuid(self, impl: Serializer) -> None:
        u1 = uuid.UUID("12345678-1234-5678-1234-567812345678")
        u2 = uuid.UUID("87654321-4321-8765-4321-876543218765")
        data = b'{"items":["12345678-1234-5678-1234-567812345678","87654321-4321-8765-4321-876543218765"]}'
        result = impl.load(SequenceOf[uuid.UUID], data)
        assert result == SequenceOf[uuid.UUID](items=[u1, u2])

    def test_datetime(self, impl: Serializer) -> None:
        dt = datetime.datetime(2024, 1, 15, 10, 30, 0, tzinfo=datetime.UTC)
        data = b'{"items":["2024-01-15T10:30:00+00:00"]}'
        result = impl.load(SequenceOf[datetime.datetime], data)
        assert result == SequenceOf[datetime.datetime](items=[dt])

    def test_date(self, impl: Serializer) -> None:
        d = datetime.date(2024, 1, 15)
        data = b'{"items":["2024-01-15"]}'
        result = impl.load(SequenceOf[datetime.date], data)
        assert result == SequenceOf[datetime.date](items=[d])

    def test_time(self, impl: Serializer) -> None:
        t = datetime.time(10, 30, 0)
        data = b'{"items":["10:30:00"]}'
        result = impl.load(SequenceOf[datetime.time], data)
        assert result == SequenceOf[datetime.time](items=[t])

    def test_str_enum(self, impl: Serializer) -> None:
        data = b'{"items":["active","pending"]}'
        result = impl.load(SequenceOf[Status], data)
        assert result == SequenceOf[Status](items=[Status.ACTIVE, Status.PENDING])

    def test_int_enum(self, impl: Serializer) -> None:
        data = b'{"items":[1,3]}'
        result = impl.load(SequenceOf[Priority], data)
        assert result == SequenceOf[Priority](items=[Priority.LOW, Priority.HIGH])

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

    def test_item_two_validators_first_fails(self, impl: Serializer) -> None:
        data = b'{"items":[1,0,50]}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithSequenceTwoValidators, data)
        assert exc.value.messages == {"items": {1: ["Invalid value."]}}

    def test_item_two_validators_second_fails(self, impl: Serializer) -> None:
        data = b'{"items":[1,150,50]}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithSequenceTwoValidators, data)
        assert exc.value.messages == {"items": {1: ["Invalid value."]}}

    def test_item_wrong_type(self, impl: Serializer) -> None:
        data = b'{"items":[1,"not_int",3]}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(SequenceOf[int], data)
        assert exc.value.messages == {"items": {1: ["Not a valid integer."]}}

    def test_wrong_type_string(self, impl: Serializer) -> None:
        data = b'{"items":"not_a_sequence"}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(SequenceOf[int], data)
        assert exc.value.messages == {"items": ["Not a valid list."]}

    def test_wrong_type_object(self, impl: Serializer) -> None:
        data = b'{"items":{"key":1}}'
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
