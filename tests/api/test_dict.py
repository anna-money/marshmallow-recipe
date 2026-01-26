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
    @pytest.mark.parametrize(
        ("schema_type", "obj", "expected"),
        [
            (DictOf[str, str], DictOf[str, str](data={"a": "x", "b": "y"}), b'{"data":{"a":"x","b":"y"}}'),
            (DictOf[str, int], DictOf[str, int](data={"a": 1, "b": 2}), b'{"data":{"a":1,"b":2}}'),
            (DictOf[str, float], DictOf[str, float](data={"a": 1.5, "b": 2.5}), b'{"data":{"a":1.5,"b":2.5}}'),
            (DictOf[str, bool], DictOf[str, bool](data={"a": True, "b": False}), b'{"data":{"a":true,"b":false}}'),
            (
                DictOf[str, decimal.Decimal],
                DictOf[str, decimal.Decimal](data={"a": decimal.Decimal("1.23"), "b": decimal.Decimal("4.56")}),
                b'{"data":{"a":"1.23","b":"4.56"}}',
            ),
            (
                DictOf[str, uuid.UUID],
                DictOf[str, uuid.UUID](data={"a": uuid.UUID("12345678-1234-5678-1234-567812345678")}),
                b'{"data":{"a":"12345678-1234-5678-1234-567812345678"}}',
            ),
            (
                DictOf[str, datetime.datetime],
                DictOf[str, datetime.datetime](
                    data={"a": datetime.datetime(2024, 1, 15, 10, 30, 0, tzinfo=datetime.UTC)}
                ),
                b'{"data":{"a":"2024-01-15T10:30:00+00:00"}}',
            ),
            (
                DictOf[str, datetime.date],
                DictOf[str, datetime.date](data={"a": datetime.date(2024, 1, 15)}),
                b'{"data":{"a":"2024-01-15"}}',
            ),
            (
                DictOf[str, datetime.time],
                DictOf[str, datetime.time](data={"a": datetime.time(10, 30, 0)}),
                b'{"data":{"a":"10:30:00"}}',
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
                DictOf[str, Status],
                DictOf[str, Status](data={"a": Status.ACTIVE, "b": Status.PENDING}),
                b'{"data":{"a":"active","b":"pending"}}',
            ),
            (
                DictOf[str, Priority],
                DictOf[str, Priority](data={"a": Priority.LOW, "b": Priority.HIGH}),
                b'{"data":{"a":1,"b":3}}',
            ),
        ],
    )
    def test_enum(self, impl: Serializer, schema_type: type, obj: object, expected: bytes) -> None:
        result = impl.dump(schema_type, obj)
        assert result == expected

    def test_dataclass(self, impl: Serializer) -> None:
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

    @pytest.mark.parametrize(
        ("obj", "expected"),
        [(OptionalDictOf[str, int](data=None), b"{}"), (OptionalDictOf[str, int](data={"a": 1}), b'{"data":{"a":1}}')],
    )
    def test_optional(self, impl: Serializer, obj: OptionalDictOf[str, int], expected: bytes) -> None:
        result = impl.dump(OptionalDictOf[str, int], obj)
        assert result == expected

    @pytest.mark.parametrize(
        ("obj", "none_value_handling", "expected"),
        [
            (OptionalDictOf[str, int](data=None), mr.NoneValueHandling.IGNORE, b"{}"),
            (OptionalDictOf[str, int](data=None), mr.NoneValueHandling.INCLUDE, b'{"data":null}'),
            (OptionalDictOf[str, int](data={"a": 1}), mr.NoneValueHandling.INCLUDE, b'{"data":{"a":1}}'),
        ],
    )
    def test_none_handling(
        self,
        impl: Serializer,
        obj: OptionalDictOf[str, int],
        none_value_handling: mr.NoneValueHandling,
        expected: bytes,
    ) -> None:
        result = impl.dump(OptionalDictOf[str, int], obj, none_value_handling=none_value_handling)
        assert result == expected

    @pytest.mark.parametrize(
        ("obj", "expected"),
        [(WithDictMissing(), b"{}"), (WithDictMissing(data={"a": 1, "b": 2}), b'{"data":{"a":1,"b":2}}')],
    )
    def test_missing(self, impl: Serializer, obj: WithDictMissing, expected: bytes) -> None:
        result = impl.dump(WithDictMissing, obj)
        assert result == expected

    def test_unsubscripted(self, impl: Serializer) -> None:
        obj = CollectionHolder[dict](items={"a": 1, "b": "va"})
        result = impl.dump(CollectionHolder[dict], obj)
        assert result == b'{"items":{"a":1,"b":"va"}}'

    @pytest.mark.parametrize(
        "obj",
        [
            pytest.param(DictOf[str, int](**{"data": "not a dict"}), id="string"),  # type: ignore[arg-type]
            pytest.param(DictOf[str, int](**{"data": [1, 2, 3]}), id="list"),  # type: ignore[arg-type]
            pytest.param(DictOf[str, int](**{"data": 123}), id="int"),  # type: ignore[arg-type]
        ],
    )
    def test_invalid_type(self, impl: Serializer, obj: DictOf[str, int]) -> None:
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(DictOf[str, int], obj)


class TestDictLoad:
    @pytest.mark.parametrize(
        ("schema_type", "data", "expected"),
        [
            (DictOf[str, str], b'{"data":{"a":"x","b":"y"}}', DictOf[str, str](data={"a": "x", "b": "y"})),
            (DictOf[str, int], b'{"data":{"a":1,"b":2}}', DictOf[str, int](data={"a": 1, "b": 2})),
            (DictOf[str, float], b'{"data":{"a":1.5,"b":2.5}}', DictOf[str, float](data={"a": 1.5, "b": 2.5})),
            (DictOf[str, bool], b'{"data":{"a":true,"b":false}}', DictOf[str, bool](data={"a": True, "b": False})),
            (
                DictOf[str, decimal.Decimal],
                b'{"data":{"a":"1.23","b":"4.56"}}',
                DictOf[str, decimal.Decimal](data={"a": decimal.Decimal("1.23"), "b": decimal.Decimal("4.56")}),
            ),
            (
                DictOf[str, uuid.UUID],
                b'{"data":{"a":"12345678-1234-5678-1234-567812345678"}}',
                DictOf[str, uuid.UUID](data={"a": uuid.UUID("12345678-1234-5678-1234-567812345678")}),
            ),
            (
                DictOf[str, datetime.datetime],
                b'{"data":{"a":"2024-01-15T10:30:00+00:00"}}',
                DictOf[str, datetime.datetime](
                    data={"a": datetime.datetime(2024, 1, 15, 10, 30, 0, tzinfo=datetime.UTC)}
                ),
            ),
            (
                DictOf[str, datetime.date],
                b'{"data":{"a":"2024-01-15"}}',
                DictOf[str, datetime.date](data={"a": datetime.date(2024, 1, 15)}),
            ),
            (
                DictOf[str, datetime.time],
                b'{"data":{"a":"10:30:00"}}',
                DictOf[str, datetime.time](data={"a": datetime.time(10, 30, 0)}),
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
                DictOf[str, Status],
                b'{"data":{"a":"active","b":"pending"}}',
                DictOf[str, Status](data={"a": Status.ACTIVE, "b": Status.PENDING}),
            ),
            (
                DictOf[str, Priority],
                b'{"data":{"a":1,"b":3}}',
                DictOf[str, Priority](data={"a": Priority.LOW, "b": Priority.HIGH}),
            ),
        ],
    )
    def test_enum(self, impl: Serializer, schema_type: type, data: bytes, expected: object) -> None:
        result = impl.load(schema_type, data)
        assert result == expected

    def test_dataclass(self, impl: Serializer) -> None:
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

    @pytest.mark.parametrize(
        ("data", "expected"),
        [(b"{}", OptionalDictOf[str, int](data=None)), (b'{"data":{"a":1}}', OptionalDictOf[str, int](data={"a": 1}))],
    )
    def test_optional(self, impl: Serializer, data: bytes, expected: OptionalDictOf[str, int]) -> None:
        result = impl.load(OptionalDictOf[str, int], data)
        assert result == expected

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

    @pytest.mark.parametrize(
        "data",
        [
            pytest.param(b'{"data":{}}', id="first_fails"),
            pytest.param(
                b'{"data":{' + b", ".join([f'"{chr(97+i)}": {i}'.encode() for i in range(11)]) + b"}}",
                id="second_fails",
            ),
        ],
    )
    def test_two_validators_fail(self, impl: Serializer, data: bytes) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithDictTwoValidators, data)
        assert exc.value.messages == {"data": ["Invalid value."]}

    def test_value_wrong_type(self, impl: Serializer) -> None:
        data = b'{"data":{"a":"not_int"}}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(DictOf[str, int], data)
        assert exc.value.messages == {"data": {"a": {"value": ["Not a valid integer."]}}}

    @pytest.mark.parametrize(
        ("data", "error_messages"),
        [
            pytest.param(b'{"data":"not_a_dict"}', {"data": ["Not a valid dict."]}, id="string"),
            pytest.param(b'{"data":[1,2,3]}', {"data": ["Not a valid dict."]}, id="list"),
        ],
    )
    def test_wrong_type(self, impl: Serializer, data: bytes, error_messages: dict[str, list[str]]) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(DictOf[str, int], data)
        assert exc.value.messages == error_messages

    def test_missing_required(self, impl: Serializer) -> None:
        data = b"{}"
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(DictOf[str, int], data)
        assert exc.value.messages == {"data": ["Missing data for required field."]}

    @pytest.mark.parametrize(
        ("data", "schema_type", "error_messages"),
        [
            pytest.param(b"{}", WithDictRequiredError, {"data": ["Custom required message"]}, id="required"),
            pytest.param(b'{"data":null}', WithDictNoneError, {"data": ["Custom none message"]}, id="none"),
            pytest.param(
                b'{"data":"not_a_dict"}', WithDictInvalidError, {"data": ["Custom invalid message"]}, id="invalid"
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
        [(b"{}", WithDictMissing()), (b'{"data":{"a":1,"b":2}}', WithDictMissing(data={"a": 1, "b": 2}))],
    )
    def test_missing(self, impl: Serializer, data: bytes, expected: WithDictMissing) -> None:
        result = impl.load(WithDictMissing, data)
        assert result == expected
