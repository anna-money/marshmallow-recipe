import datetime
import decimal
import uuid

import marshmallow
import pytest

import marshmallow_recipe as mr

from .conftest import (
    CollectionHolder,
    FrozenSetOf,
    OptionalFrozenSetOf,
    Priority,
    Serializer,
    Status,
    WithFrozenSetInvalidError,
    WithFrozenSetItemTwoValidators,
    WithFrozenSetItemValidation,
    WithFrozenSetMissing,
    WithFrozenSetNoneError,
    WithFrozenSetRequiredError,
)


class TestFrozenSetDump:
    def test_str(self, impl: Serializer) -> None:
        obj = FrozenSetOf[str](items=frozenset({"a"}))
        result = impl.dump(FrozenSetOf[str], obj)
        assert result == b'{"items":["a"]}'

    def test_int(self, impl: Serializer) -> None:
        obj = FrozenSetOf[int](items=frozenset({42}))
        result = impl.dump(FrozenSetOf[int], obj)
        assert result == b'{"items":[42]}'

    def test_float(self, impl: Serializer) -> None:
        obj = FrozenSetOf[float](items=frozenset({3.14}))
        result = impl.dump(FrozenSetOf[float], obj)
        assert result == b'{"items":[3.14]}'

    def test_bool(self, impl: Serializer) -> None:
        obj = FrozenSetOf[bool](items=frozenset({True}))
        result = impl.dump(FrozenSetOf[bool], obj)
        assert result == b'{"items":[true]}'

    def test_decimal(self, impl: Serializer) -> None:
        obj = FrozenSetOf[decimal.Decimal](items=frozenset({decimal.Decimal("1.23")}))
        result = impl.dump(FrozenSetOf[decimal.Decimal], obj)
        assert result == b'{"items":["1.23"]}'

    def test_uuid(self, impl: Serializer) -> None:
        u = uuid.UUID("12345678-1234-5678-1234-567812345678")
        obj = FrozenSetOf[uuid.UUID](items=frozenset({u}))
        result = impl.dump(FrozenSetOf[uuid.UUID], obj)
        assert result == b'{"items":["12345678-1234-5678-1234-567812345678"]}'

    def test_datetime(self, impl: Serializer) -> None:
        dt = datetime.datetime(2024, 1, 15, 10, 30, 0, tzinfo=datetime.UTC)
        obj = FrozenSetOf[datetime.datetime](items=frozenset({dt}))
        result = impl.dump(FrozenSetOf[datetime.datetime], obj)
        assert result == b'{"items":["2024-01-15T10:30:00+00:00"]}'

    def test_date(self, impl: Serializer) -> None:
        d = datetime.date(2024, 1, 15)
        obj = FrozenSetOf[datetime.date](items=frozenset({d}))
        result = impl.dump(FrozenSetOf[datetime.date], obj)
        assert result == b'{"items":["2024-01-15"]}'

    def test_time(self, impl: Serializer) -> None:
        t = datetime.time(10, 30, 0)
        obj = FrozenSetOf[datetime.time](items=frozenset({t}))
        result = impl.dump(FrozenSetOf[datetime.time], obj)
        assert result == b'{"items":["10:30:00"]}'

    def test_str_enum(self, impl: Serializer) -> None:
        obj = FrozenSetOf[Status](items=frozenset({Status.ACTIVE}))
        result = impl.dump(FrozenSetOf[Status], obj)
        assert result == b'{"items":["active"]}'

    def test_int_enum(self, impl: Serializer) -> None:
        obj = FrozenSetOf[Priority](items=frozenset({Priority.HIGH}))
        result = impl.dump(FrozenSetOf[Priority], obj)
        assert result == b'{"items":[3]}'

    def test_empty(self, impl: Serializer) -> None:
        obj = FrozenSetOf[int](items=frozenset())
        result = impl.dump(FrozenSetOf[int], obj)
        assert result == b'{"items":[]}'

    def test_optional_none(self, impl: Serializer) -> None:
        obj = OptionalFrozenSetOf[int](items=None)
        result = impl.dump(OptionalFrozenSetOf[int], obj)
        assert result == b"{}"

    def test_optional_value(self, impl: Serializer) -> None:
        obj = OptionalFrozenSetOf[int](items=frozenset({42}))
        result = impl.dump(OptionalFrozenSetOf[int], obj)
        assert result == b'{"items":[42]}'

    def test_none_handling_ignore_default(self, impl: Serializer) -> None:
        obj = OptionalFrozenSetOf[int](items=None)
        result = impl.dump(OptionalFrozenSetOf[int], obj)
        assert result == b"{}"

    def test_none_handling_ignore_explicit(self, impl: Serializer) -> None:
        obj = OptionalFrozenSetOf[int](items=None)
        result = impl.dump(OptionalFrozenSetOf[int], obj, none_value_handling=mr.NoneValueHandling.IGNORE)
        assert result == b"{}"

    def test_none_handling_include(self, impl: Serializer) -> None:
        obj = OptionalFrozenSetOf[int](items=None)
        result = impl.dump(OptionalFrozenSetOf[int], obj, none_value_handling=mr.NoneValueHandling.INCLUDE)
        assert result == b'{"items":null}'

    def test_none_handling_include_with_value(self, impl: Serializer) -> None:
        obj = OptionalFrozenSetOf[int](items=frozenset({42}))
        result = impl.dump(OptionalFrozenSetOf[int], obj, none_value_handling=mr.NoneValueHandling.INCLUDE)
        assert result == b'{"items":[42]}'

    def test_missing(self, impl: Serializer) -> None:
        obj = WithFrozenSetMissing()
        result = impl.dump(WithFrozenSetMissing, obj)
        assert result == b"{}"

    def test_missing_with_value(self, impl: Serializer) -> None:
        obj = WithFrozenSetMissing(items=frozenset({1}))
        result = impl.dump(WithFrozenSetMissing, obj)
        assert result == b'{"items":[1]}'

    def test_unsubscripted(self, impl: Serializer) -> None:
        obj = CollectionHolder[frozenset](items=frozenset(["fs", 77]))
        result = impl.dump(CollectionHolder[frozenset], obj)
        assert result == b'{"items":["fs",77]}' or result == b'{"items":[77,"fs"]}'


class TestFrozenSetLoad:
    def test_str(self, impl: Serializer) -> None:
        data = b'{"items":["a"]}'
        result = impl.load(FrozenSetOf[str], data)
        assert result == FrozenSetOf[str](items=frozenset({"a"}))

    def test_int(self, impl: Serializer) -> None:
        data = b'{"items":[42]}'
        result = impl.load(FrozenSetOf[int], data)
        assert result == FrozenSetOf[int](items=frozenset({42}))

    def test_float(self, impl: Serializer) -> None:
        data = b'{"items":[3.14]}'
        result = impl.load(FrozenSetOf[float], data)
        assert result == FrozenSetOf[float](items=frozenset({3.14}))

    def test_bool(self, impl: Serializer) -> None:
        data = b'{"items":[true]}'
        result = impl.load(FrozenSetOf[bool], data)
        assert result == FrozenSetOf[bool](items=frozenset({True}))

    def test_decimal(self, impl: Serializer) -> None:
        data = b'{"items":["1.23"]}'
        result = impl.load(FrozenSetOf[decimal.Decimal], data)
        assert result == FrozenSetOf[decimal.Decimal](items=frozenset({decimal.Decimal("1.23")}))

    def test_uuid(self, impl: Serializer) -> None:
        u = uuid.UUID("12345678-1234-5678-1234-567812345678")
        data = b'{"items":["12345678-1234-5678-1234-567812345678"]}'
        result = impl.load(FrozenSetOf[uuid.UUID], data)
        assert result == FrozenSetOf[uuid.UUID](items=frozenset({u}))

    def test_datetime(self, impl: Serializer) -> None:
        dt = datetime.datetime(2024, 1, 15, 10, 30, 0, tzinfo=datetime.UTC)
        data = b'{"items":["2024-01-15T10:30:00+00:00"]}'
        result = impl.load(FrozenSetOf[datetime.datetime], data)
        assert result == FrozenSetOf[datetime.datetime](items=frozenset({dt}))

    def test_date(self, impl: Serializer) -> None:
        d = datetime.date(2024, 1, 15)
        data = b'{"items":["2024-01-15"]}'
        result = impl.load(FrozenSetOf[datetime.date], data)
        assert result == FrozenSetOf[datetime.date](items=frozenset({d}))

    def test_time(self, impl: Serializer) -> None:
        t = datetime.time(10, 30, 0)
        data = b'{"items":["10:30:00"]}'
        result = impl.load(FrozenSetOf[datetime.time], data)
        assert result == FrozenSetOf[datetime.time](items=frozenset({t}))

    def test_str_enum(self, impl: Serializer) -> None:
        data = b'{"items":["active"]}'
        result = impl.load(FrozenSetOf[Status], data)
        assert result == FrozenSetOf[Status](items=frozenset({Status.ACTIVE}))

    def test_int_enum(self, impl: Serializer) -> None:
        data = b'{"items":[3]}'
        result = impl.load(FrozenSetOf[Priority], data)
        assert result == FrozenSetOf[Priority](items=frozenset({Priority.HIGH}))

    def test_empty(self, impl: Serializer) -> None:
        data = b'{"items":[]}'
        result = impl.load(FrozenSetOf[int], data)
        assert result == FrozenSetOf[int](items=frozenset())

    def test_multiple_elements(self, impl: Serializer) -> None:
        data = b'{"items":[1,2,3]}'
        result = impl.load(FrozenSetOf[int], data)
        assert result == FrozenSetOf[int](items=frozenset({1, 2, 3}))

    def test_optional_none(self, impl: Serializer) -> None:
        data = b"{}"
        result = impl.load(OptionalFrozenSetOf[int], data)
        assert result == OptionalFrozenSetOf[int](items=None)

    def test_optional_value(self, impl: Serializer) -> None:
        data = b'{"items":[42]}'
        result = impl.load(OptionalFrozenSetOf[int], data)
        assert result == OptionalFrozenSetOf[int](items=frozenset({42}))

    def test_item_validation_pass(self, impl: Serializer) -> None:
        data = b'{"codes":["ABC","XYZ","DEF"]}'
        result = impl.load(WithFrozenSetItemValidation, data)
        assert result == WithFrozenSetItemValidation(codes=frozenset(["ABC", "XYZ", "DEF"]))

    def test_item_validation_short_fail(self, impl: Serializer) -> None:
        data = b'{"codes":["ABC","X","DEF"]}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithFrozenSetItemValidation, data)
        assert exc.value.messages == {"codes": {1: ["Invalid value."]}}

    def test_item_two_validators_pass(self, impl: Serializer) -> None:
        data = b'{"codes":["AB","CDE","FGHI"]}'
        result = impl.load(WithFrozenSetItemTwoValidators, data)
        assert result == WithFrozenSetItemTwoValidators(codes=frozenset(["AB", "CDE", "FGHI"]))

    def test_item_two_validators_first_fails(self, impl: Serializer) -> None:
        data = b'{"codes":["AB","X","CDE"]}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithFrozenSetItemTwoValidators, data)
        assert exc.value.messages == {"codes": {1: ["Invalid value."]}}

    def test_item_two_validators_second_fails(self, impl: Serializer) -> None:
        data = b'{"codes":["AB","TOOLONG","CDE"]}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithFrozenSetItemTwoValidators, data)
        assert exc.value.messages == {"codes": {1: ["Invalid value."]}}

    def test_item_wrong_type(self, impl: Serializer) -> None:
        data = b'{"items":[1,"not_int",3]}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(FrozenSetOf[int], data)
        assert exc.value.messages == {"items": {1: ["Not a valid integer."]}}

    def test_wrong_type_string(self, impl: Serializer) -> None:
        data = b'{"items":"not_a_frozenset"}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(FrozenSetOf[int], data)

        assert exc.value.messages == {"items": ["Not a valid frozenset."]}

    def test_wrong_type_object(self, impl: Serializer) -> None:
        data = b'{"items":{"key":1}}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(FrozenSetOf[int], data)
        assert exc.value.messages == {"items": ["Not a valid frozenset."]}

    def test_missing_required(self, impl: Serializer) -> None:
        data = b"{}"
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(FrozenSetOf[int], data)
        assert exc.value.messages == {"items": ["Missing data for required field."]}

    def test_custom_required_error(self, impl: Serializer) -> None:
        data = b"{}"
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithFrozenSetRequiredError, data)
        assert exc.value.messages == {"items": ["Custom required message"]}

    def test_custom_none_error(self, impl: Serializer) -> None:
        data = b'{"items":null}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithFrozenSetNoneError, data)
        assert exc.value.messages == {"items": ["Custom none message"]}

    def test_custom_invalid_error(self, impl: Serializer) -> None:
        data = b'{"items":"not_a_frozenset"}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithFrozenSetInvalidError, data)
        assert exc.value.messages == {"items": ["Custom invalid message"]}

    def test_missing(self, impl: Serializer) -> None:
        data = b"{}"
        result = impl.load(WithFrozenSetMissing, data)
        assert result == WithFrozenSetMissing()

    def test_missing_with_value(self, impl: Serializer) -> None:
        data = b'{"items":[1,2,3]}'
        result = impl.load(WithFrozenSetMissing, data)
        assert result == WithFrozenSetMissing(items=frozenset({1, 2, 3}))


class TestFrozenSetDumpInvalidType:
    """Test that invalid types in frozenset fields raise ValidationError on dump."""

    def test_string(self, impl: Serializer) -> None:
        obj = FrozenSetOf[int](**{"items": "not a frozenset"})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(FrozenSetOf[int], obj)

    def test_list(self, impl: Serializer) -> None:
        obj = FrozenSetOf[int](**{"items": [1, 2, 3]})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(FrozenSetOf[int], obj)

    def test_set(self, impl: Serializer) -> None:
        obj = FrozenSetOf[int](**{"items": {1, 2, 3}})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(FrozenSetOf[int], obj)

    def test_int(self, impl: Serializer) -> None:
        obj = FrozenSetOf[int](**{"items": 123})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(FrozenSetOf[int], obj)
