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
    @pytest.mark.parametrize(
        ("schema_type", "obj", "expected"),
        [
            (FrozenSetOf[str], FrozenSetOf[str](items=frozenset({"a"})), b'{"items":["a"]}'),
            (FrozenSetOf[int], FrozenSetOf[int](items=frozenset({42})), b'{"items":[42]}'),
            (FrozenSetOf[float], FrozenSetOf[float](items=frozenset({3.14})), b'{"items":[3.14]}'),
            (FrozenSetOf[bool], FrozenSetOf[bool](items=frozenset({True})), b'{"items":[true]}'),
            (
                FrozenSetOf[decimal.Decimal],
                FrozenSetOf[decimal.Decimal](items=frozenset({decimal.Decimal("1.23")})),
                b'{"items":["1.23"]}',
            ),
            (
                FrozenSetOf[uuid.UUID],
                FrozenSetOf[uuid.UUID](items=frozenset({uuid.UUID("12345678-1234-5678-1234-567812345678")})),
                b'{"items":["12345678-1234-5678-1234-567812345678"]}',
            ),
            (
                FrozenSetOf[datetime.datetime],
                FrozenSetOf[datetime.datetime](
                    items=frozenset({datetime.datetime(2024, 1, 15, 10, 30, 0, tzinfo=datetime.UTC)})
                ),
                b'{"items":["2024-01-15T10:30:00+00:00"]}',
            ),
            (
                FrozenSetOf[datetime.date],
                FrozenSetOf[datetime.date](items=frozenset({datetime.date(2024, 1, 15)})),
                b'{"items":["2024-01-15"]}',
            ),
            (
                FrozenSetOf[datetime.time],
                FrozenSetOf[datetime.time](items=frozenset({datetime.time(10, 30, 0)})),
                b'{"items":["10:30:00"]}',
            ),
        ],
    )
    def test_value(self, impl: Serializer, schema_type: type, obj: object, expected: bytes) -> None:
        result = impl.dump(schema_type, obj)
        assert result == expected

    @pytest.mark.parametrize(
        ("schema_type", "obj", "expected"),
        [
            (FrozenSetOf[Status], FrozenSetOf[Status](items=frozenset({Status.ACTIVE})), b'{"items":["active"]}'),
            (FrozenSetOf[Priority], FrozenSetOf[Priority](items=frozenset({Priority.HIGH})), b'{"items":[3]}'),
        ],
    )
    def test_enum(self, impl: Serializer, schema_type: type, obj: object, expected: bytes) -> None:
        result = impl.dump(schema_type, obj)
        assert result == expected

    def test_empty(self, impl: Serializer) -> None:
        obj = FrozenSetOf[int](items=frozenset())
        result = impl.dump(FrozenSetOf[int], obj)
        assert result == b'{"items":[]}'

    @pytest.mark.parametrize(
        ("obj", "expected"),
        [
            (OptionalFrozenSetOf[int](items=None), b"{}"),
            (OptionalFrozenSetOf[int](items=frozenset({42})), b'{"items":[42]}'),
        ],
    )
    def test_optional(self, impl: Serializer, obj: OptionalFrozenSetOf[int], expected: bytes) -> None:
        result = impl.dump(OptionalFrozenSetOf[int], obj)
        assert result == expected

    @pytest.mark.parametrize(
        ("obj", "none_value_handling", "expected"),
        [
            (OptionalFrozenSetOf[int](items=None), mr.NoneValueHandling.IGNORE, b"{}"),
            (OptionalFrozenSetOf[int](items=None), mr.NoneValueHandling.INCLUDE, b'{"items":null}'),
            (OptionalFrozenSetOf[int](items=frozenset({42})), mr.NoneValueHandling.INCLUDE, b'{"items":[42]}'),
        ],
    )
    def test_none_handling(
        self,
        impl: Serializer,
        obj: OptionalFrozenSetOf[int],
        none_value_handling: mr.NoneValueHandling,
        expected: bytes,
    ) -> None:
        result = impl.dump(OptionalFrozenSetOf[int], obj, none_value_handling=none_value_handling)
        assert result == expected

    @pytest.mark.parametrize(
        ("obj", "expected"),
        [(WithFrozenSetMissing(), b"{}"), (WithFrozenSetMissing(items=frozenset({1})), b'{"items":[1]}')],
    )
    def test_missing(self, impl: Serializer, obj: WithFrozenSetMissing, expected: bytes) -> None:
        result = impl.dump(WithFrozenSetMissing, obj)
        assert result == expected

    def test_unsubscripted(self, impl: Serializer) -> None:
        obj = CollectionHolder[frozenset](items=frozenset(["fs", 77]))
        result = impl.dump(CollectionHolder[frozenset], obj)
        assert result == b'{"items":["fs",77]}' or result == b'{"items":[77,"fs"]}'

    @pytest.mark.parametrize(
        "obj",
        [
            pytest.param(FrozenSetOf[int](**{"items": "not a frozenset"}), id="string"),  # type: ignore[arg-type]
            pytest.param(FrozenSetOf[int](**{"items": [1, 2, 3]}), id="list"),  # type: ignore[arg-type]
            pytest.param(FrozenSetOf[int](**{"items": {1, 2, 3}}), id="set"),  # type: ignore[arg-type]
            pytest.param(FrozenSetOf[int](**{"items": 123}), id="int"),  # type: ignore[arg-type]
        ],
    )
    def test_invalid_type(self, impl: Serializer, obj: FrozenSetOf[int]) -> None:
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(FrozenSetOf[int], obj)


class TestFrozenSetLoad:
    @pytest.mark.parametrize(
        ("schema_type", "data", "expected"),
        [
            (FrozenSetOf[str], b'{"items":["a"]}', FrozenSetOf[str](items=frozenset({"a"}))),
            (FrozenSetOf[int], b'{"items":[42]}', FrozenSetOf[int](items=frozenset({42}))),
            (FrozenSetOf[float], b'{"items":[3.14]}', FrozenSetOf[float](items=frozenset({3.14}))),
            (FrozenSetOf[bool], b'{"items":[true]}', FrozenSetOf[bool](items=frozenset({True}))),
            (
                FrozenSetOf[decimal.Decimal],
                b'{"items":["1.23"]}',
                FrozenSetOf[decimal.Decimal](items=frozenset({decimal.Decimal("1.23")})),
            ),
            (
                FrozenSetOf[uuid.UUID],
                b'{"items":["12345678-1234-5678-1234-567812345678"]}',
                FrozenSetOf[uuid.UUID](items=frozenset({uuid.UUID("12345678-1234-5678-1234-567812345678")})),
            ),
            (
                FrozenSetOf[datetime.datetime],
                b'{"items":["2024-01-15T10:30:00+00:00"]}',
                FrozenSetOf[datetime.datetime](
                    items=frozenset({datetime.datetime(2024, 1, 15, 10, 30, 0, tzinfo=datetime.UTC)})
                ),
            ),
            (
                FrozenSetOf[datetime.date],
                b'{"items":["2024-01-15"]}',
                FrozenSetOf[datetime.date](items=frozenset({datetime.date(2024, 1, 15)})),
            ),
            (
                FrozenSetOf[datetime.time],
                b'{"items":["10:30:00"]}',
                FrozenSetOf[datetime.time](items=frozenset({datetime.time(10, 30, 0)})),
            ),
        ],
    )
    def test_value(self, impl: Serializer, schema_type: type, data: bytes, expected: object) -> None:
        result = impl.load(schema_type, data)
        assert result == expected

    @pytest.mark.parametrize(
        ("schema_type", "data", "expected"),
        [
            (FrozenSetOf[Status], b'{"items":["active"]}', FrozenSetOf[Status](items=frozenset({Status.ACTIVE}))),
            (FrozenSetOf[Priority], b'{"items":[3]}', FrozenSetOf[Priority](items=frozenset({Priority.HIGH}))),
        ],
    )
    def test_enum(self, impl: Serializer, schema_type: type, data: bytes, expected: object) -> None:
        result = impl.load(schema_type, data)
        assert result == expected

    def test_empty(self, impl: Serializer) -> None:
        data = b'{"items":[]}'
        result = impl.load(FrozenSetOf[int], data)
        assert result == FrozenSetOf[int](items=frozenset())

    def test_multiple_elements(self, impl: Serializer) -> None:
        data = b'{"items":[1,2,3]}'
        result = impl.load(FrozenSetOf[int], data)
        assert result == FrozenSetOf[int](items=frozenset({1, 2, 3}))

    @pytest.mark.parametrize(
        ("data", "expected"),
        [
            (b"{}", OptionalFrozenSetOf[int](items=None)),
            (b'{"items":[42]}', OptionalFrozenSetOf[int](items=frozenset({42}))),
        ],
    )
    def test_optional(self, impl: Serializer, data: bytes, expected: OptionalFrozenSetOf[int]) -> None:
        result = impl.load(OptionalFrozenSetOf[int], data)
        assert result == expected

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

    @pytest.mark.parametrize(
        ("data", "error_messages"),
        [
            pytest.param(b'{"codes":["AB","X","CDE"]}', {"codes": {1: ["Invalid value."]}}, id="first_fails"),
            pytest.param(b'{"codes":["AB","TOOLONG","CDE"]}', {"codes": {1: ["Invalid value."]}}, id="second_fails"),
        ],
    )
    def test_item_two_validators_fail(
        self, impl: Serializer, data: bytes, error_messages: dict[str, dict[int, list[str]]]
    ) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithFrozenSetItemTwoValidators, data)
        assert exc.value.messages == error_messages

    def test_item_wrong_type(self, impl: Serializer) -> None:
        data = b'{"items":[1,"not_int",3]}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(FrozenSetOf[int], data)
        assert exc.value.messages == {"items": {1: ["Not a valid integer."]}}

    @pytest.mark.parametrize(
        ("data", "error_messages"),
        [
            pytest.param(b'{"items":"not_a_frozenset"}', {"items": ["Not a valid frozenset."]}, id="string"),
            pytest.param(b'{"items":{"key":1}}', {"items": ["Not a valid frozenset."]}, id="object"),
        ],
    )
    def test_wrong_type(self, impl: Serializer, data: bytes, error_messages: dict[str, list[str]]) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(FrozenSetOf[int], data)
        assert exc.value.messages == error_messages

    def test_missing_required(self, impl: Serializer) -> None:
        data = b"{}"
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(FrozenSetOf[int], data)
        assert exc.value.messages == {"items": ["Missing data for required field."]}

    @pytest.mark.parametrize(
        ("data", "schema_type", "error_messages"),
        [
            pytest.param(b"{}", WithFrozenSetRequiredError, {"items": ["Custom required message"]}, id="required"),
            pytest.param(b'{"items":null}', WithFrozenSetNoneError, {"items": ["Custom none message"]}, id="none"),
            pytest.param(
                b'{"items":"not_a_frozenset"}',
                WithFrozenSetInvalidError,
                {"items": ["Custom invalid message"]},
                id="invalid",
            ),
        ],
    )
    def test_custom_error(
        self, impl: Serializer, data: bytes, schema_type: type, error_messages: dict[str, list[str]]
    ) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(schema_type, data)
        assert exc.value.messages == error_messages

    @pytest.mark.parametrize(
        ("data", "expected"),
        [(b"{}", WithFrozenSetMissing()), (b'{"items":[1,2,3]}', WithFrozenSetMissing(items=frozenset({1, 2, 3})))],
    )
    def test_missing(self, impl: Serializer, data: bytes, expected: WithFrozenSetMissing) -> None:
        result = impl.load(WithFrozenSetMissing, data)
        assert result == expected
