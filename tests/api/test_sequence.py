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
    @pytest.mark.parametrize(
        ("schema_type", "obj", "expected"),
        [
            (SequenceOf[str], SequenceOf[str](items=["a", "b", "c"]), b'{"items":["a","b","c"]}'),
            (SequenceOf[int], SequenceOf[int](items=[1, 2, 3]), b'{"items":[1,2,3]}'),
            (SequenceOf[float], SequenceOf[float](items=[1.5, 2.5, 3.5]), b'{"items":[1.5,2.5,3.5]}'),
            (SequenceOf[bool], SequenceOf[bool](items=[True, False, True]), b'{"items":[true,false,true]}'),
            (
                SequenceOf[decimal.Decimal],
                SequenceOf[decimal.Decimal](items=[decimal.Decimal("1.23"), decimal.Decimal("4.56")]),
                b'{"items":["1.23","4.56"]}',
            ),
            (
                SequenceOf[uuid.UUID],
                SequenceOf[uuid.UUID](
                    items=[
                        uuid.UUID("12345678-1234-5678-1234-567812345678"),
                        uuid.UUID("87654321-4321-8765-4321-876543218765"),
                    ]
                ),
                b'{"items":["12345678-1234-5678-1234-567812345678","87654321-4321-8765-4321-876543218765"]}',
            ),
            (
                SequenceOf[datetime.datetime],
                SequenceOf[datetime.datetime](items=[datetime.datetime(2024, 1, 15, 10, 30, 0, tzinfo=datetime.UTC)]),
                b'{"items":["2024-01-15T10:30:00+00:00"]}',
            ),
            (
                SequenceOf[datetime.date],
                SequenceOf[datetime.date](items=[datetime.date(2024, 1, 15)]),
                b'{"items":["2024-01-15"]}',
            ),
            (
                SequenceOf[datetime.time],
                SequenceOf[datetime.time](items=[datetime.time(10, 30, 0)]),
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
            (
                SequenceOf[Status],
                SequenceOf[Status](items=[Status.ACTIVE, Status.PENDING]),
                b'{"items":["active","pending"]}',
            ),
            (SequenceOf[Priority], SequenceOf[Priority](items=[Priority.LOW, Priority.HIGH]), b'{"items":[1,3]}'),
        ],
    )
    def test_enum(self, impl: Serializer, schema_type: type, obj: object, expected: bytes) -> None:
        result = impl.dump(schema_type, obj)
        assert result == expected

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

    @pytest.mark.parametrize(
        ("obj", "expected"),
        [
            (OptionalSequenceOf[int](items=None), b"{}"),
            (OptionalSequenceOf[int](items=[1, 2, 3]), b'{"items":[1,2,3]}'),
        ],
    )
    def test_optional(self, impl: Serializer, obj: OptionalSequenceOf[int], expected: bytes) -> None:
        result = impl.dump(OptionalSequenceOf[int], obj)
        assert result == expected

    @pytest.mark.parametrize(
        ("obj", "none_value_handling", "expected"),
        [
            (OptionalSequenceOf[int](items=None), mr.NoneValueHandling.IGNORE, b"{}"),
            (OptionalSequenceOf[int](items=None), mr.NoneValueHandling.INCLUDE, b'{"items":null}'),
            (OptionalSequenceOf[int](items=[1, 2, 3]), mr.NoneValueHandling.INCLUDE, b'{"items":[1,2,3]}'),
        ],
    )
    def test_none_handling(
        self, impl: Serializer, obj: OptionalSequenceOf[int], none_value_handling: mr.NoneValueHandling, expected: bytes
    ) -> None:
        result = impl.dump(OptionalSequenceOf[int], obj, none_value_handling=none_value_handling)
        assert result == expected

    def test_item_validation(self, impl: Serializer) -> None:
        obj = WithSequenceValidation(items=[5, 10, 15])
        result = impl.dump(WithSequenceValidation, obj)
        assert result == b'{"items":[5,10,15]}'

    @pytest.mark.parametrize(
        ("obj", "expected"),
        [(WithSequenceMissing(), b"{}"), (WithSequenceMissing(items=[1, 2, 3]), b'{"items":[1,2,3]}')],
    )
    def test_missing(self, impl: Serializer, obj: WithSequenceMissing, expected: bytes) -> None:
        result = impl.dump(WithSequenceMissing, obj)
        assert result == expected

    def test_custom_invalid_error(self, impl: Serializer) -> None:
        obj = WithSequenceInvalidError(**{"items": "not a sequence"})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.dump(WithSequenceInvalidError, obj)
        if impl.supports_proper_validation_errors_on_dump:
            assert exc.value.messages == {"items": ["Custom invalid message"]}


class TestSequenceLoad:
    @pytest.mark.parametrize(
        ("schema_type", "data", "expected"),
        [
            (SequenceOf[str], b'{"items":["a","b","c"]}', SequenceOf[str](items=["a", "b", "c"])),
            (SequenceOf[int], b'{"items":[1,2,3]}', SequenceOf[int](items=[1, 2, 3])),
            (SequenceOf[float], b'{"items":[1.5,2.5,3.5]}', SequenceOf[float](items=[1.5, 2.5, 3.5])),
            (SequenceOf[bool], b'{"items":[true,false,true]}', SequenceOf[bool](items=[True, False, True])),
            (
                SequenceOf[decimal.Decimal],
                b'{"items":["1.23","4.56"]}',
                SequenceOf[decimal.Decimal](items=[decimal.Decimal("1.23"), decimal.Decimal("4.56")]),
            ),
            (
                SequenceOf[uuid.UUID],
                b'{"items":["12345678-1234-5678-1234-567812345678","87654321-4321-8765-4321-876543218765"]}',
                SequenceOf[uuid.UUID](
                    items=[
                        uuid.UUID("12345678-1234-5678-1234-567812345678"),
                        uuid.UUID("87654321-4321-8765-4321-876543218765"),
                    ]
                ),
            ),
            (
                SequenceOf[datetime.datetime],
                b'{"items":["2024-01-15T10:30:00+00:00"]}',
                SequenceOf[datetime.datetime](items=[datetime.datetime(2024, 1, 15, 10, 30, 0, tzinfo=datetime.UTC)]),
            ),
            (
                SequenceOf[datetime.date],
                b'{"items":["2024-01-15"]}',
                SequenceOf[datetime.date](items=[datetime.date(2024, 1, 15)]),
            ),
            (
                SequenceOf[datetime.time],
                b'{"items":["10:30:00"]}',
                SequenceOf[datetime.time](items=[datetime.time(10, 30, 0)]),
            ),
        ],
    )
    def test_value(self, impl: Serializer, schema_type: type, data: bytes, expected: object) -> None:
        result = impl.load(schema_type, data)
        assert result == expected

    @pytest.mark.parametrize(
        ("schema_type", "data", "expected"),
        [
            (
                SequenceOf[Status],
                b'{"items":["active","pending"]}',
                SequenceOf[Status](items=[Status.ACTIVE, Status.PENDING]),
            ),
            (SequenceOf[Priority], b'{"items":[1,3]}', SequenceOf[Priority](items=[Priority.LOW, Priority.HIGH])),
        ],
    )
    def test_enum(self, impl: Serializer, schema_type: type, data: bytes, expected: object) -> None:
        result = impl.load(schema_type, data)
        assert result == expected

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

    @pytest.mark.parametrize(
        ("data", "expected"),
        [
            (b"{}", OptionalSequenceOf[int](items=None)),
            (b'{"items":[1,2,3]}', OptionalSequenceOf[int](items=[1, 2, 3])),
        ],
    )
    def test_optional(self, impl: Serializer, data: bytes, expected: OptionalSequenceOf[int]) -> None:
        result = impl.load(OptionalSequenceOf[int], data)
        assert result == expected

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
            impl.load(WithSequenceTwoValidators, data)
        assert exc.value.messages == error_messages

    def test_item_wrong_type(self, impl: Serializer) -> None:
        data = b'{"items":[1,"not_int",3]}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(SequenceOf[int], data)
        assert exc.value.messages == {"items": {1: ["Not a valid integer."]}}

    @pytest.mark.parametrize(
        ("data", "error_messages"),
        [
            pytest.param(b'{"items":"not_a_sequence"}', {"items": ["Not a valid list."]}, id="string"),
            pytest.param(b'{"items":{"key":1}}', {"items": ["Not a valid list."]}, id="object"),
        ],
    )
    def test_wrong_type(self, impl: Serializer, data: bytes, error_messages: dict[str, list[str]]) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(SequenceOf[int], data)
        assert exc.value.messages == error_messages

    def test_missing_required(self, impl: Serializer) -> None:
        data = b"{}"
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(SequenceOf[int], data)
        assert exc.value.messages == {"items": ["Missing data for required field."]}

    @pytest.mark.parametrize(
        ("data", "schema_type", "error_messages"),
        [
            pytest.param(b"{}", WithSequenceRequiredError, {"items": ["Custom required message"]}, id="required"),
            pytest.param(b'{"items":null}', WithSequenceNoneError, {"items": ["Custom none message"]}, id="none"),
            pytest.param(
                b'{"items":"not_a_sequence"}',
                WithSequenceInvalidError,
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
        [(b"{}", WithSequenceMissing()), (b'{"items":[1,2,3]}', WithSequenceMissing(items=[1, 2, 3]))],
    )
    def test_missing(self, impl: Serializer, data: bytes, expected: WithSequenceMissing) -> None:
        result = impl.load(WithSequenceMissing, data)
        assert result == expected
