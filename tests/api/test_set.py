import datetime
import decimal
import uuid

import marshmallow
import pytest

import marshmallow_recipe as mr

from .conftest import (
    CollectionHolder,
    OptionalSetOf,
    Priority,
    Serializer,
    SetOf,
    Status,
    WithSetInvalidError,
    WithSetItemTwoValidators,
    WithSetItemValidation,
    WithSetMissing,
    WithSetNoneError,
    WithSetRequiredError,
)


class TestSetDump:
    def test_str(self, impl: Serializer) -> None:
        obj = SetOf[str](items={"a"})
        result = impl.dump(SetOf[str], obj)
        assert result == b'{"items":["a"]}'

    def test_int(self, impl: Serializer) -> None:
        obj = SetOf[int](items={42})
        result = impl.dump(SetOf[int], obj)
        assert result == b'{"items":[42]}'

    def test_float(self, impl: Serializer) -> None:
        obj = SetOf[float](items={3.14})
        result = impl.dump(SetOf[float], obj)
        assert result == b'{"items":[3.14]}'

    def test_bool(self, impl: Serializer) -> None:
        obj = SetOf[bool](items={True})
        result = impl.dump(SetOf[bool], obj)
        assert result == b'{"items":[true]}'

    def test_decimal(self, impl: Serializer) -> None:
        obj = SetOf[decimal.Decimal](items={decimal.Decimal("1.23")})
        result = impl.dump(SetOf[decimal.Decimal], obj)
        assert result == b'{"items":["1.23"]}'

    def test_uuid(self, impl: Serializer) -> None:
        u = uuid.UUID("12345678-1234-5678-1234-567812345678")
        obj = SetOf[uuid.UUID](items={u})
        result = impl.dump(SetOf[uuid.UUID], obj)
        assert result == b'{"items":["12345678-1234-5678-1234-567812345678"]}'

    def test_datetime(self, impl: Serializer) -> None:
        dt = datetime.datetime(2024, 1, 15, 10, 30, 0, tzinfo=datetime.UTC)
        obj = SetOf[datetime.datetime](items={dt})
        result = impl.dump(SetOf[datetime.datetime], obj)
        assert result == b'{"items":["2024-01-15T10:30:00+00:00"]}'

    def test_date(self, impl: Serializer) -> None:
        d = datetime.date(2024, 1, 15)
        obj = SetOf[datetime.date](items={d})
        result = impl.dump(SetOf[datetime.date], obj)
        assert result == b'{"items":["2024-01-15"]}'

    def test_time(self, impl: Serializer) -> None:
        t = datetime.time(10, 30, 0)
        obj = SetOf[datetime.time](items={t})
        result = impl.dump(SetOf[datetime.time], obj)
        assert result == b'{"items":["10:30:00"]}'

    def test_str_enum(self, impl: Serializer) -> None:
        obj = SetOf[Status](items={Status.ACTIVE})
        result = impl.dump(SetOf[Status], obj)
        assert result == b'{"items":["active"]}'

    def test_int_enum(self, impl: Serializer) -> None:
        obj = SetOf[Priority](items={Priority.HIGH})
        result = impl.dump(SetOf[Priority], obj)
        assert result == b'{"items":[3]}'

    def test_empty(self, impl: Serializer) -> None:
        obj = SetOf[int](items=set())
        result = impl.dump(SetOf[int], obj)
        assert result == b'{"items":[]}'

    def test_optional_none(self, impl: Serializer) -> None:
        obj = OptionalSetOf[int](items=None)
        result = impl.dump(OptionalSetOf[int], obj)
        assert result == b"{}"

    def test_optional_value(self, impl: Serializer) -> None:
        obj = OptionalSetOf[int](items={42})
        result = impl.dump(OptionalSetOf[int], obj)
        assert result == b'{"items":[42]}'

    def test_none_handling_ignore_default(self, impl: Serializer) -> None:
        obj = OptionalSetOf[int](items=None)
        result = impl.dump(OptionalSetOf[int], obj)
        assert result == b"{}"

    def test_none_handling_ignore_explicit(self, impl: Serializer) -> None:
        obj = OptionalSetOf[int](items=None)
        result = impl.dump(OptionalSetOf[int], obj, none_value_handling=mr.NoneValueHandling.IGNORE)
        assert result == b"{}"

    def test_none_handling_include(self, impl: Serializer) -> None:
        obj = OptionalSetOf[int](items=None)
        result = impl.dump(OptionalSetOf[int], obj, none_value_handling=mr.NoneValueHandling.INCLUDE)
        assert result == b'{"items":null}'

    def test_none_handling_include_with_value(self, impl: Serializer) -> None:
        obj = OptionalSetOf[int](items={42})
        result = impl.dump(OptionalSetOf[int], obj, none_value_handling=mr.NoneValueHandling.INCLUDE)
        assert result == b'{"items":[42]}'

    def test_missing(self, impl: Serializer) -> None:
        obj = WithSetMissing()
        result = impl.dump(WithSetMissing, obj)
        assert result == b"{}"

    def test_missing_with_value(self, impl: Serializer) -> None:
        obj = WithSetMissing(items={1})
        result = impl.dump(WithSetMissing, obj)
        assert result == b'{"items":[1]}'

    def test_unsubscripted(self, impl: Serializer) -> None:
        obj = CollectionHolder[set](items={"se", 55})
        result = impl.dump(CollectionHolder[set], obj)
        assert result == b'{"items":["se",55]}' or result == b'{"items":[55,"se"]}'


class TestSetLoad:
    def test_str(self, impl: Serializer) -> None:
        data = b'{"items":["a"]}'
        result = impl.load(SetOf[str], data)
        assert result == SetOf[str](items={"a"})

    def test_int(self, impl: Serializer) -> None:
        data = b'{"items":[42]}'
        result = impl.load(SetOf[int], data)
        assert result == SetOf[int](items={42})

    def test_float(self, impl: Serializer) -> None:
        data = b'{"items":[3.14]}'
        result = impl.load(SetOf[float], data)
        assert result == SetOf[float](items={3.14})

    def test_bool(self, impl: Serializer) -> None:
        data = b'{"items":[true]}'
        result = impl.load(SetOf[bool], data)
        assert result == SetOf[bool](items={True})

    def test_decimal(self, impl: Serializer) -> None:
        data = b'{"items":["1.23"]}'
        result = impl.load(SetOf[decimal.Decimal], data)
        assert result == SetOf[decimal.Decimal](items={decimal.Decimal("1.23")})

    def test_uuid(self, impl: Serializer) -> None:
        u = uuid.UUID("12345678-1234-5678-1234-567812345678")
        data = b'{"items":["12345678-1234-5678-1234-567812345678"]}'
        result = impl.load(SetOf[uuid.UUID], data)
        assert result == SetOf[uuid.UUID](items={u})

    def test_datetime(self, impl: Serializer) -> None:
        dt = datetime.datetime(2024, 1, 15, 10, 30, 0, tzinfo=datetime.UTC)
        data = b'{"items":["2024-01-15T10:30:00+00:00"]}'
        result = impl.load(SetOf[datetime.datetime], data)
        assert result == SetOf[datetime.datetime](items={dt})

    def test_date(self, impl: Serializer) -> None:
        d = datetime.date(2024, 1, 15)
        data = b'{"items":["2024-01-15"]}'
        result = impl.load(SetOf[datetime.date], data)
        assert result == SetOf[datetime.date](items={d})

    def test_time(self, impl: Serializer) -> None:
        t = datetime.time(10, 30, 0)
        data = b'{"items":["10:30:00"]}'
        result = impl.load(SetOf[datetime.time], data)
        assert result == SetOf[datetime.time](items={t})

    def test_str_enum(self, impl: Serializer) -> None:
        data = b'{"items":["active"]}'
        result = impl.load(SetOf[Status], data)
        assert result == SetOf[Status](items={Status.ACTIVE})

    def test_int_enum(self, impl: Serializer) -> None:
        data = b'{"items":[3]}'
        result = impl.load(SetOf[Priority], data)
        assert result == SetOf[Priority](items={Priority.HIGH})

    def test_empty(self, impl: Serializer) -> None:
        data = b'{"items":[]}'
        result = impl.load(SetOf[int], data)
        assert result == SetOf[int](items=set())

    def test_multiple_elements(self, impl: Serializer) -> None:
        data = b'{"items":[1,2,3]}'
        result = impl.load(SetOf[int], data)
        assert result == SetOf[int](items={1, 2, 3})

    def test_optional_none(self, impl: Serializer) -> None:
        data = b"{}"
        result = impl.load(OptionalSetOf[int], data)
        assert result == OptionalSetOf[int](items=None)

    def test_optional_value(self, impl: Serializer) -> None:
        data = b'{"items":[42]}'
        result = impl.load(OptionalSetOf[int], data)
        assert result == OptionalSetOf[int](items={42})

    def test_item_validation_pass(self, impl: Serializer) -> None:
        data = b'{"tags":["a","b","c"]}'
        result = impl.load(WithSetItemValidation, data)
        assert result == WithSetItemValidation(tags={"a", "b", "c"})

    def test_item_validation_empty_fail(self, impl: Serializer) -> None:
        data = b'{"tags":["a","","c"]}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithSetItemValidation, data)
        assert exc.value.messages == {"tags": {1: ["Invalid value."]}}

    def test_item_two_validators_pass(self, impl: Serializer) -> None:
        data = b'{"tags":["a","bb","ccc"]}'
        result = impl.load(WithSetItemTwoValidators, data)
        assert result == WithSetItemTwoValidators(tags={"a", "bb", "ccc"})

    def test_item_two_validators_first_fails(self, impl: Serializer) -> None:
        data = b'{"tags":["a","","ccc"]}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithSetItemTwoValidators, data)
        assert exc.value.messages == {"tags": {1: ["Invalid value."]}}

    def test_item_two_validators_second_fails(self, impl: Serializer) -> None:
        long_string = "a" * 51
        data = b'{"tags":["a","' + long_string.encode() + b'"]}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithSetItemTwoValidators, data)
        assert exc.value.messages == {"tags": {1: ["Invalid value."]}}

    def test_item_wrong_type(self, impl: Serializer) -> None:
        data = b'{"items":[1,"not_int",3]}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(SetOf[int], data)
        assert exc.value.messages == {"items": {1: ["Not a valid integer."]}}

    def test_wrong_type_string(self, impl: Serializer) -> None:
        data = b'{"items":"not_a_set"}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(SetOf[int], data)
        assert exc.value.messages == {"items": ["Not a valid set."]}

    def test_wrong_type_object(self, impl: Serializer) -> None:
        data = b'{"items":{"key":1}}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(SetOf[int], data)
        assert exc.value.messages == {"items": ["Not a valid set."]}

    def test_missing_required(self, impl: Serializer) -> None:
        data = b"{}"
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(SetOf[int], data)
        assert exc.value.messages == {"items": ["Missing data for required field."]}

    def test_custom_required_error(self, impl: Serializer) -> None:
        data = b"{}"
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithSetRequiredError, data)
        assert exc.value.messages == {"items": ["Custom required message"]}

    def test_custom_none_error(self, impl: Serializer) -> None:
        data = b'{"items":null}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithSetNoneError, data)
        assert exc.value.messages == {"items": ["Custom none message"]}

    def test_custom_invalid_error(self, impl: Serializer) -> None:
        data = b'{"items":"not_a_set"}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithSetInvalidError, data)
        assert exc.value.messages == {"items": ["Custom invalid message"]}

    def test_missing(self, impl: Serializer) -> None:
        data = b"{}"
        result = impl.load(WithSetMissing, data)
        assert result == WithSetMissing()

    def test_missing_with_value(self, impl: Serializer) -> None:
        data = b'{"items":[1,2,3]}'
        result = impl.load(WithSetMissing, data)
        assert result == WithSetMissing(items={1, 2, 3})


class TestSetDumpInvalidType:
    """Test that invalid types in set fields raise ValidationError on dump."""

    def test_string(self, impl: Serializer) -> None:
        obj = SetOf[int](**{"items": "not a set"})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(SetOf[int], obj)

    def test_list(self, impl: Serializer) -> None:
        obj = SetOf[int](**{"items": [1, 2, 3]})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(SetOf[int], obj)

    def test_int(self, impl: Serializer) -> None:
        obj = SetOf[int](**{"items": 123})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(SetOf[int], obj)

    def test_dict(self, impl: Serializer) -> None:
        obj = SetOf[int](**{"items": {"a": 1}})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(SetOf[int], obj)
