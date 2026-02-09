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
    @pytest.mark.parametrize(
        ("schema_type", "obj", "expected"),
        [
            (SetOf[str], SetOf[str](items={"a"}), b'{"items":["a"]}'),
            (SetOf[int], SetOf[int](items={42}), b'{"items":[42]}'),
            (SetOf[float], SetOf[float](items={3.14}), b'{"items":[3.14]}'),
            (SetOf[bool], SetOf[bool](items={True}), b'{"items":[true]}'),
            (SetOf[decimal.Decimal], SetOf[decimal.Decimal](items={decimal.Decimal("1.23")}), b'{"items":["1.23"]}'),
            (
                SetOf[uuid.UUID],
                SetOf[uuid.UUID](items={uuid.UUID("12345678-1234-5678-1234-567812345678")}),
                b'{"items":["12345678-1234-5678-1234-567812345678"]}',
            ),
            (
                SetOf[datetime.datetime],
                SetOf[datetime.datetime](items={datetime.datetime(2024, 1, 15, 10, 30, 0, tzinfo=datetime.UTC)}),
                b'{"items":["2024-01-15T10:30:00+00:00"]}',
            ),
            (
                SetOf[datetime.date],
                SetOf[datetime.date](items={datetime.date(2024, 1, 15)}),
                b'{"items":["2024-01-15"]}',
            ),
            (SetOf[datetime.time], SetOf[datetime.time](items={datetime.time(10, 30, 0)}), b'{"items":["10:30:00"]}'),
        ],
    )
    def test_value(self, impl: Serializer, schema_type: type, obj: object, expected: bytes) -> None:
        result = impl.dump(schema_type, obj)
        assert result == expected

    @pytest.mark.parametrize(
        ("schema_type", "obj", "expected"),
        [
            (SetOf[Status], SetOf[Status](items={Status.ACTIVE}), b'{"items":["active"]}'),
            (SetOf[Priority], SetOf[Priority](items={Priority.HIGH}), b'{"items":[3]}'),
        ],
    )
    def test_enum(self, impl: Serializer, schema_type: type, obj: object, expected: bytes) -> None:
        result = impl.dump(schema_type, obj)
        assert result == expected

    def test_empty(self, impl: Serializer) -> None:
        obj = SetOf[int](items=set())
        result = impl.dump(SetOf[int], obj)
        assert result == b'{"items":[]}'

    @pytest.mark.parametrize(
        ("obj", "expected"),
        [(OptionalSetOf[int](items=None), b"{}"), (OptionalSetOf[int](items={42}), b'{"items":[42]}')],
    )
    def test_optional(self, impl: Serializer, obj: OptionalSetOf[int], expected: bytes) -> None:
        result = impl.dump(OptionalSetOf[int], obj)
        assert result == expected

    @pytest.mark.parametrize(
        ("obj", "none_value_handling", "expected"),
        [
            (OptionalSetOf[int](items=None), mr.NoneValueHandling.IGNORE, b"{}"),
            (OptionalSetOf[int](items=None), mr.NoneValueHandling.INCLUDE, b'{"items":null}'),
            (OptionalSetOf[int](items={42}), mr.NoneValueHandling.INCLUDE, b'{"items":[42]}'),
        ],
    )
    def test_none_handling(
        self, impl: Serializer, obj: OptionalSetOf[int], none_value_handling: mr.NoneValueHandling, expected: bytes
    ) -> None:
        result = impl.dump(OptionalSetOf[int], obj, none_value_handling=none_value_handling)
        assert result == expected

    @pytest.mark.parametrize(
        ("obj", "expected"), [(WithSetMissing(), b"{}"), (WithSetMissing(items={1}), b'{"items":[1]}')]
    )
    def test_missing(self, impl: Serializer, obj: WithSetMissing, expected: bytes) -> None:
        result = impl.dump(WithSetMissing, obj)
        assert result == expected

    def test_unsubscripted(self, impl: Serializer) -> None:
        obj = CollectionHolder[set](items={"se", 55})
        result = impl.dump(CollectionHolder[set], obj)
        assert result == b'{"items":["se",55]}' or result == b'{"items":[55,"se"]}'

    @pytest.mark.parametrize(
        "obj",
        [
            pytest.param(SetOf[int](**{"items": "not a set"}), id="string"),  # type: ignore[arg-type]
            pytest.param(SetOf[int](**{"items": [1, 2, 3]}), id="list"),  # type: ignore[arg-type]
            pytest.param(SetOf[int](**{"items": 123}), id="int"),  # type: ignore[arg-type]
            pytest.param(SetOf[int](**{"items": {"a": 1}}), id="dict"),  # type: ignore[arg-type]
        ],
    )
    def test_invalid_type(self, impl: Serializer, obj: SetOf[int]) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.dump(SetOf[int], obj)
        if impl.supports_proper_validation_errors_on_dump:
            assert exc.value.messages == {"items": ["Not a valid set."]}

    def test_custom_invalid_error(self, impl: Serializer) -> None:
        obj = WithSetInvalidError(**{"items": "not a set"})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.dump(WithSetInvalidError, obj)
        if impl.supports_proper_validation_errors_on_dump:
            assert exc.value.messages == {"items": ["Custom invalid message"]}


class TestSetLoad:
    @pytest.mark.parametrize(
        ("schema_type", "data", "expected"),
        [
            (SetOf[str], b'{"items":["a"]}', SetOf[str](items={"a"})),
            (SetOf[int], b'{"items":[42]}', SetOf[int](items={42})),
            (SetOf[float], b'{"items":[3.14]}', SetOf[float](items={3.14})),
            (SetOf[bool], b'{"items":[true]}', SetOf[bool](items={True})),
            (SetOf[decimal.Decimal], b'{"items":["1.23"]}', SetOf[decimal.Decimal](items={decimal.Decimal("1.23")})),
            (
                SetOf[uuid.UUID],
                b'{"items":["12345678-1234-5678-1234-567812345678"]}',
                SetOf[uuid.UUID](items={uuid.UUID("12345678-1234-5678-1234-567812345678")}),
            ),
            (
                SetOf[datetime.datetime],
                b'{"items":["2024-01-15T10:30:00+00:00"]}',
                SetOf[datetime.datetime](items={datetime.datetime(2024, 1, 15, 10, 30, 0, tzinfo=datetime.UTC)}),
            ),
            (
                SetOf[datetime.date],
                b'{"items":["2024-01-15"]}',
                SetOf[datetime.date](items={datetime.date(2024, 1, 15)}),
            ),
            (SetOf[datetime.time], b'{"items":["10:30:00"]}', SetOf[datetime.time](items={datetime.time(10, 30, 0)})),
        ],
    )
    def test_value(self, impl: Serializer, schema_type: type, data: bytes, expected: object) -> None:
        result = impl.load(schema_type, data)
        assert result == expected

    @pytest.mark.parametrize(
        ("schema_type", "data", "expected"),
        [
            (SetOf[Status], b'{"items":["active"]}', SetOf[Status](items={Status.ACTIVE})),
            (SetOf[Priority], b'{"items":[3]}', SetOf[Priority](items={Priority.HIGH})),
        ],
    )
    def test_enum(self, impl: Serializer, schema_type: type, data: bytes, expected: object) -> None:
        result = impl.load(schema_type, data)
        assert result == expected

    def test_empty(self, impl: Serializer) -> None:
        data = b'{"items":[]}'
        result = impl.load(SetOf[int], data)
        assert result == SetOf[int](items=set())

    def test_multiple_elements(self, impl: Serializer) -> None:
        data = b'{"items":[1,2,3]}'
        result = impl.load(SetOf[int], data)
        assert result == SetOf[int](items={1, 2, 3})

    @pytest.mark.parametrize(
        ("data", "expected"),
        [(b"{}", OptionalSetOf[int](items=None)), (b'{"items":[42]}', OptionalSetOf[int](items={42}))],
    )
    def test_optional(self, impl: Serializer, data: bytes, expected: OptionalSetOf[int]) -> None:
        result = impl.load(OptionalSetOf[int], data)
        assert result == expected

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

    @pytest.mark.parametrize(
        ("data", "error_messages"),
        [
            pytest.param(b'{"tags":["a","","ccc"]}', {"tags": {1: ["Invalid value."]}}, id="first_fails"),
            pytest.param(b'{"tags":["a","' + b"a" * 51 + b'"]}', {"tags": {1: ["Invalid value."]}}, id="second_fails"),
        ],
    )
    def test_item_two_validators_fail(
        self, impl: Serializer, data: bytes, error_messages: dict[str, dict[int, list[str]]]
    ) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithSetItemTwoValidators, data)
        assert exc.value.messages == error_messages

    def test_item_wrong_type(self, impl: Serializer) -> None:
        data = b'{"items":[1,"not_int",3]}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(SetOf[int], data)
        assert exc.value.messages == {"items": {1: ["Not a valid integer."]}}

    @pytest.mark.parametrize(
        ("data", "error_messages"),
        [
            pytest.param(b'{"items":"not_a_set"}', {"items": ["Not a valid set."]}, id="string"),
            pytest.param(b'{"items":{"key":1}}', {"items": ["Not a valid set."]}, id="object"),
        ],
    )
    def test_wrong_type(self, impl: Serializer, data: bytes, error_messages: dict[str, list[str]]) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(SetOf[int], data)
        assert exc.value.messages == error_messages

    def test_missing_required(self, impl: Serializer) -> None:
        data = b"{}"
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(SetOf[int], data)
        assert exc.value.messages == {"items": ["Missing data for required field."]}

    @pytest.mark.parametrize(
        ("data", "schema_type", "error_messages"),
        [
            pytest.param(b"{}", WithSetRequiredError, {"items": ["Custom required message"]}, id="required"),
            pytest.param(b'{"items":null}', WithSetNoneError, {"items": ["Custom none message"]}, id="none"),
            pytest.param(
                b'{"items":"not_a_set"}', WithSetInvalidError, {"items": ["Custom invalid message"]}, id="invalid"
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
        ("data", "expected"), [(b"{}", WithSetMissing()), (b'{"items":[1,2,3]}', WithSetMissing(items={1, 2, 3}))]
    )
    def test_missing(self, impl: Serializer, data: bytes, expected: WithSetMissing) -> None:
        result = impl.load(WithSetMissing, data)
        assert result == expected
