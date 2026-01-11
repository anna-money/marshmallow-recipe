import datetime
import decimal
import json
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
    @pytest.mark.parametrize(
        ("item_type", "value", "expected"),
        [
            pytest.param(str, {"a"}, b'{"items":["a"]}', id="str"),
            pytest.param(int, {42}, b'{"items":[42]}', id="int"),
            pytest.param(float, {3.14}, b'{"items":[3.14]}', id="float"),
            pytest.param(bool, {True}, b'{"items":[true]}', id="bool"),
            pytest.param(decimal.Decimal, {decimal.Decimal("1.23")}, b'{"items":["1.23"]}', id="decimal"),
            pytest.param(
                uuid.UUID,
                {uuid.UUID("12345678-1234-5678-1234-567812345678")},
                b'{"items":["12345678-1234-5678-1234-567812345678"]}',
                id="uuid",
            ),
            pytest.param(
                datetime.datetime,
                {datetime.datetime(2024, 1, 15, 10, 30, 0, tzinfo=datetime.UTC)},
                b'{"items":["2024-01-15T10:30:00+00:00"]}',
                id="datetime",
            ),
            pytest.param(datetime.date, {datetime.date(2024, 1, 15)}, b'{"items":["2024-01-15"]}', id="date"),
            pytest.param(datetime.time, {datetime.time(10, 30, 0)}, b'{"items":["10:30:00"]}', id="time"),
            pytest.param(Status, {Status.ACTIVE}, b'{"items":["active"]}', id="str_enum"),
            pytest.param(Priority, {Priority.HIGH}, b'{"items":[3]}', id="int_enum"),
        ],
    )
    def test_value(self, impl: Serializer, item_type: type, value: set, expected: bytes) -> None:
        obj = SetOf[item_type](items=value)
        result = impl.dump(SetOf[item_type], obj)
        assert result == expected

    def test_empty(self, impl: Serializer) -> None:
        obj = SetOf[int](items=set())
        result = impl.dump(SetOf[int], obj)
        assert result == b'{"items":[]}'

    def test_single_element(self, impl: Serializer) -> None:
        obj = SetOf[int](items={42})
        result = impl.dump(SetOf[int], obj)
        assert result == b'{"items":[42]}'

    def test_many_elements(self, impl: Serializer) -> None:
        items = set(range(100))
        obj = SetOf[int](items=items)
        result = impl.dump(SetOf[int], obj)
        parsed = json.loads(result)
        assert set(parsed["items"]) == items

    def test_optional_none(self, impl: Serializer) -> None:
        obj = OptionalSetOf[int](items=None)
        result = impl.dump(OptionalSetOf[int], obj)
        assert result == b"{}"

    def test_optional_value(self, impl: Serializer) -> None:
        obj = OptionalSetOf[int](items={42})
        result = impl.dump(OptionalSetOf[int], obj)
        assert result == b'{"items":[42]}'

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
    @pytest.mark.parametrize(
        ("item_type", "data", "expected_items"),
        [
            pytest.param(str, b'{"items":["a"]}', {"a"}, id="str"),
            pytest.param(int, b'{"items":[42]}', {42}, id="int"),
            pytest.param(float, b'{"items":[3.14]}', {3.14}, id="float"),
            pytest.param(bool, b'{"items":[true]}', {True}, id="bool"),
            pytest.param(decimal.Decimal, b'{"items":["1.23"]}', {decimal.Decimal("1.23")}, id="decimal"),
            pytest.param(
                uuid.UUID,
                b'{"items":["12345678-1234-5678-1234-567812345678"]}',
                {uuid.UUID("12345678-1234-5678-1234-567812345678")},
                id="uuid",
            ),
            pytest.param(
                datetime.datetime,
                b'{"items":["2024-01-15T10:30:00+00:00"]}',
                {datetime.datetime(2024, 1, 15, 10, 30, 0, tzinfo=datetime.UTC)},
                id="datetime",
            ),
            pytest.param(datetime.date, b'{"items":["2024-01-15"]}', {datetime.date(2024, 1, 15)}, id="date"),
            pytest.param(datetime.time, b'{"items":["10:30:00"]}', {datetime.time(10, 30, 0)}, id="time"),
            pytest.param(Status, b'{"items":["active"]}', {Status.ACTIVE}, id="str_enum"),
            pytest.param(Priority, b'{"items":[3]}', {Priority.HIGH}, id="int_enum"),
        ],
    )
    def test_value(self, impl: Serializer, item_type: type, data: bytes, expected_items: set) -> None:
        result = impl.load(SetOf[item_type], data)
        assert result == SetOf[item_type](items=expected_items)

    def test_empty(self, impl: Serializer) -> None:
        data = b'{"items":[]}'
        result = impl.load(SetOf[int], data)
        assert result == SetOf[int](items=set())

    def test_multiple_elements(self, impl: Serializer) -> None:
        data = b'{"items":[1,2,3]}'
        result = impl.load(SetOf[int], data)
        assert result == SetOf[int](items={1, 2, 3})

    def test_many_elements(self, impl: Serializer) -> None:
        items = list(range(100))
        data = json.dumps({"items": items}).encode()
        result = impl.load(SetOf[int], data)
        assert result == SetOf[int](items=set(items))

    def test_deduplication(self, impl: Serializer) -> None:
        data = b'{"items":[1,2,2,3,3,3]}'
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

    @pytest.mark.parametrize("data", [b'{"tags":["a","","ccc"]}', b'{"tags":["a","' + b"a" * 51 + b'"]}'])
    def test_item_two_validators_fail(self, impl: Serializer, data: bytes) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithSetItemTwoValidators, data)
        assert exc.value.messages == {"tags": {1: ["Invalid value."]}}

    def test_item_wrong_type(self, impl: Serializer) -> None:
        data = b'{"items":[1,"not_int",3]}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(SetOf[int], data)
        assert exc.value.messages == {"items": {1: ["Not a valid integer."]}}

    @pytest.mark.parametrize("data", [b'{"items":"not_a_set"}', b'{"items":{"key":1}}'])
    def test_wrong_type(self, impl: Serializer, data: bytes) -> None:
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


class TestSetEdgeCases:
    """Test set edge cases with boundary values and special scenarios."""

    def test_big_int_values(self, impl: Serializer) -> None:
        big_vals = {9223372036854775808, 18446744073709551616, 2**100}
        obj = SetOf[int](items=big_vals)
        result = impl.dump(SetOf[int], obj)
        loaded = impl.load(SetOf[int], result)
        assert loaded.items == big_vals

    def test_boundary_int_values(self, impl: Serializer) -> None:
        boundary_vals = {-9223372036854775808, 9223372036854775807, 0, -1, 1}
        obj = SetOf[int](items=boundary_vals)
        result = impl.dump(SetOf[int], obj)
        loaded = impl.load(SetOf[int], result)
        assert loaded.items == boundary_vals

    def test_unicode_string_values(self, impl: Serializer) -> None:
        unicode_vals = {"Привет", "你好", "🎉", "مرحبا"}
        obj = SetOf[str](items=unicode_vals)
        result = impl.dump(SetOf[str], obj)
        loaded = impl.load(SetOf[str], result)
        assert loaded.items == unicode_vals

    def test_empty_string_in_set(self, impl: Serializer) -> None:
        obj = SetOf[str](items={""})
        result = impl.dump(SetOf[str], obj)
        assert result == b'{"items":[""]}'

    def test_whitespace_strings_in_set(self, impl: Serializer) -> None:
        whitespace_vals = {" ", "\t", "\n", "  "}
        obj = SetOf[str](items=whitespace_vals)
        result = impl.dump(SetOf[str], obj)
        loaded = impl.load(SetOf[str], result)
        assert loaded.items == whitespace_vals

    def test_heavy_deduplication(self, impl: Serializer) -> None:
        data = b'{"items":[1,1,1,1,1,1,1,1,1,1,2,2,2,2,2,3]}'
        result = impl.load(SetOf[int], data)
        assert result == SetOf[int](items={1, 2, 3})


class TestSetDumpInvalidType:
    """Test that invalid types in set fields raise ValidationError on dump."""

    @pytest.mark.parametrize("value", ["not a set", [1, 2, 3], 123, {"a": 1}])
    def test_invalid_type(self, impl: Serializer, value: object) -> None:
        obj = SetOf[int](**{"items": value})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(SetOf[int], obj)
