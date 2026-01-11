import datetime
import decimal
import json
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
    @pytest.mark.parametrize(
        ("item_type", "value", "expected"),
        [
            pytest.param(str, frozenset({"a"}), b'{"items":["a"]}', id="str"),
            pytest.param(int, frozenset({42}), b'{"items":[42]}', id="int"),
            pytest.param(float, frozenset({3.14}), b'{"items":[3.14]}', id="float"),
            pytest.param(bool, frozenset({True}), b'{"items":[true]}', id="bool"),
            pytest.param(decimal.Decimal, frozenset({decimal.Decimal("1.23")}), b'{"items":["1.23"]}', id="decimal"),
            pytest.param(
                uuid.UUID,
                frozenset({uuid.UUID("12345678-1234-5678-1234-567812345678")}),
                b'{"items":["12345678-1234-5678-1234-567812345678"]}',
                id="uuid",
            ),
            pytest.param(
                datetime.datetime,
                frozenset({datetime.datetime(2024, 1, 15, 10, 30, 0, tzinfo=datetime.UTC)}),
                b'{"items":["2024-01-15T10:30:00+00:00"]}',
                id="datetime",
            ),
            pytest.param(
                datetime.date, frozenset({datetime.date(2024, 1, 15)}), b'{"items":["2024-01-15"]}', id="date"
            ),
            pytest.param(datetime.time, frozenset({datetime.time(10, 30, 0)}), b'{"items":["10:30:00"]}', id="time"),
            pytest.param(Status, frozenset({Status.ACTIVE}), b'{"items":["active"]}', id="str_enum"),
            pytest.param(Priority, frozenset({Priority.HIGH}), b'{"items":[3]}', id="int_enum"),
        ],
    )
    def test_value(self, impl: Serializer, item_type: type, value: frozenset, expected: bytes) -> None:
        obj = FrozenSetOf[item_type](items=value)
        result = impl.dump(FrozenSetOf[item_type], obj)
        assert result == expected

    def test_empty(self, impl: Serializer) -> None:
        obj = FrozenSetOf[int](items=frozenset())
        result = impl.dump(FrozenSetOf[int], obj)
        assert result == b'{"items":[]}'

    def test_single_element(self, impl: Serializer) -> None:
        obj = FrozenSetOf[int](items=frozenset({42}))
        result = impl.dump(FrozenSetOf[int], obj)
        assert result == b'{"items":[42]}'

    def test_many_elements(self, impl: Serializer) -> None:
        items = frozenset(range(100))
        obj = FrozenSetOf[int](items=items)
        result = impl.dump(FrozenSetOf[int], obj)
        parsed = json.loads(result)
        assert frozenset(parsed["items"]) == items

    def test_optional_none(self, impl: Serializer) -> None:
        obj = OptionalFrozenSetOf[int](items=None)
        result = impl.dump(OptionalFrozenSetOf[int], obj)
        assert result == b"{}"

    def test_optional_value(self, impl: Serializer) -> None:
        obj = OptionalFrozenSetOf[int](items=frozenset({42}))
        result = impl.dump(OptionalFrozenSetOf[int], obj)
        assert result == b'{"items":[42]}'

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
    @pytest.mark.parametrize(
        ("item_type", "data", "expected_items"),
        [
            pytest.param(str, b'{"items":["a"]}', frozenset({"a"}), id="str"),
            pytest.param(int, b'{"items":[42]}', frozenset({42}), id="int"),
            pytest.param(float, b'{"items":[3.14]}', frozenset({3.14}), id="float"),
            pytest.param(bool, b'{"items":[true]}', frozenset({True}), id="bool"),
            pytest.param(decimal.Decimal, b'{"items":["1.23"]}', frozenset({decimal.Decimal("1.23")}), id="decimal"),
            pytest.param(
                uuid.UUID,
                b'{"items":["12345678-1234-5678-1234-567812345678"]}',
                frozenset({uuid.UUID("12345678-1234-5678-1234-567812345678")}),
                id="uuid",
            ),
            pytest.param(
                datetime.datetime,
                b'{"items":["2024-01-15T10:30:00+00:00"]}',
                frozenset({datetime.datetime(2024, 1, 15, 10, 30, 0, tzinfo=datetime.UTC)}),
                id="datetime",
            ),
            pytest.param(
                datetime.date, b'{"items":["2024-01-15"]}', frozenset({datetime.date(2024, 1, 15)}), id="date"
            ),
            pytest.param(datetime.time, b'{"items":["10:30:00"]}', frozenset({datetime.time(10, 30, 0)}), id="time"),
            pytest.param(Status, b'{"items":["active"]}', frozenset({Status.ACTIVE}), id="str_enum"),
            pytest.param(Priority, b'{"items":[3]}', frozenset({Priority.HIGH}), id="int_enum"),
        ],
    )
    def test_value(self, impl: Serializer, item_type: type, data: bytes, expected_items: frozenset) -> None:
        result = impl.load(FrozenSetOf[item_type], data)
        assert result == FrozenSetOf[item_type](items=expected_items)

    def test_empty(self, impl: Serializer) -> None:
        data = b'{"items":[]}'
        result = impl.load(FrozenSetOf[int], data)
        assert result == FrozenSetOf[int](items=frozenset())

    def test_multiple_elements(self, impl: Serializer) -> None:
        data = b'{"items":[1,2,3]}'
        result = impl.load(FrozenSetOf[int], data)
        assert result == FrozenSetOf[int](items=frozenset({1, 2, 3}))

    def test_many_elements(self, impl: Serializer) -> None:
        items = list(range(100))
        data = json.dumps({"items": items}).encode()
        result = impl.load(FrozenSetOf[int], data)
        assert result == FrozenSetOf[int](items=frozenset(items))

    def test_deduplication(self, impl: Serializer) -> None:
        data = b'{"items":[1,2,2,3,3,3]}'
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

    @pytest.mark.parametrize("data", [b'{"codes":["AB","X","CDE"]}', b'{"codes":["AB","TOOLONG","CDE"]}'])
    def test_item_two_validators_fail(self, impl: Serializer, data: bytes) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithFrozenSetItemTwoValidators, data)
        assert exc.value.messages == {"codes": {1: ["Invalid value."]}}

    def test_item_wrong_type(self, impl: Serializer) -> None:
        data = b'{"items":[1,"not_int",3]}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(FrozenSetOf[int], data)
        assert exc.value.messages == {"items": {1: ["Not a valid integer."]}}

    @pytest.mark.parametrize("data", [b'{"items":"not_a_frozenset"}', b'{"items":{"key":1}}'])
    def test_wrong_type(self, impl: Serializer, data: bytes) -> None:
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


class TestFrozenSetEdgeCases:
    """Test frozenset edge cases with boundary values and special scenarios."""

    def test_big_int_values(self, impl: Serializer) -> None:
        big_vals = frozenset({9223372036854775808, 18446744073709551616, 2**100})
        obj = FrozenSetOf[int](items=big_vals)
        result = impl.dump(FrozenSetOf[int], obj)
        loaded = impl.load(FrozenSetOf[int], result)
        assert loaded.items == big_vals

    def test_boundary_int_values(self, impl: Serializer) -> None:
        boundary_vals = frozenset({-9223372036854775808, 9223372036854775807, 0, -1, 1})
        obj = FrozenSetOf[int](items=boundary_vals)
        result = impl.dump(FrozenSetOf[int], obj)
        loaded = impl.load(FrozenSetOf[int], result)
        assert loaded.items == boundary_vals

    def test_unicode_string_values(self, impl: Serializer) -> None:
        unicode_vals = frozenset({"Привет", "你好", "🎉", "مرحبا"})
        obj = FrozenSetOf[str](items=unicode_vals)
        result = impl.dump(FrozenSetOf[str], obj)
        loaded = impl.load(FrozenSetOf[str], result)
        assert loaded.items == unicode_vals

    def test_empty_string_in_frozenset(self, impl: Serializer) -> None:
        obj = FrozenSetOf[str](items=frozenset({""}))
        result = impl.dump(FrozenSetOf[str], obj)
        assert result == b'{"items":[""]}'

    def test_whitespace_strings_in_frozenset(self, impl: Serializer) -> None:
        whitespace_vals = frozenset({" ", "\t", "\n", "  "})
        obj = FrozenSetOf[str](items=whitespace_vals)
        result = impl.dump(FrozenSetOf[str], obj)
        loaded = impl.load(FrozenSetOf[str], result)
        assert loaded.items == whitespace_vals

    def test_heavy_deduplication(self, impl: Serializer) -> None:
        data = b'{"items":[1,1,1,1,1,1,1,1,1,1,2,2,2,2,2,3]}'
        result = impl.load(FrozenSetOf[int], data)
        assert result == FrozenSetOf[int](items=frozenset({1, 2, 3}))


class TestFrozenSetDumpInvalidType:
    """Test that invalid types in frozenset fields raise ValidationError on dump."""

    @pytest.mark.parametrize("value", ["not a frozenset", [1, 2, 3], {1, 2, 3}, 123])
    def test_invalid_type(self, impl: Serializer, value: object) -> None:
        obj = FrozenSetOf[int](**{"items": value})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(FrozenSetOf[int], obj)
