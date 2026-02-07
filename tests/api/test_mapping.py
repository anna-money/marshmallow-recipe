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
    MappingOf,
    OptionalMappingOf,
    Priority,
    Serializer,
    Status,
    WithMappingInvalidError,
    WithMappingMissing,
    WithMappingNoneError,
    WithMappingRequiredError,
    WithMappingTwoValidators,
    WithMappingValidation,
)


class TestMappingDump:
    @pytest.mark.parametrize(
        ("schema_type", "obj", "expected"),
        [
            (MappingOf[str, str], MappingOf[str, str](data={"a": "x", "b": "y"}), b'{"data":{"a":"x","b":"y"}}'),
            (MappingOf[str, int], MappingOf[str, int](data={"a": 1, "b": 2}), b'{"data":{"a":1,"b":2}}'),
            (MappingOf[str, float], MappingOf[str, float](data={"a": 1.5, "b": 2.5}), b'{"data":{"a":1.5,"b":2.5}}'),
            (
                MappingOf[str, bool],
                MappingOf[str, bool](data={"a": True, "b": False}),
                b'{"data":{"a":true,"b":false}}',
            ),
            (
                MappingOf[str, decimal.Decimal],
                MappingOf[str, decimal.Decimal](data={"a": decimal.Decimal("1.23"), "b": decimal.Decimal("4.56")}),
                b'{"data":{"a":"1.23","b":"4.56"}}',
            ),
            (
                MappingOf[str, uuid.UUID],
                MappingOf[str, uuid.UUID](data={"a": uuid.UUID("12345678-1234-5678-1234-567812345678")}),
                b'{"data":{"a":"12345678-1234-5678-1234-567812345678"}}',
            ),
            (
                MappingOf[str, datetime.datetime],
                MappingOf[str, datetime.datetime](
                    data={"a": datetime.datetime(2024, 1, 15, 10, 30, 0, tzinfo=datetime.UTC)}
                ),
                b'{"data":{"a":"2024-01-15T10:30:00+00:00"}}',
            ),
            (
                MappingOf[str, datetime.date],
                MappingOf[str, datetime.date](data={"a": datetime.date(2024, 1, 15)}),
                b'{"data":{"a":"2024-01-15"}}',
            ),
            (
                MappingOf[str, datetime.time],
                MappingOf[str, datetime.time](data={"a": datetime.time(10, 30, 0)}),
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
                MappingOf[str, Status],
                MappingOf[str, Status](data={"a": Status.ACTIVE, "b": Status.PENDING}),
                b'{"data":{"a":"active","b":"pending"}}',
            ),
            (
                MappingOf[str, Priority],
                MappingOf[str, Priority](data={"a": Priority.LOW, "b": Priority.HIGH}),
                b'{"data":{"a":1,"b":3}}',
            ),
        ],
    )
    def test_enum(self, impl: Serializer, schema_type: type, obj: object, expected: bytes) -> None:
        result = impl.dump(schema_type, obj)
        assert result == expected

    def test_dataclass(self, impl: Serializer) -> None:
        addr = Address(street="Main St", city="NYC", zip_code="10001")
        obj = MappingOf[str, Address](data={"home": addr})
        result = impl.dump(MappingOf[str, Address], obj)
        assert json.loads(result) == {"data": {"home": {"street": "Main St", "city": "NYC", "zip_code": "10001"}}}

    def test_list_value(self, impl: Serializer) -> None:
        obj = MappingOf[str, list[int]](data={"a": [1, 2], "b": [3, 4]})
        result = impl.dump(MappingOf[str, list[int]], obj)
        assert result == b'{"data":{"a":[1,2],"b":[3,4]}}'

    def test_nested_dict(self, impl: Serializer) -> None:
        obj = MappingOf[str, dict[str, int]](data={"a": {"x": 1}, "b": {"y": 2}})
        result = impl.dump(MappingOf[str, dict[str, int]], obj)
        assert result == b'{"data":{"a":{"x":1},"b":{"y":2}}}'

    def test_sequence_value(self, impl: Serializer) -> None:
        obj = MappingOf[str, Sequence[int]](data={"a": [1, 2], "b": [3, 4]})
        result = impl.dump(MappingOf[str, Sequence[int]], obj)
        assert result == b'{"data":{"a":[1,2],"b":[3,4]}}'

    def test_nested_mapping(self, impl: Serializer) -> None:
        obj = MappingOf[str, Mapping[str, int]](data={"a": {"x": 1}, "b": {"y": 2}})
        result = impl.dump(MappingOf[str, Mapping[str, int]], obj)
        assert result == b'{"data":{"a":{"x":1},"b":{"y":2}}}'

    def test_optional_value(self, impl: Serializer) -> None:
        obj = MappingOf[str, int | None](data={"a": 1, "b": None})
        result = impl.dump(MappingOf[str, int | None], obj)
        assert result == b'{"data":{"a":1,"b":null}}'

    def test_any_value(self, impl: Serializer) -> None:
        obj = MappingOf[str, Any](data={"a": 1, "b": "two", "c": None})
        result = impl.dump(MappingOf[str, Any], obj)
        assert result == b'{"data":{"a":1,"b":"two","c":null}}'

    def test_empty(self, impl: Serializer) -> None:
        obj = MappingOf[str, int](data={})
        result = impl.dump(MappingOf[str, int], obj)
        assert result == b'{"data":{}}'

    @pytest.mark.parametrize(
        ("obj", "expected"),
        [
            (OptionalMappingOf[str, int](data=None), b"{}"),
            (OptionalMappingOf[str, int](data={"a": 1}), b'{"data":{"a":1}}'),
        ],
    )
    def test_optional(self, impl: Serializer, obj: OptionalMappingOf[str, int], expected: bytes) -> None:
        result = impl.dump(OptionalMappingOf[str, int], obj)
        assert result == expected

    @pytest.mark.parametrize(
        ("obj", "none_value_handling", "expected"),
        [
            (OptionalMappingOf[str, int](data=None), mr.NoneValueHandling.IGNORE, b"{}"),
            (OptionalMappingOf[str, int](data=None), mr.NoneValueHandling.INCLUDE, b'{"data":null}'),
            (OptionalMappingOf[str, int](data={"a": 1}), mr.NoneValueHandling.INCLUDE, b'{"data":{"a":1}}'),
        ],
    )
    def test_none_handling(
        self,
        impl: Serializer,
        obj: OptionalMappingOf[str, int],
        none_value_handling: mr.NoneValueHandling,
        expected: bytes,
    ) -> None:
        result = impl.dump(OptionalMappingOf[str, int], obj, none_value_handling=none_value_handling)
        assert result == expected

    @pytest.mark.parametrize(
        ("obj", "expected"),
        [(WithMappingMissing(), b"{}"), (WithMappingMissing(data={"a": 1, "b": 2}), b'{"data":{"a":1,"b":2}}')],
    )
    def test_missing(self, impl: Serializer, obj: WithMappingMissing, expected: bytes) -> None:
        result = impl.dump(WithMappingMissing, obj)
        assert result == expected

    def test_unsubscripted(self, impl: Serializer) -> None:
        obj = CollectionHolder[Mapping](items={"a": 1, "b": "va"})
        result = impl.dump(CollectionHolder[Mapping], obj)
        assert result == b'{"items":{"a":1,"b":"va"}}'


class TestMappingLoad:
    @pytest.mark.parametrize(
        ("schema_type", "data", "expected"),
        [
            (MappingOf[str, str], b'{"data":{"a":"x","b":"y"}}', MappingOf[str, str](data={"a": "x", "b": "y"})),
            (MappingOf[str, int], b'{"data":{"a":1,"b":2}}', MappingOf[str, int](data={"a": 1, "b": 2})),
            (MappingOf[str, float], b'{"data":{"a":1.5,"b":2.5}}', MappingOf[str, float](data={"a": 1.5, "b": 2.5})),
            (
                MappingOf[str, bool],
                b'{"data":{"a":true,"b":false}}',
                MappingOf[str, bool](data={"a": True, "b": False}),
            ),
            (
                MappingOf[str, decimal.Decimal],
                b'{"data":{"a":"1.23","b":"4.56"}}',
                MappingOf[str, decimal.Decimal](data={"a": decimal.Decimal("1.23"), "b": decimal.Decimal("4.56")}),
            ),
            (
                MappingOf[str, uuid.UUID],
                b'{"data":{"a":"12345678-1234-5678-1234-567812345678"}}',
                MappingOf[str, uuid.UUID](data={"a": uuid.UUID("12345678-1234-5678-1234-567812345678")}),
            ),
            (
                MappingOf[str, datetime.datetime],
                b'{"data":{"a":"2024-01-15T10:30:00+00:00"}}',
                MappingOf[str, datetime.datetime](
                    data={"a": datetime.datetime(2024, 1, 15, 10, 30, 0, tzinfo=datetime.UTC)}
                ),
            ),
            (
                MappingOf[str, datetime.date],
                b'{"data":{"a":"2024-01-15"}}',
                MappingOf[str, datetime.date](data={"a": datetime.date(2024, 1, 15)}),
            ),
            (
                MappingOf[str, datetime.time],
                b'{"data":{"a":"10:30:00"}}',
                MappingOf[str, datetime.time](data={"a": datetime.time(10, 30, 0)}),
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
                MappingOf[str, Status],
                b'{"data":{"a":"active","b":"pending"}}',
                MappingOf[str, Status](data={"a": Status.ACTIVE, "b": Status.PENDING}),
            ),
            (
                MappingOf[str, Priority],
                b'{"data":{"a":1,"b":3}}',
                MappingOf[str, Priority](data={"a": Priority.LOW, "b": Priority.HIGH}),
            ),
        ],
    )
    def test_enum(self, impl: Serializer, schema_type: type, data: bytes, expected: object) -> None:
        result = impl.load(schema_type, data)
        assert result == expected

    def test_dataclass(self, impl: Serializer) -> None:
        addr = Address(street="Main St", city="NYC", zip_code="10001")
        data = b'{"data":{"home":{"street":"Main St","city":"NYC","zip_code":"10001"}}}'
        result = impl.load(MappingOf[str, Address], data)
        assert result == MappingOf[str, Address](data={"home": addr})

    def test_list_value(self, impl: Serializer) -> None:
        data = b'{"data":{"a":[1,2],"b":[3,4]}}'
        result = impl.load(MappingOf[str, list[int]], data)
        assert result == MappingOf[str, list[int]](data={"a": [1, 2], "b": [3, 4]})

    def test_nested_dict(self, impl: Serializer) -> None:
        data = b'{"data":{"a":{"x":1},"b":{"y":2}}}'
        result = impl.load(MappingOf[str, dict[str, int]], data)
        assert result == MappingOf[str, dict[str, int]](data={"a": {"x": 1}, "b": {"y": 2}})

    def test_sequence_value(self, impl: Serializer) -> None:
        data = b'{"data":{"a":[1,2],"b":[3,4]}}'
        result = impl.load(MappingOf[str, Sequence[int]], data)
        assert result == MappingOf[str, Sequence[int]](data={"a": [1, 2], "b": [3, 4]})

    def test_nested_mapping(self, impl: Serializer) -> None:
        data = b'{"data":{"a":{"x":1},"b":{"y":2}}}'
        result = impl.load(MappingOf[str, Mapping[str, int]], data)
        assert result == MappingOf[str, Mapping[str, int]](data={"a": {"x": 1}, "b": {"y": 2}})

    def test_optional_value(self, impl: Serializer) -> None:
        data = b'{"data":{"a":1,"b":null}}'
        result = impl.load(MappingOf[str, int | None], data)
        assert result == MappingOf[str, int | None](data={"a": 1, "b": None})

    def test_any_value(self, impl: Serializer) -> None:
        data = b'{"data":{"a":1,"b":"two","c":null}}'
        result = impl.load(MappingOf[str, Any], data)
        assert result == MappingOf[str, Any](data={"a": 1, "b": "two", "c": None})

    def test_empty(self, impl: Serializer) -> None:
        data = b'{"data":{}}'
        result = impl.load(MappingOf[str, int], data)
        assert result == MappingOf[str, int](data={})

    @pytest.mark.parametrize(
        ("data", "expected"),
        [
            (b"{}", OptionalMappingOf[str, int](data=None)),
            (b'{"data":{"a":1}}', OptionalMappingOf[str, int](data={"a": 1})),
        ],
    )
    def test_optional(self, impl: Serializer, data: bytes, expected: OptionalMappingOf[str, int]) -> None:
        result = impl.load(OptionalMappingOf[str, int], data)
        assert result == expected

    def test_validation_pass(self, impl: Serializer) -> None:
        data = b'{"data":{"a":1}}'
        result = impl.load(WithMappingValidation, data)
        assert result == WithMappingValidation(data={"a": 1})

    def test_validation_fail(self, impl: Serializer) -> None:
        data = b'{"data":{}}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithMappingValidation, data)
        assert exc.value.messages == {"data": ["Invalid value."]}

    def test_two_validators_pass(self, impl: Serializer) -> None:
        data = b'{"data":{"a":1,"b":2,"c":3}}'
        result = impl.load(WithMappingTwoValidators, data)
        assert result == WithMappingTwoValidators(data={"a": 1, "b": 2, "c": 3})

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
            impl.load(WithMappingTwoValidators, data)
        assert exc.value.messages == {"data": ["Invalid value."]}

    def test_value_wrong_type(self, impl: Serializer) -> None:
        data = b'{"data":{"a":"not_int"}}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(MappingOf[str, int], data)
        assert exc.value.messages == {"data": {"a": {"value": ["Not a valid integer."]}}}

    @pytest.mark.parametrize(
        ("data", "error_messages"),
        [
            pytest.param(b'{"data":"not_a_mapping"}', {"data": ["Not a valid dict."]}, id="string"),
            pytest.param(b'{"data":[1,2,3]}', {"data": ["Not a valid dict."]}, id="list"),
        ],
    )
    def test_wrong_type(self, impl: Serializer, data: bytes, error_messages: dict[str, list[str]]) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(MappingOf[str, int], data)
        assert exc.value.messages == error_messages

    def test_missing_required(self, impl: Serializer) -> None:
        data = b"{}"
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(MappingOf[str, int], data)
        assert exc.value.messages == {"data": ["Missing data for required field."]}

    @pytest.mark.parametrize(
        ("data", "schema_type", "error_messages"),
        [
            pytest.param(b"{}", WithMappingRequiredError, {"data": ["Custom required message"]}, id="required"),
            pytest.param(b'{"data":null}', WithMappingNoneError, {"data": ["Custom none message"]}, id="none"),
            pytest.param(
                b'{"data":"not_a_mapping"}', WithMappingInvalidError, {"data": ["Custom invalid message"]}, id="invalid"
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
        [(b"{}", WithMappingMissing()), (b'{"data":{"a":1,"b":2}}', WithMappingMissing(data={"a": 1, "b": 2}))],
    )
    def test_missing(self, impl: Serializer, data: bytes, expected: WithMappingMissing) -> None:
        result = impl.load(WithMappingMissing, data)
        assert result == expected
