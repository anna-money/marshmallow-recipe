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
    DictOf,
    OptionalDictOf,
    Priority,
    Serializer,
    Status,
    WithDictInvalidError,
    WithDictMissing,
    WithDictNoneError,
    WithDictRequiredError,
    WithDictTwoValidators,
    WithDictValidation,
)


class TestDictDump:
    def test_str_value(self, impl: Serializer) -> None:
        obj = DictOf[str, str](data={"a": "x", "b": "y"})
        result = impl.dump(DictOf[str, str], obj)
        assert result == b'{"data":{"a":"x","b":"y"}}'

    def test_int_value(self, impl: Serializer) -> None:
        obj = DictOf[str, int](data={"a": 1, "b": 2})
        result = impl.dump(DictOf[str, int], obj)
        assert result == b'{"data":{"a":1,"b":2}}'

    def test_float_value(self, impl: Serializer) -> None:
        obj = DictOf[str, float](data={"a": 1.5, "b": 2.5})
        result = impl.dump(DictOf[str, float], obj)
        assert result == b'{"data":{"a":1.5,"b":2.5}}'

    def test_bool_value(self, impl: Serializer) -> None:
        obj = DictOf[str, bool](data={"a": True, "b": False})
        result = impl.dump(DictOf[str, bool], obj)
        assert result == b'{"data":{"a":true,"b":false}}'

    def test_decimal_value(self, impl: Serializer) -> None:
        obj = DictOf[str, decimal.Decimal](data={"a": decimal.Decimal("1.23"), "b": decimal.Decimal("4.56")})
        result = impl.dump(DictOf[str, decimal.Decimal], obj)
        assert result == b'{"data":{"a":"1.23","b":"4.56"}}'

    def test_uuid_value(self, impl: Serializer) -> None:
        u = uuid.UUID("12345678-1234-5678-1234-567812345678")
        obj = DictOf[str, uuid.UUID](data={"a": u})
        result = impl.dump(DictOf[str, uuid.UUID], obj)
        assert result == b'{"data":{"a":"12345678-1234-5678-1234-567812345678"}}'

    def test_datetime_value(self, impl: Serializer) -> None:
        dt = datetime.datetime(2024, 1, 15, 10, 30, 0, tzinfo=datetime.UTC)
        obj = DictOf[str, datetime.datetime](data={"a": dt})
        result = impl.dump(DictOf[str, datetime.datetime], obj)
        assert result == b'{"data":{"a":"2024-01-15T10:30:00+00:00"}}'

    def test_date_value(self, impl: Serializer) -> None:
        d = datetime.date(2024, 1, 15)
        obj = DictOf[str, datetime.date](data={"a": d})
        result = impl.dump(DictOf[str, datetime.date], obj)
        assert result == b'{"data":{"a":"2024-01-15"}}'

    def test_time_value(self, impl: Serializer) -> None:
        t = datetime.time(10, 30, 0)
        obj = DictOf[str, datetime.time](data={"a": t})
        result = impl.dump(DictOf[str, datetime.time], obj)
        assert result == b'{"data":{"a":"10:30:00"}}'

    def test_str_enum_value(self, impl: Serializer) -> None:
        obj = DictOf[str, Status](data={"a": Status.ACTIVE, "b": Status.PENDING})
        result = impl.dump(DictOf[str, Status], obj)
        assert result == b'{"data":{"a":"active","b":"pending"}}'

    def test_int_enum_value(self, impl: Serializer) -> None:
        obj = DictOf[str, Priority](data={"a": Priority.LOW, "b": Priority.HIGH})
        result = impl.dump(DictOf[str, Priority], obj)
        assert result == b'{"data":{"a":1,"b":3}}'

    def test_dataclass_value(self, impl: Serializer) -> None:
        addr = Address(street="Main St", city="NYC", zip_code="10001")
        obj = DictOf[str, Address](data={"home": addr})
        result = impl.dump(DictOf[str, Address], obj)
        assert json.loads(result) == {"data": {"home": {"street": "Main St", "city": "NYC", "zip_code": "10001"}}}

    def test_list_value(self, impl: Serializer) -> None:
        obj = DictOf[str, list[int]](data={"a": [1, 2], "b": [3, 4]})
        result = impl.dump(DictOf[str, list[int]], obj)
        assert result == b'{"data":{"a":[1,2],"b":[3,4]}}'

    def test_nested_dict(self, impl: Serializer) -> None:
        obj = DictOf[str, dict[str, int]](data={"a": {"x": 1}, "b": {"y": 2}})
        result = impl.dump(DictOf[str, dict[str, int]], obj)
        assert result == b'{"data":{"a":{"x":1},"b":{"y":2}}}'

    def test_sequence_value(self, impl: Serializer) -> None:
        obj = DictOf[str, Sequence[int]](data={"a": [1, 2], "b": [3, 4]})
        result = impl.dump(DictOf[str, Sequence[int]], obj)
        assert result == b'{"data":{"a":[1,2],"b":[3,4]}}'

    def test_mapping_value(self, impl: Serializer) -> None:
        obj = DictOf[str, Mapping[str, int]](data={"a": {"x": 1}, "b": {"y": 2}})
        result = impl.dump(DictOf[str, Mapping[str, int]], obj)
        assert result == b'{"data":{"a":{"x":1},"b":{"y":2}}}'

    def test_optional_value(self, impl: Serializer) -> None:
        obj = DictOf[str, int | None](data={"a": 1, "b": None})
        result = impl.dump(DictOf[str, int | None], obj)
        assert result == b'{"data":{"a":1,"b":null}}'

    def test_any_value(self, impl: Serializer) -> None:
        obj = DictOf[str, Any](data={"a": 1, "b": "two", "c": None})
        result = impl.dump(DictOf[str, Any], obj)
        assert result == b'{"data":{"a":1,"b":"two","c":null}}'

    def test_empty(self, impl: Serializer) -> None:
        obj = DictOf[str, int](data={})
        result = impl.dump(DictOf[str, int], obj)
        assert result == b'{"data":{}}'

    def test_optional_none(self, impl: Serializer) -> None:
        obj = OptionalDictOf[str, int](data=None)
        result = impl.dump(OptionalDictOf[str, int], obj)
        assert result == b"{}"

    def test_optional_value_present(self, impl: Serializer) -> None:
        obj = OptionalDictOf[str, int](data={"a": 1})
        result = impl.dump(OptionalDictOf[str, int], obj)
        assert result == b'{"data":{"a":1}}'

    def test_none_handling_ignore_default(self, impl: Serializer) -> None:
        obj = OptionalDictOf[str, int](data=None)
        result = impl.dump(OptionalDictOf[str, int], obj)
        assert result == b"{}"

    def test_none_handling_ignore_explicit(self, impl: Serializer) -> None:
        obj = OptionalDictOf[str, int](data=None)
        result = impl.dump(OptionalDictOf[str, int], obj, none_value_handling=mr.NoneValueHandling.IGNORE)
        assert result == b"{}"

    def test_none_handling_include(self, impl: Serializer) -> None:
        obj = OptionalDictOf[str, int](data=None)
        result = impl.dump(OptionalDictOf[str, int], obj, none_value_handling=mr.NoneValueHandling.INCLUDE)
        assert result == b'{"data":null}'

    def test_none_handling_include_with_value(self, impl: Serializer) -> None:
        obj = OptionalDictOf[str, int](data={"a": 1})
        result = impl.dump(OptionalDictOf[str, int], obj, none_value_handling=mr.NoneValueHandling.INCLUDE)
        assert result == b'{"data":{"a":1}}'

    def test_missing(self, impl: Serializer) -> None:
        obj = WithDictMissing()
        result = impl.dump(WithDictMissing, obj)
        assert result == b"{}"

    def test_missing_with_value(self, impl: Serializer) -> None:
        obj = WithDictMissing(data={"a": 1, "b": 2})
        result = impl.dump(WithDictMissing, obj)
        assert result == b'{"data":{"a":1,"b":2}}'

    def test_unsubscripted(self, impl: Serializer) -> None:
        obj = CollectionHolder[dict](items={"a": 1, "b": "va"})
        result = impl.dump(CollectionHolder[dict], obj)
        assert result == b'{"items":{"a":1,"b":"va"}}'


class TestDictLoad:
    def test_str_value(self, impl: Serializer) -> None:
        data = b'{"data":{"a":"x","b":"y"}}'
        result = impl.load(DictOf[str, str], data)
        assert result == DictOf[str, str](data={"a": "x", "b": "y"})

    def test_int_value(self, impl: Serializer) -> None:
        data = b'{"data":{"a":1,"b":2}}'
        result = impl.load(DictOf[str, int], data)
        assert result == DictOf[str, int](data={"a": 1, "b": 2})

    def test_float_value(self, impl: Serializer) -> None:
        data = b'{"data":{"a":1.5,"b":2.5}}'
        result = impl.load(DictOf[str, float], data)
        assert result == DictOf[str, float](data={"a": 1.5, "b": 2.5})

    def test_bool_value(self, impl: Serializer) -> None:
        data = b'{"data":{"a":true,"b":false}}'
        result = impl.load(DictOf[str, bool], data)
        assert result == DictOf[str, bool](data={"a": True, "b": False})

    def test_decimal_value(self, impl: Serializer) -> None:
        data = b'{"data":{"a":"1.23","b":"4.56"}}'
        result = impl.load(DictOf[str, decimal.Decimal], data)
        assert result == DictOf[str, decimal.Decimal](data={"a": decimal.Decimal("1.23"), "b": decimal.Decimal("4.56")})

    def test_uuid_value(self, impl: Serializer) -> None:
        u = uuid.UUID("12345678-1234-5678-1234-567812345678")
        data = b'{"data":{"a":"12345678-1234-5678-1234-567812345678"}}'
        result = impl.load(DictOf[str, uuid.UUID], data)
        assert result == DictOf[str, uuid.UUID](data={"a": u})

    def test_datetime_value(self, impl: Serializer) -> None:
        dt = datetime.datetime(2024, 1, 15, 10, 30, 0, tzinfo=datetime.UTC)
        data = b'{"data":{"a":"2024-01-15T10:30:00+00:00"}}'
        result = impl.load(DictOf[str, datetime.datetime], data)
        assert result == DictOf[str, datetime.datetime](data={"a": dt})

    def test_date_value(self, impl: Serializer) -> None:
        d = datetime.date(2024, 1, 15)
        data = b'{"data":{"a":"2024-01-15"}}'
        result = impl.load(DictOf[str, datetime.date], data)
        assert result == DictOf[str, datetime.date](data={"a": d})

    def test_time_value(self, impl: Serializer) -> None:
        t = datetime.time(10, 30, 0)
        data = b'{"data":{"a":"10:30:00"}}'
        result = impl.load(DictOf[str, datetime.time], data)
        assert result == DictOf[str, datetime.time](data={"a": t})

    def test_str_enum_value(self, impl: Serializer) -> None:
        data = b'{"data":{"a":"active","b":"pending"}}'
        result = impl.load(DictOf[str, Status], data)
        assert result == DictOf[str, Status](data={"a": Status.ACTIVE, "b": Status.PENDING})

    def test_int_enum_value(self, impl: Serializer) -> None:
        data = b'{"data":{"a":1,"b":3}}'
        result = impl.load(DictOf[str, Priority], data)
        assert result == DictOf[str, Priority](data={"a": Priority.LOW, "b": Priority.HIGH})

    def test_dataclass_value(self, impl: Serializer) -> None:
        addr = Address(street="Main St", city="NYC", zip_code="10001")
        data = b'{"data":{"home":{"street":"Main St","city":"NYC","zip_code":"10001"}}}'
        result = impl.load(DictOf[str, Address], data)
        assert result == DictOf[str, Address](data={"home": addr})

    def test_list_value(self, impl: Serializer) -> None:
        data = b'{"data":{"a":[1,2],"b":[3,4]}}'
        result = impl.load(DictOf[str, list[int]], data)
        assert result == DictOf[str, list[int]](data={"a": [1, 2], "b": [3, 4]})

    def test_nested_dict(self, impl: Serializer) -> None:
        data = b'{"data":{"a":{"x":1},"b":{"y":2}}}'
        result = impl.load(DictOf[str, dict[str, int]], data)
        assert result == DictOf[str, dict[str, int]](data={"a": {"x": 1}, "b": {"y": 2}})

    def test_sequence_value(self, impl: Serializer) -> None:
        data = b'{"data":{"a":[1,2],"b":[3,4]}}'
        result = impl.load(DictOf[str, Sequence[int]], data)
        assert result == DictOf[str, Sequence[int]](data={"a": [1, 2], "b": [3, 4]})

    def test_mapping_value(self, impl: Serializer) -> None:
        data = b'{"data":{"a":{"x":1},"b":{"y":2}}}'
        result = impl.load(DictOf[str, Mapping[str, int]], data)
        assert result == DictOf[str, Mapping[str, int]](data={"a": {"x": 1}, "b": {"y": 2}})

    def test_optional_value(self, impl: Serializer) -> None:
        data = b'{"data":{"a":1,"b":null}}'
        result = impl.load(DictOf[str, int | None], data)
        assert result == DictOf[str, int | None](data={"a": 1, "b": None})

    def test_any_value(self, impl: Serializer) -> None:
        data = b'{"data":{"a":1,"b":"two","c":null}}'
        result = impl.load(DictOf[str, Any], data)
        assert result == DictOf[str, Any](data={"a": 1, "b": "two", "c": None})

    def test_empty(self, impl: Serializer) -> None:
        data = b'{"data":{}}'
        result = impl.load(DictOf[str, int], data)
        assert result == DictOf[str, int](data={})

    def test_optional_none(self, impl: Serializer) -> None:
        data = b"{}"
        result = impl.load(OptionalDictOf[str, int], data)
        assert result == OptionalDictOf[str, int](data=None)

    def test_optional_value_present(self, impl: Serializer) -> None:
        data = b'{"data":{"a":1}}'
        result = impl.load(OptionalDictOf[str, int], data)
        assert result == OptionalDictOf[str, int](data={"a": 1})

    def test_validation_pass(self, impl: Serializer) -> None:
        data = b'{"data":{"a":1}}'
        result = impl.load(WithDictValidation, data)
        assert result == WithDictValidation(data={"a": 1})

    def test_validation_fail(self, impl: Serializer) -> None:
        data = b'{"data":{}}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithDictValidation, data)
        assert exc.value.messages == {"data": ["Invalid value."]}

    def test_two_validators_pass(self, impl: Serializer) -> None:
        data = b'{"data":{"a":1,"b":2,"c":3}}'
        result = impl.load(WithDictTwoValidators, data)
        assert result == WithDictTwoValidators(data={"a": 1, "b": 2, "c": 3})

    def test_two_validators_first_fails(self, impl: Serializer) -> None:
        data = b'{"data":{}}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithDictTwoValidators, data)
        assert exc.value.messages == {"data": ["Invalid value."]}

    def test_two_validators_second_fails(self, impl: Serializer) -> None:
        items = ", ".join([f'"{chr(97+i)}": {i}' for i in range(11)])
        data = b'{"data":{' + items.encode() + b"}}"
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithDictTwoValidators, data)
        assert exc.value.messages == {"data": ["Invalid value."]}

    def test_value_wrong_type(self, impl: Serializer) -> None:
        data = b'{"data":{"a":"not_int"}}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(DictOf[str, int], data)
        assert exc.value.messages == {"data": {"a": {"value": ["Not a valid integer."]}}}

    def test_wrong_type_string(self, impl: Serializer) -> None:
        data = b'{"data":"not_a_dict"}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(DictOf[str, int], data)
        assert exc.value.messages == {"data": ["Not a valid dict."]}

    def test_wrong_type_list(self, impl: Serializer) -> None:
        data = b'{"data":[1,2,3]}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(DictOf[str, int], data)
        assert exc.value.messages == {"data": ["Not a valid dict."]}

    def test_missing_required(self, impl: Serializer) -> None:
        data = b"{}"
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(DictOf[str, int], data)
        assert exc.value.messages == {"data": ["Missing data for required field."]}

    def test_custom_required_error(self, impl: Serializer) -> None:
        data = b"{}"
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithDictRequiredError, data)
        assert exc.value.messages == {"data": ["Custom required message"]}

    def test_custom_none_error(self, impl: Serializer) -> None:
        data = b'{"data":null}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithDictNoneError, data)
        assert exc.value.messages == {"data": ["Custom none message"]}

    def test_custom_invalid_error(self, impl: Serializer) -> None:
        data = b'{"data":"not_a_dict"}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithDictInvalidError, data)
        assert exc.value.messages == {"data": ["Custom invalid message"]}

    def test_missing(self, impl: Serializer) -> None:
        data = b"{}"
        result = impl.load(WithDictMissing, data)
        assert result == WithDictMissing()

    def test_missing_with_value(self, impl: Serializer) -> None:
        data = b'{"data":{"a":1,"b":2}}'
        result = impl.load(WithDictMissing, data)
        assert result == WithDictMissing(data={"a": 1, "b": 2})


class TestDictDumpInvalidType:
    """Test that invalid types in dict fields raise ValidationError on dump."""

    def test_string(self, impl: Serializer) -> None:
        obj = DictOf[str, int](**{"data": "not a dict"})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(DictOf[str, int], obj)

    def test_list(self, impl: Serializer) -> None:
        obj = DictOf[str, int](**{"data": [1, 2, 3]})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(DictOf[str, int], obj)

    def test_int(self, impl: Serializer) -> None:
        obj = DictOf[str, int](**{"data": 123})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(DictOf[str, int], obj)
