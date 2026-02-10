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
    OptionalTupleOf,
    Priority,
    Serializer,
    Status,
    TupleOf,
    WithTupleInvalidError,
    WithTupleItemTwoValidators,
    WithTupleItemValidation,
    WithTupleMissing,
    WithTupleNoneError,
    WithTupleRequiredError,
)


class TestTupleDump:
    @pytest.mark.parametrize(
        "schema_type,obj,expected",
        [
            (TupleOf[str], TupleOf[str](items=("a", "b", "c")), b'{"items":["a","b","c"]}'),
            (TupleOf[int], TupleOf[int](items=(1, 2, 3)), b'{"items":[1,2,3]}'),
            (TupleOf[float], TupleOf[float](items=(1.5, 2.5, 3.5)), b'{"items":[1.5,2.5,3.5]}'),
            (TupleOf[bool], TupleOf[bool](items=(True, False, True)), b'{"items":[true,false,true]}'),
            (
                TupleOf[decimal.Decimal],
                TupleOf[decimal.Decimal](items=(decimal.Decimal("1.23"), decimal.Decimal("4.56"))),
                b'{"items":["1.23","4.56"]}',
            ),
            (
                TupleOf[uuid.UUID],
                TupleOf[uuid.UUID](
                    items=(
                        uuid.UUID("12345678-1234-5678-1234-567812345678"),
                        uuid.UUID("87654321-4321-8765-4321-876543218765"),
                    )
                ),
                b'{"items":["12345678-1234-5678-1234-567812345678","87654321-4321-8765-4321-876543218765"]}',
            ),
            (
                TupleOf[datetime.datetime],
                TupleOf[datetime.datetime](items=(datetime.datetime(2024, 1, 15, 10, 30, 0, tzinfo=datetime.UTC),)),
                b'{"items":["2024-01-15T10:30:00+00:00"]}',
            ),
            (
                TupleOf[datetime.date],
                TupleOf[datetime.date](items=(datetime.date(2024, 1, 15),)),
                b'{"items":["2024-01-15"]}',
            ),
            (
                TupleOf[datetime.time],
                TupleOf[datetime.time](items=(datetime.time(10, 30, 0),)),
                b'{"items":["10:30:00"]}',
            ),
            (
                TupleOf[Status],
                TupleOf[Status](items=(Status.ACTIVE, Status.PENDING)),
                b'{"items":["active","pending"]}',
            ),
            (TupleOf[Priority], TupleOf[Priority](items=(Priority.LOW, Priority.HIGH)), b'{"items":[1,3]}'),
            (TupleOf[list[int]], TupleOf[list[int]](items=([1, 2], [3, 4])), b'{"items":[[1,2],[3,4]]}'),
            (
                TupleOf[dict[str, int]],
                TupleOf[dict[str, int]](items=({"a": 1}, {"b": 2})),
                b'{"items":[{"a":1},{"b":2}]}',
            ),
            (TupleOf[Sequence[int]], TupleOf[Sequence[int]](items=([1, 2], [3, 4])), b'{"items":[[1,2],[3,4]]}'),
            (
                TupleOf[Mapping[str, int]],
                TupleOf[Mapping[str, int]](items=({"a": 1}, {"b": 2})),
                b'{"items":[{"a":1},{"b":2}]}',
            ),
            (TupleOf[int | None], TupleOf[int | None](items=(1, None, 3)), b'{"items":[1,null,3]}'),
            (TupleOf[Any], TupleOf[Any](items=(1, "two", 3.0, True, None)), b'{"items":[1,"two",3.0,true,null]}'),
            (TupleOf[int], TupleOf[int](items=()), b'{"items":[]}'),
            (CollectionHolder[tuple], CollectionHolder[tuple](items=(99, "xx")), b'{"items":[99,"xx"]}'),
        ],
    )
    def test_dump_value(self, impl: Serializer, schema_type: type, obj: object, expected: bytes) -> None:
        result = impl.dump(schema_type, obj)
        assert result == expected

    def test_dataclass(self, impl: Serializer) -> None:
        obj = TupleOf[Address](items=(Address(street="Main St", city="NYC", zip_code="10001"),))
        result = impl.dump(TupleOf[Address], obj)
        assert json.loads(result) == {"items": [{"street": "Main St", "city": "NYC", "zip_code": "10001"}]}

    @pytest.mark.parametrize(
        "obj,expected",
        [(OptionalTupleOf[int](items=None), b"{}"), (OptionalTupleOf[int](items=(1, 2, 3)), b'{"items":[1,2,3]}')],
    )
    def test_optional(self, impl: Serializer, obj: OptionalTupleOf[int], expected: bytes) -> None:
        result = impl.dump(OptionalTupleOf[int], obj)
        assert result == expected

    @pytest.mark.parametrize(
        "none_value_handling,expected",
        [(None, b"{}"), (mr.NoneValueHandling.IGNORE, b"{}"), (mr.NoneValueHandling.INCLUDE, b'{"items":null}')],
    )
    def test_none_handling(
        self, impl: Serializer, none_value_handling: mr.NoneValueHandling | None, expected: bytes
    ) -> None:
        obj = OptionalTupleOf[int](items=None)
        result = impl.dump(OptionalTupleOf[int], obj, none_value_handling=none_value_handling)
        assert result == expected

    def test_none_handling_include_with_value(self, impl: Serializer) -> None:
        obj = OptionalTupleOf[int](items=(1, 2, 3))
        result = impl.dump(OptionalTupleOf[int], obj, none_value_handling=mr.NoneValueHandling.INCLUDE)
        assert result == b'{"items":[1,2,3]}'

    @pytest.mark.parametrize(
        "obj,expected", [(WithTupleMissing(), b"{}"), (WithTupleMissing(items=(1, 2, 3)), b'{"items":[1,2,3]}')]
    )
    def test_missing(self, impl: Serializer, obj: WithTupleMissing, expected: bytes) -> None:
        result = impl.dump(WithTupleMissing, obj)
        assert result == expected

    @pytest.mark.parametrize(
        "value",
        [
            pytest.param("not a tuple", id="string"),
            pytest.param([1, 2, 3], id="list"),
            pytest.param(123, id="int"),
            pytest.param({"a": 1}, id="dict"),
        ],
    )
    def test_invalid_type(self, impl: Serializer, value: object) -> None:
        obj = TupleOf[int](**{"items": value})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.dump(TupleOf[int], obj)
        if impl.supports_proper_validation_errors_on_dump:
            assert exc.value.messages == {"items": ["Not a valid tuple."]}

    def test_custom_invalid_error(self, impl: Serializer) -> None:
        obj = WithTupleInvalidError(**{"items": "not a tuple"})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.dump(WithTupleInvalidError, obj)
        if impl.supports_proper_validation_errors_on_dump:
            assert exc.value.messages == {"items": ["Custom invalid message"]}


class TestTupleLoad:
    @pytest.mark.parametrize(
        "schema_type,data,expected",
        [
            (TupleOf[str], b'{"items":["a","b","c"]}', TupleOf[str](items=("a", "b", "c"))),
            (TupleOf[int], b'{"items":[1,2,3]}', TupleOf[int](items=(1, 2, 3))),
            (TupleOf[float], b'{"items":[1.5,2.5,3.5]}', TupleOf[float](items=(1.5, 2.5, 3.5))),
            (TupleOf[bool], b'{"items":[true,false,true]}', TupleOf[bool](items=(True, False, True))),
            (
                TupleOf[decimal.Decimal],
                b'{"items":["1.23","4.56"]}',
                TupleOf[decimal.Decimal](items=(decimal.Decimal("1.23"), decimal.Decimal("4.56"))),
            ),
            (
                TupleOf[uuid.UUID],
                b'{"items":["12345678-1234-5678-1234-567812345678","87654321-4321-8765-4321-876543218765"]}',
                TupleOf[uuid.UUID](
                    items=(
                        uuid.UUID("12345678-1234-5678-1234-567812345678"),
                        uuid.UUID("87654321-4321-8765-4321-876543218765"),
                    )
                ),
            ),
            (
                TupleOf[datetime.datetime],
                b'{"items":["2024-01-15T10:30:00+00:00"]}',
                TupleOf[datetime.datetime](items=(datetime.datetime(2024, 1, 15, 10, 30, 0, tzinfo=datetime.UTC),)),
            ),
            (
                TupleOf[datetime.date],
                b'{"items":["2024-01-15"]}',
                TupleOf[datetime.date](items=(datetime.date(2024, 1, 15),)),
            ),
            (
                TupleOf[datetime.time],
                b'{"items":["10:30:00"]}',
                TupleOf[datetime.time](items=(datetime.time(10, 30, 0),)),
            ),
            (
                TupleOf[Status],
                b'{"items":["active","pending"]}',
                TupleOf[Status](items=(Status.ACTIVE, Status.PENDING)),
            ),
            (TupleOf[Priority], b'{"items":[1,3]}', TupleOf[Priority](items=(Priority.LOW, Priority.HIGH))),
            (
                TupleOf[Address],
                b'{"items":[{"street":"Main St","city":"NYC","zip_code":"10001"}]}',
                TupleOf[Address](items=(Address(street="Main St", city="NYC", zip_code="10001"),)),
            ),
            (TupleOf[list[int]], b'{"items":[[1,2],[3,4]]}', TupleOf[list[int]](items=([1, 2], [3, 4]))),
            (
                TupleOf[dict[str, int]],
                b'{"items":[{"a":1},{"b":2}]}',
                TupleOf[dict[str, int]](items=({"a": 1}, {"b": 2})),
            ),
            (TupleOf[Sequence[int]], b'{"items":[[1,2],[3,4]]}', TupleOf[Sequence[int]](items=([1, 2], [3, 4]))),
            (
                TupleOf[Mapping[str, int]],
                b'{"items":[{"a":1},{"b":2}]}',
                TupleOf[Mapping[str, int]](items=({"a": 1}, {"b": 2})),
            ),
            (TupleOf[int | None], b'{"items":[1,null,3]}', TupleOf[int | None](items=(1, None, 3))),
            (TupleOf[Any], b'{"items":[1,"two",3.0,true,null]}', TupleOf[Any](items=(1, "two", 3.0, True, None))),
            (TupleOf[int], b'{"items":[]}', TupleOf[int](items=())),
        ],
    )
    def test_load_value(self, impl: Serializer, schema_type: type, data: bytes, expected: object) -> None:
        result = impl.load(schema_type, data)
        assert result == expected

    @pytest.mark.parametrize(
        "data,expected",
        [(b"{}", OptionalTupleOf[int](items=None)), (b'{"items":[1,2,3]}', OptionalTupleOf[int](items=(1, 2, 3)))],
    )
    def test_optional(self, impl: Serializer, data: bytes, expected: OptionalTupleOf[int]) -> None:
        result = impl.load(OptionalTupleOf[int], data)
        assert result == expected

    def test_item_validation_pass(self, impl: Serializer) -> None:
        data = b'{"values":[1,2,3]}'
        result = impl.load(WithTupleItemValidation, data)
        assert result == WithTupleItemValidation(values=(1, 2, 3))

    def test_item_validation_fail(self, impl: Serializer) -> None:
        data = b'{"values":[1,0,3]}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithTupleItemValidation, data)
        assert exc.value.messages == {"values": {1: ["Invalid value."]}}

    def test_two_validators_pass(self, impl: Serializer) -> None:
        data = b'{"values":[1,50,99]}'
        result = impl.load(WithTupleItemTwoValidators, data)
        assert result == WithTupleItemTwoValidators(values=(1, 50, 99))

    @pytest.mark.parametrize(
        "data",
        [
            pytest.param(b'{"values":[1,0,50]}', id="first_fails"),
            pytest.param(b'{"values":[1,150,50]}', id="second_fails"),
        ],
    )
    def test_two_validators_fail(self, impl: Serializer, data: bytes) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithTupleItemTwoValidators, data)
        assert exc.value.messages == {"values": {1: ["Invalid value."]}}

    def test_item_wrong_type(self, impl: Serializer) -> None:
        data = b'{"items":[1,"not_int",3]}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(TupleOf[int], data)
        assert exc.value.messages == {"items": {1: ["Not a valid integer."]}}

    @pytest.mark.parametrize(
        "data",
        [pytest.param(b'{"items":"not_a_tuple"}', id="string"), pytest.param(b'{"items":{"key":1}}', id="object")],
    )
    def test_wrong_type(self, impl: Serializer, data: bytes) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(TupleOf[int], data)
        assert exc.value.messages == {"items": ["Not a valid tuple."]}

    def test_missing_required(self, impl: Serializer) -> None:
        data = b"{}"
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(TupleOf[int], data)
        assert exc.value.messages == {"items": ["Missing data for required field."]}

    @pytest.mark.parametrize(
        "data,schema_type,error_message",
        [
            pytest.param(b"{}", WithTupleRequiredError, "Custom required message", id="required"),
            pytest.param(b'{"items":null}', WithTupleNoneError, "Custom none message", id="none"),
            pytest.param(b'{"items":"not_a_tuple"}', WithTupleInvalidError, "Custom invalid message", id="invalid"),
        ],
    )
    def test_custom_error(self, impl: Serializer, data: bytes, schema_type: type, error_message: str) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(schema_type, data)
        assert exc.value.messages == {"items": [error_message]}

    @pytest.mark.parametrize(
        "data,expected", [(b"{}", WithTupleMissing()), (b'{"items":[1,2,3]}', WithTupleMissing(items=(1, 2, 3)))]
    )
    def test_missing(self, impl: Serializer, data: bytes, expected: WithTupleMissing) -> None:
        result = impl.load(WithTupleMissing, data)
        assert result == expected
