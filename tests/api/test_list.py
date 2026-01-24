import datetime
import decimal
import json
import uuid
from collections.abc import Mapping, Sequence
from typing import Any

import marshmallow
import marshmallow_recipe as mr
import pytest

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
    @pytest.mark.parametrize(
        ("schema_type", "obj", "expected"),
        [
            (ListOf[str], ListOf[str](items=["a", "b", "c"]), b'{"items":["a","b","c"]}'),
            (ListOf[int], ListOf[int](items=[1, 2, 3]), b'{"items":[1,2,3]}'),
            (ListOf[float], ListOf[float](items=[1.5, 2.5, 3.5]), b'{"items":[1.5,2.5,3.5]}'),
            (ListOf[bool], ListOf[bool](items=[True, False, True]), b'{"items":[true,false,true]}'),
            (
                ListOf[decimal.Decimal],
                ListOf[decimal.Decimal](items=[decimal.Decimal("1.23"), decimal.Decimal("4.56")]),
                b'{"items":["1.23","4.56"]}',
            ),
            (
                ListOf[uuid.UUID],
                ListOf[uuid.UUID](
                    items=[
                        uuid.UUID("12345678-1234-5678-1234-567812345678"),
                        uuid.UUID("87654321-4321-8765-4321-876543218765"),
                    ]
                ),
                b'{"items":["12345678-1234-5678-1234-567812345678","87654321-4321-8765-4321-876543218765"]}',
            ),
            (
                ListOf[datetime.datetime],
                ListOf[datetime.datetime](items=[datetime.datetime(2024, 1, 15, 10, 30, 0, tzinfo=datetime.UTC)]),
                b'{"items":["2024-01-15T10:30:00+00:00"]}',
            ),
            (
                ListOf[datetime.date],
                ListOf[datetime.date](items=[datetime.date(2024, 1, 15)]),
                b'{"items":["2024-01-15"]}',
            ),
            (ListOf[datetime.time], ListOf[datetime.time](items=[datetime.time(10, 30, 0)]), b'{"items":["10:30:00"]}'),
        ],
    )
    def test_value(self, impl: Serializer, schema_type: type, obj: object, expected: bytes) -> None:
        result = impl.dump(schema_type, obj)
        assert result == expected

    @pytest.mark.parametrize(
        ("schema_type", "obj", "expected"),
        [
            (ListOf[Status], ListOf[Status](items=[Status.ACTIVE, Status.PENDING]), b'{"items":["active","pending"]}'),
            (ListOf[Priority], ListOf[Priority](items=[Priority.LOW, Priority.HIGH]), b'{"items":[1,3]}'),
        ],
    )
    def test_enum(self, impl: Serializer, schema_type: type, obj: object, expected: bytes) -> None:
        result = impl.dump(schema_type, obj)
        assert result == expected

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

    @pytest.mark.parametrize(
        ("obj", "expected"),
        [(OptionalListOf[int](items=None), b"{}"), (OptionalListOf[int](items=[1, 2, 3]), b'{"items":[1,2,3]}')],
    )
    def test_optional(self, impl: Serializer, obj: OptionalListOf[int], expected: bytes) -> None:
        result = impl.dump(OptionalListOf[int], obj)
        assert result == expected

    @pytest.mark.parametrize(
        ("obj", "none_value_handling", "expected"),
        [
            (OptionalListOf[int](items=None), mr.NoneValueHandling.IGNORE, b"{}"),
            (OptionalListOf[int](items=None), mr.NoneValueHandling.INCLUDE, b'{"items":null}'),
            (OptionalListOf[int](items=[1, 2, 3]), mr.NoneValueHandling.INCLUDE, b'{"items":[1,2,3]}'),
        ],
    )
    def test_none_handling(
        self, impl: Serializer, obj: OptionalListOf[int], none_value_handling: mr.NoneValueHandling, expected: bytes
    ) -> None:
        result = impl.dump(OptionalListOf[int], obj, none_value_handling=none_value_handling)
        assert result == expected

    def test_item_validation(self, impl: Serializer) -> None:
        obj = WithListItemValidation(items=[5, 10, 15])
        result = impl.dump(WithListItemValidation, obj)
        assert result == b'{"items":[5,10,15]}'

    @pytest.mark.parametrize(
        ("obj", "expected"), [(WithListMissing(), b"{}"), (WithListMissing(items=[1, 2, 3]), b'{"items":[1,2,3]}')]
    )
    def test_missing(self, impl: Serializer, obj: WithListMissing, expected: bytes) -> None:
        result = impl.dump(WithListMissing, obj)
        assert result == expected

    def test_unsubscripted(self, impl: Serializer) -> None:
        obj = CollectionHolder[list](items=["str", 123, {"a": "s"}])
        result = impl.dump(CollectionHolder[list], obj)
        assert result == b'{"items":["str",123,{"a":"s"}]}'

    @pytest.mark.parametrize(
        "obj",
        [
            pytest.param(ListOf[int](**{"items": "not a list"}), id="string"),  # type: ignore[arg-type]
            pytest.param(ListOf[int](**{"items": {"a": 1}}), id="dict"),  # type: ignore[arg-type]
            pytest.param(ListOf[int](**{"items": 123}), id="int"),  # type: ignore[arg-type]
            pytest.param(ListOf[int](**{"items": (1, 2, 3)}), id="tuple"),  # type: ignore[arg-type]
        ],
    )
    def test_invalid_type(self, impl: Serializer, obj: ListOf[int]) -> None:
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(ListOf[int], obj)


class TestListLoad:
    @pytest.mark.parametrize(
        ("schema_type", "data", "expected"),
        [
            (ListOf[str], b'{"items":["a","b","c"]}', ListOf[str](items=["a", "b", "c"])),
            (ListOf[int], b'{"items":[1,2,3]}', ListOf[int](items=[1, 2, 3])),
            (ListOf[float], b'{"items":[1.5,2.5,3.5]}', ListOf[float](items=[1.5, 2.5, 3.5])),
            (ListOf[bool], b'{"items":[true,false,true]}', ListOf[bool](items=[True, False, True])),
            (
                ListOf[decimal.Decimal],
                b'{"items":["1.23","4.56"]}',
                ListOf[decimal.Decimal](items=[decimal.Decimal("1.23"), decimal.Decimal("4.56")]),
            ),
            (
                ListOf[uuid.UUID],
                b'{"items":["12345678-1234-5678-1234-567812345678","87654321-4321-8765-4321-876543218765"]}',
                ListOf[uuid.UUID](
                    items=[
                        uuid.UUID("12345678-1234-5678-1234-567812345678"),
                        uuid.UUID("87654321-4321-8765-4321-876543218765"),
                    ]
                ),
            ),
            (
                ListOf[datetime.datetime],
                b'{"items":["2024-01-15T10:30:00+00:00"]}',
                ListOf[datetime.datetime](items=[datetime.datetime(2024, 1, 15, 10, 30, 0, tzinfo=datetime.UTC)]),
            ),
            (
                ListOf[datetime.date],
                b'{"items":["2024-01-15"]}',
                ListOf[datetime.date](items=[datetime.date(2024, 1, 15)]),
            ),
            (ListOf[datetime.time], b'{"items":["10:30:00"]}', ListOf[datetime.time](items=[datetime.time(10, 30, 0)])),
        ],
    )
    def test_value(self, impl: Serializer, schema_type: type, data: bytes, expected: object) -> None:
        result = impl.load(schema_type, data)
        assert result == expected

    @pytest.mark.parametrize(
        ("schema_type", "data", "expected"),
        [
            (ListOf[Status], b'{"items":["active","pending"]}', ListOf[Status](items=[Status.ACTIVE, Status.PENDING])),
            (ListOf[Priority], b'{"items":[1,3]}', ListOf[Priority](items=[Priority.LOW, Priority.HIGH])),
        ],
    )
    def test_enum(self, impl: Serializer, schema_type: type, data: bytes, expected: object) -> None:
        result = impl.load(schema_type, data)
        assert result == expected

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

    @pytest.mark.parametrize(
        ("data", "expected"),
        [(b"{}", OptionalListOf[int](items=None)), (b'{"items":[1,2,3]}', OptionalListOf[int](items=[1, 2, 3]))],
    )
    def test_optional(self, impl: Serializer, data: bytes, expected: OptionalListOf[int]) -> None:
        result = impl.load(OptionalListOf[int], data)
        assert result == expected

    def test_item_validation_pass(self, impl: Serializer) -> None:
        data = b'{"items":[1,2,3]}'
        result = impl.load(WithListItemValidation, data)
        assert result == WithListItemValidation(items=[1, 2, 3])

    @pytest.mark.parametrize(
        ("data", "error_messages"),
        [
            pytest.param(b'{"items":[1,0,3]}', {"items": {1: ["Invalid value."]}}, id="zero"),
            pytest.param(b'{"items":[1,-5,3]}', {"items": {1: ["Invalid value."]}}, id="negative"),
        ],
    )
    def test_item_validation_fail(
        self, impl: Serializer, data: bytes, error_messages: dict[str, dict[int, list[str]]]
    ) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithListItemValidation, data)
        assert exc.value.messages == error_messages

    def test_item_two_validators_pass(self, impl: Serializer) -> None:
        data = b'{"items":[1,50,99]}'
        result = impl.load(WithListItemTwoValidators, data)
        assert result == WithListItemTwoValidators(items=[1, 50, 99])

    @pytest.mark.parametrize(
        ("data", "error_messages"),
        [
            pytest.param(b'{"items":[1,0,50]}', {"items": {1: ["Invalid value."]}}, id="first_fails"),
            pytest.param(b'{"items":[1,150,50]}', {"items": {1: ["Invalid value."]}}, id="second_fails"),
        ],
    )
    def test_item_two_validators_fail(
        self, impl: Serializer, data: bytes, error_messages: dict[str, dict[int, list[str]]]
    ) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithListItemTwoValidators, data)
        assert exc.value.messages == error_messages

    def test_item_wrong_type(self, impl: Serializer) -> None:
        data = b'{"items":[1,"not_int",3]}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ListOf[int], data)
        assert exc.value.messages == {"items": {1: ["Not a valid integer."]}}

    @pytest.mark.parametrize(
        ("data", "error_messages"),
        [
            pytest.param(b'{"items":"not_a_list"}', {"items": ["Not a valid list."]}, id="string"),
            pytest.param(b'{"items":{"key":1}}', {"items": ["Not a valid list."]}, id="object"),
        ],
    )
    def test_wrong_type(self, impl: Serializer, data: bytes, error_messages: dict[str, list[str]]) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ListOf[int], data)
        assert exc.value.messages == error_messages

    def test_missing_required(self, impl: Serializer) -> None:
        data = b"{}"
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(ListOf[int], data)
        assert exc.value.messages == {"items": ["Missing data for required field."]}

    @pytest.mark.parametrize(
        ("data", "schema_type", "error_messages"),
        [
            pytest.param(b"{}", WithListRequiredError, {"items": ["Custom required message"]}, id="required"),
            pytest.param(b'{"items":null}', WithListNoneError, {"items": ["Custom none message"]}, id="none"),
            pytest.param(
                b'{"items":"not_a_list"}', WithListInvalidError, {"items": ["Custom invalid message"]}, id="invalid"
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
        ("data", "expected"), [(b"{}", WithListMissing()), (b'{"items":[1,2,3]}', WithListMissing(items=[1, 2, 3]))]
    )
    def test_missing(self, impl: Serializer, data: bytes, expected: WithListMissing) -> None:
        result = impl.load(WithListMissing, data)
        assert result == expected

    def test_strip_whitespace(self, impl: Serializer) -> None:
        data = b'{"items":[" hello "," world "]}'
        result = impl.load(WithListStripWhitespace, data)
        assert result == WithListStripWhitespace(items=["hello", "world"])
