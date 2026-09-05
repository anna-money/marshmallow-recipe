import dataclasses
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
    WithAliasKey,
    WithAnnotatedIntKey,
    WithAsStringMetadataKey,
    WithAsStringMetadataValue,
    WithBoolLiteralKey,
    WithDictInvalidError,
    WithDictMissing,
    WithDictNoneError,
    WithDictRequiredError,
    WithDictTwoValidators,
    WithDictValidation,
    WithIntKeyGte,
    WithIntLiteralKey,
    WithNewTypeKey,
    WithStrKeyMinLength,
    WithStrLiteralKey,
    WithTimestampKey,
)

_WRAPPED_KEY_CASES = [
    pytest.param(WithAliasKey, {1: "x"}, b'{"data":{"1":"x"}}', id="type_alias"),
    pytest.param(WithNewTypeKey, {1: "x"}, b'{"data":{"1":"x"}}', id="new_type"),
    pytest.param(WithAnnotatedIntKey, {1: "x"}, b'{"data":{"1":"x"}}', id="annotated"),
    pytest.param(WithStrLiteralKey, {"a": "x"}, b'{"data":{"a":"x"}}', id="str_literal"),
    pytest.param(WithIntLiteralKey, {1: "x"}, b'{"data":{"1":"x"}}', id="int_literal"),
    pytest.param(WithBoolLiteralKey, {True: "x"}, b'{"data":{"true":"x"}}', id="bool_literal"),
]

_KEY_UUID = uuid.UUID("12345678-1234-5678-1234-567812345678")
_KEY_DATETIME = datetime.datetime(2024, 1, 15, 10, 30, 0, tzinfo=datetime.UTC)

_KEY_CASES = [
    pytest.param(DictOf[str, str], {"a": "x"}, b'{"data":{"a":"x"}}', id="str"),
    pytest.param(DictOf[int, str], {1: "x"}, b'{"data":{"1":"x"}}', id="int"),
    pytest.param(DictOf[float, str], {1.5: "x"}, b'{"data":{"1.5":"x"}}', id="float"),
    pytest.param(DictOf[bool, str], {True: "x", False: "y"}, b'{"data":{"true":"x","false":"y"}}', id="bool"),
    pytest.param(DictOf[decimal.Decimal, str], {decimal.Decimal("1.23"): "x"}, b'{"data":{"1.23":"x"}}', id="decimal"),
    pytest.param(DictOf[bytes, str], {b"hi": "x"}, b'{"data":{"aGk=":"x"}}', id="bytes"),
    pytest.param(
        DictOf[uuid.UUID, str], {_KEY_UUID: "x"}, b'{"data":{"12345678-1234-5678-1234-567812345678":"x"}}', id="uuid"
    ),
    pytest.param(
        DictOf[datetime.date, str], {datetime.date(2024, 1, 15): "x"}, b'{"data":{"2024-01-15":"x"}}', id="date"
    ),
    pytest.param(DictOf[datetime.time, str], {datetime.time(10, 30, 0): "x"}, b'{"data":{"10:30:00":"x"}}', id="time"),
    pytest.param(
        DictOf[datetime.datetime, str],
        {_KEY_DATETIME: "x"},
        b'{"data":{"2024-01-15T10:30:00+00:00":"x"}}',
        id="datetime",
    ),
    pytest.param(WithTimestampKey, {_KEY_DATETIME: "x"}, b'{"data":{"1705314600.0":"x"}}', id="datetime_timestamp"),
    pytest.param(DictOf[Status, str], {Status.ACTIVE: "x"}, b'{"data":{"active":"x"}}', id="str_enum"),
    pytest.param(DictOf[Priority, str], {Priority.LOW: "x"}, b'{"data":{"1":"x"}}', id="int_enum"),
]

_UNSUPPORTED_KEY_CASES = [
    pytest.param(Any, id="any"),
    pytest.param(Address, id="dataclass"),
    pytest.param(list[int], id="list"),
    pytest.param(tuple[int, ...], id="tuple"),
    pytest.param(frozenset[int], id="frozenset"),
    pytest.param(dict[str, int], id="dict"),
    pytest.param(int | str, id="union"),
    pytest.param(int | None, id="optional"),
]

_UNSUPPORTED_KEY_CONTAINERS = [pytest.param(dict, id="dict"), pytest.param(Mapping, id="mapping")]

_KEY_AND_VALUE_ERROR_CASES = [
    pytest.param(
        DictOf[int, int],
        {"not_int": "not_int"},
        b'{"data":{"not_int":"not_int"}}',
        {"data": {"not_int": {"key": ["Not a valid integer."], "value": ["Not a valid integer."]}}},
        id="scalar_value",
    ),
    pytest.param(
        DictOf[int, Address],
        {"not_int": Address(street=1, city="NYC", zip_code="10001")},  # type: ignore[arg-type]
        b'{"data":{"not_int":{"street":1,"city":"NYC","zip_code":"10001"}}}',
        {"data": {"not_int": {"key": ["Not a valid integer."], "value": {"street": ["Not a valid string."]}}}},
        id="dataclass_value",
    ),
]


_ROOT_ERROR_CASES = [
    pytest.param(dict[str, int], {"a": "x"}, b'{"a":"x"}', {"a": {"value": ["Not a valid integer."]}}, id="value"),
    pytest.param(
        dict[bool, int],
        {True: "x"},
        b'{"true":"x"}',
        {"true": {"value": ["Not a valid integer."]}},
        id="value_under_non_str_key",
    ),
    pytest.param(
        dict[int, int],
        {"a": "x"},
        b'{"a":"x"}',
        {"a": {"key": ["Not a valid integer."], "value": ["Not a valid integer."]}},
        id="key_and_value",
    ),
]


def _with_unsupported_key(container: Any, key_type: Any) -> type:
    return dataclasses.make_dataclass(
        "WithUnsupportedKey", [("data", container[key_type, str])], frozen=True, slots=True, kw_only=True
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
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.dump(DictOf[str, int], obj)
        if impl.supports_proper_validation_errors_on_dump:
            assert exc.value.messages == {"data": ["Not a valid dict."]}

    def test_custom_invalid_error(self, impl: Serializer) -> None:
        obj = WithDictInvalidError(**{"data": "not a dict"})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.dump(WithDictInvalidError, obj)
        if impl.supports_proper_validation_errors_on_dump:
            assert exc.value.messages == {"data": ["Custom invalid message"]}

    def test_value_wrong_type(self, impl: Serializer) -> None:
        obj = DictOf[str, int](**{"data": {"a": "not_int"}})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.dump(DictOf[str, int], obj)
        if impl.supports_proper_validation_errors_on_dump:
            assert exc.value.messages == {"data": {"a": {"value": ["Not a valid integer."]}}}

    def test_nested_value_wrong_type(self, impl: Serializer) -> None:
        obj = DictOf[str, Address](**{"data": {"home": "not_an_address"}})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.dump(DictOf[str, Address], obj)
        if impl.supports_proper_validation_errors_on_dump:
            assert exc.value.messages == {
                "data": {"home": {"value": ["Invalid nested object type. Expected instance of dataclass."]}}
            }

    def test_multiple_value_errors(self, impl: Serializer) -> None:
        obj = DictOf[str, int](**{"data": {"a": "not_int", "b": "also_not_int"}})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.dump(DictOf[str, int], obj)
        if impl.supports_proper_validation_errors_on_dump:
            assert exc.value.messages == {
                "data": {"a": {"value": ["Not a valid integer."]}, "b": {"value": ["Not a valid integer."]}}
            }

    @pytest.mark.parametrize(("schema_type", "data", "expected"), _KEY_CASES)
    def test_key(self, impl: Serializer, schema_type: type, data: dict[Any, str], expected: bytes) -> None:
        result = impl.dump(schema_type, schema_type(data=data))
        assert result == expected

    @pytest.mark.parametrize(("schema_type", "data", "expected"), _WRAPPED_KEY_CASES)
    def test_wrapped_key(self, impl: Serializer, schema_type: type, data: dict[Any, str], expected: bytes) -> None:
        result = impl.dump(schema_type, schema_type(data=data))
        assert result == expected

    def test_key_empty(self, impl: Serializer) -> None:
        result = impl.dump(DictOf[int, str], DictOf[int, str](data={}))
        assert result == b'{"data":{}}'

    def test_key_optional(self, impl: Serializer) -> None:
        result = impl.dump(OptionalDictOf[int, str], OptionalDictOf[int, str](data=None))
        assert result == b"{}"

    def test_key_none_value(self, impl: Serializer) -> None:
        obj = DictOf[int, str | None](data={1: None})
        result = impl.dump(DictOf[int, str | None], obj)
        assert result == b'{"data":{"1":null}}'

    def test_key_not_affected_by_naming_case(self, impl: Serializer) -> None:
        obj = DictOf[str, int](data={"some_key": 1})
        result = impl.dump(DictOf[str, int], obj, naming_case=mr.CAMEL_CASE)
        assert result == b'{"data":{"some_key":1}}'

    @pytest.mark.parametrize(
        ("schema_type", "data", "expected"),
        [
            pytest.param(WithStrKeyMinLength, {"abc": 1}, b'{"data":{"abc":1}}', id="str_min_length"),
            pytest.param(WithIntKeyGte, {10: "x"}, b'{"data":{"10":"x"}}', id="int_gte"),
        ],
    )
    def test_key_meta_pass(self, impl: Serializer, schema_type: type, data: dict[Any, Any], expected: bytes) -> None:
        result = impl.dump(schema_type, schema_type(data=data))
        assert result == expected

    @pytest.mark.parametrize(
        ("schema_type", "data", "error_messages"),
        [
            pytest.param(
                WithStrKeyMinLength,
                {"ab": 1},
                {"data": {"ab": {"key": ["Shorter than minimum length 3."]}}},
                id="str_min_length",
            ),
            pytest.param(
                WithIntKeyGte,
                {5: "x"},
                {"data": {"5": {"key": ["Must be greater than or equal to 10."]}}},
                id="int_gte",
            ),
        ],
    )
    def test_key_meta_fail(
        self, impl: Serializer, schema_type: type, data: dict[Any, Any], error_messages: dict[str, Any]
    ) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.dump(schema_type, schema_type(data=data))
        if impl.supports_proper_validation_errors_on_dump:
            assert exc.value.messages == error_messages

    def test_key_wrong_type(self, impl: Serializer) -> None:
        obj = DictOf[int, str](**{"data": {"not_int": "x"}})  # type: ignore[dict-item]
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.dump(DictOf[int, str], obj)
        if impl.supports_proper_validation_errors_on_dump:
            assert exc.value.messages == {"data": {"not_int": {"key": ["Not a valid integer."]}}}

    @pytest.mark.parametrize(("schema_type", "obj_data", "json_data", "error_messages"), _KEY_AND_VALUE_ERROR_CASES)
    def test_key_and_value_wrong_type(
        self,
        impl: Serializer,
        schema_type: type,
        obj_data: dict[Any, Any],
        json_data: bytes,
        error_messages: dict[str, Any],
    ) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.dump(schema_type, schema_type(data=obj_data))
        if impl.supports_proper_validation_errors_on_dump:
            assert exc.value.messages == error_messages

    @pytest.mark.parametrize("container", _UNSUPPORTED_KEY_CONTAINERS)
    @pytest.mark.parametrize("key_type", _UNSUPPORTED_KEY_CASES)
    def test_unsupported_key(self, impl: Serializer, key_type: Any, container: Any) -> None:
        schema_type = _with_unsupported_key(container, key_type)
        with pytest.raises(ValueError, match="Unsupported dict key"):
            impl.dump(schema_type, schema_type(data={}))

    @pytest.mark.parametrize(
        ("schema_type", "data", "expected"),
        [
            pytest.param(WithAsStringMetadataValue, {"a": 1}, b'{"data":{"a":1}}', id="value"),
            pytest.param(WithAsStringMetadataKey, {1: "x"}, b'{"data":{"1":"x"}}', id="key"),
        ],
    )
    def test_as_string_metadata_ignored(
        self, impl: Serializer, schema_type: type, data: dict[Any, Any], expected: bytes
    ) -> None:
        result = impl.dump(schema_type, schema_type(data=data))
        assert result == expected


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

    def test_nested_value_wrong_type(self, impl: Serializer) -> None:
        data = b'{"data":{"home":"not_a_dict"}}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(DictOf[str, Address], data)
        assert exc.value.messages == {"data": {"home": {"value": {"_schema": ["Invalid input type."]}}}}

    def test_multiple_value_errors(self, impl: Serializer) -> None:
        data = b'{"data":{"a":"not_int","b":"also_not_int"}}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(DictOf[str, int], data)
        assert exc.value.messages == {
            "data": {"a": {"value": ["Not a valid integer."]}, "b": {"value": ["Not a valid integer."]}}
        }

    @pytest.mark.parametrize(("schema_type", "expected", "data"), _KEY_CASES)
    def test_key(self, impl: Serializer, schema_type: type, expected: dict[Any, str], data: bytes) -> None:
        result = impl.load(schema_type, data)
        assert result == schema_type(data=expected)

    @pytest.mark.parametrize(("schema_type", "expected", "data"), _WRAPPED_KEY_CASES)
    def test_wrapped_key(self, impl: Serializer, schema_type: type, expected: dict[Any, str], data: bytes) -> None:
        result = impl.load(schema_type, data)
        assert result == schema_type(data=expected)

    def test_key_empty(self, impl: Serializer) -> None:
        result = impl.load(DictOf[int, str], b'{"data":{}}')
        assert result == DictOf[int, str](data={})

    def test_key_optional(self, impl: Serializer) -> None:
        result = impl.load(OptionalDictOf[int, str], b'{"data":null}')
        assert result == OptionalDictOf[int, str](data=None)

    def test_key_none_value(self, impl: Serializer) -> None:
        result = impl.load(DictOf[int, str | None], b'{"data":{"1":null}}')
        assert result == DictOf[int, str | None](data={1: None})

    @pytest.mark.parametrize(
        ("data", "expected"),
        [
            pytest.param(b'{"data":{"true":"x"}}', {True: "x"}, id="lowercase_true"),
            pytest.param(b'{"data":{"false":"x"}}', {False: "x"}, id="lowercase_false"),
            pytest.param(b'{"data":{"True":"x"}}', {True: "x"}, id="capitalized_true"),
            pytest.param(b'{"data":{"False":"x"}}', {False: "x"}, id="capitalized_false"),
            pytest.param(b'{"data":{"1":"x"}}', {True: "x"}, id="numeric_true"),
            pytest.param(b'{"data":{"0":"x"}}', {False: "x"}, id="numeric_false"),
        ],
    )
    def test_bool_key_forms(self, impl: Serializer, data: bytes, expected: dict[bool, str]) -> None:
        result = impl.load(DictOf[bool, str], data)
        assert result == DictOf[bool, str](data=expected)

    @pytest.mark.parametrize(
        ("schema_type", "data", "expected"),
        [
            pytest.param(WithStrKeyMinLength, b'{"data":{"abc":1}}', {"abc": 1}, id="str_min_length"),
            pytest.param(WithIntKeyGte, b'{"data":{"10":"x"}}', {10: "x"}, id="int_gte"),
        ],
    )
    def test_key_meta_pass(self, impl: Serializer, schema_type: type, data: bytes, expected: dict[Any, Any]) -> None:
        result = impl.load(schema_type, data)
        assert result == schema_type(data=expected)

    @pytest.mark.parametrize(
        ("schema_type", "data", "error_messages"),
        [
            pytest.param(
                WithStrKeyMinLength,
                b'{"data":{"ab":1}}',
                {"data": {"ab": {"key": ["Shorter than minimum length 3."]}}},
                id="str_min_length",
            ),
            pytest.param(
                WithIntKeyGte,
                b'{"data":{"5":"x"}}',
                {"data": {"5": {"key": ["Must be greater than or equal to 10."]}}},
                id="int_gte",
            ),
        ],
    )
    def test_key_meta_fail(
        self, impl: Serializer, schema_type: type, data: bytes, error_messages: dict[str, Any]
    ) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(schema_type, data)
        assert exc.value.messages == error_messages

    def test_key_wrong_type(self, impl: Serializer) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(DictOf[int, str], b'{"data":{"not_int":"x"}}')
        assert exc.value.messages == {"data": {"not_int": {"key": ["Not a valid integer."]}}}

    @pytest.mark.parametrize(("schema_type", "obj_data", "json_data", "error_messages"), _KEY_AND_VALUE_ERROR_CASES)
    def test_key_and_value_wrong_type(
        self,
        impl: Serializer,
        schema_type: type,
        obj_data: dict[Any, Any],
        json_data: bytes,
        error_messages: dict[str, Any],
    ) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(schema_type, json_data)
        assert exc.value.messages == error_messages

    @pytest.mark.parametrize(
        ("schema_type", "data", "error_messages"),
        [
            pytest.param(
                DictOf[str, int],
                b'{"data":{"a":null}}',
                {"data": {"a": {"value": ["Field may not be null."]}}},
                id="null_value",
            ),
            pytest.param(
                DictOf[int, str],
                b'{"data":{"not_int":null}}',
                {"data": {"not_int": {"key": ["Not a valid integer."], "value": ["Field may not be null."]}}},
                id="bad_key_and_null_value",
            ),
        ],
    )
    def test_null_value_rejected(
        self, impl: Serializer, schema_type: type, data: bytes, error_messages: dict[str, Any]
    ) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(schema_type, data)
        assert exc.value.messages == error_messages

    @pytest.mark.parametrize("container", _UNSUPPORTED_KEY_CONTAINERS)
    @pytest.mark.parametrize("key_type", _UNSUPPORTED_KEY_CASES)
    def test_unsupported_key(self, impl: Serializer, key_type: Any, container: Any) -> None:
        schema_type = _with_unsupported_key(container, key_type)
        with pytest.raises(ValueError, match="Unsupported dict key"):
            impl.load(schema_type, b'{"data":{}}')


class TestRootDictDump:
    @pytest.mark.parametrize(
        ("schema_type", "obj", "expected"),
        [
            (dict[str, str], {"a": "x", "b": "y"}, b'{"a":"x","b":"y"}'),
            (dict[str, int], {"a": 1, "b": 2}, b'{"a":1,"b":2}'),
            (dict[str, float], {"a": 1.5, "b": 2.5}, b'{"a":1.5,"b":2.5}'),
            (dict[str, bool], {"a": True, "b": False}, b'{"a":true,"b":false}'),
            (dict[str, decimal.Decimal], {"a": decimal.Decimal("1.23")}, b'{"a":"1.23"}'),
            (
                dict[str, uuid.UUID],
                {"a": uuid.UUID("12345678-1234-5678-1234-567812345678")},
                b'{"a":"12345678-1234-5678-1234-567812345678"}',
            ),
            (
                dict[str, datetime.datetime],
                {"a": datetime.datetime(2024, 1, 15, 10, 30, 0, tzinfo=datetime.UTC)},
                b'{"a":"2024-01-15T10:30:00+00:00"}',
            ),
            (dict[str, datetime.date], {"a": datetime.date(2024, 1, 15)}, b'{"a":"2024-01-15"}'),
            (dict[str, datetime.time], {"a": datetime.time(10, 30, 0)}, b'{"a":"10:30:00"}'),
            (dict[str, Status], {"a": Status.ACTIVE, "b": Status.PENDING}, b'{"a":"active","b":"pending"}'),
            (dict[str, Priority], {"a": Priority.LOW, "b": Priority.HIGH}, b'{"a":1,"b":3}'),
            (
                dict[str, Address],
                {"home": Address(street="Main St", city="NYC", zip_code="10001")},
                b'{"home":{"street":"Main St","city":"NYC","zip_code":"10001"}}',
            ),
            (dict[str, list[int]], {"a": [1, 2], "b": [3, 4]}, b'{"a":[1,2],"b":[3,4]}'),
            (dict[str, dict[str, int]], {"a": {"x": 1}, "b": {"y": 2}}, b'{"a":{"x":1},"b":{"y":2}}'),
            (dict[str, int | None], {"a": 1, "b": None}, b'{"a":1,"b":null}'),
            (dict[str, Any], {"a": 1, "b": "two", "c": None}, b'{"a":1,"b":"two","c":null}'),
            (dict[str, int], {}, b"{}"),
        ],
    )
    def test_value(self, impl: Serializer, schema_type: type, obj: object, expected: bytes) -> None:
        if not impl.supports_root_non_dataclasses:
            with pytest.raises(ValueError):
                impl.dump(schema_type, obj)
            return
        result = impl.dump(schema_type, obj)
        assert result == expected

    @pytest.mark.parametrize(
        ("schema_type", "obj", "expected"),
        [
            pytest.param(dict[int, str], {1: "x"}, b'{"1":"x"}', id="int"),
            pytest.param(
                dict[uuid.UUID, str], {_KEY_UUID: "x"}, b'{"12345678-1234-5678-1234-567812345678":"x"}', id="uuid"
            ),
            pytest.param(dict[Priority, str], {Priority.LOW: "x"}, b'{"1":"x"}', id="int_enum"),
        ],
    )
    def test_key(self, impl: Serializer, schema_type: type, obj: object, expected: bytes) -> None:
        if not impl.supports_root_non_dataclasses:
            with pytest.raises(ValueError):
                impl.dump(schema_type, obj)
            return
        result = impl.dump(schema_type, obj)
        assert result == expected

    @pytest.mark.parametrize(("schema_type", "obj", "json_data", "error_messages"), _ROOT_ERROR_CASES)
    def test_wrong_type(
        self, impl: Serializer, schema_type: type, obj: object, json_data: bytes, error_messages: dict[str, Any]
    ) -> None:
        if not impl.supports_root_non_dataclasses:
            with pytest.raises(ValueError):
                impl.dump(schema_type, obj)
            return
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.dump(schema_type, obj)
        assert exc.value.messages == error_messages


class TestRootDictLoad:
    @pytest.mark.parametrize(
        ("schema_type", "data", "expected"),
        [
            (dict[str, str], b'{"a":"x","b":"y"}', {"a": "x", "b": "y"}),
            (dict[str, int], b'{"a":1,"b":2}', {"a": 1, "b": 2}),
            (dict[str, float], b'{"a":1.5,"b":2.5}', {"a": 1.5, "b": 2.5}),
            (dict[str, bool], b'{"a":true,"b":false}', {"a": True, "b": False}),
            (dict[str, decimal.Decimal], b'{"a":"1.23"}', {"a": decimal.Decimal("1.23")}),
            (
                dict[str, uuid.UUID],
                b'{"a":"12345678-1234-5678-1234-567812345678"}',
                {"a": uuid.UUID("12345678-1234-5678-1234-567812345678")},
            ),
            (
                dict[str, datetime.datetime],
                b'{"a":"2024-01-15T10:30:00+00:00"}',
                {"a": datetime.datetime(2024, 1, 15, 10, 30, 0, tzinfo=datetime.UTC)},
            ),
            (dict[str, datetime.date], b'{"a":"2024-01-15"}', {"a": datetime.date(2024, 1, 15)}),
            (dict[str, datetime.time], b'{"a":"10:30:00"}', {"a": datetime.time(10, 30, 0)}),
            (dict[str, Status], b'{"a":"active","b":"pending"}', {"a": Status.ACTIVE, "b": Status.PENDING}),
            (dict[str, Priority], b'{"a":1,"b":3}', {"a": Priority.LOW, "b": Priority.HIGH}),
            (
                dict[str, Address],
                b'{"home":{"street":"Main St","city":"NYC","zip_code":"10001"}}',
                {"home": Address(street="Main St", city="NYC", zip_code="10001")},
            ),
            (dict[str, list[int]], b'{"a":[1,2],"b":[3,4]}', {"a": [1, 2], "b": [3, 4]}),
            (dict[str, dict[str, int]], b'{"a":{"x":1},"b":{"y":2}}', {"a": {"x": 1}, "b": {"y": 2}}),
            (dict[str, int | None], b'{"a":1,"b":null}', {"a": 1, "b": None}),
            (dict[str, Any], b'{"a":1,"b":"two","c":null}', {"a": 1, "b": "two", "c": None}),
            (dict[str, int], b"{}", {}),
        ],
    )
    def test_value(self, impl: Serializer, schema_type: type, data: bytes, expected: object) -> None:
        if not impl.supports_root_non_dataclasses:
            with pytest.raises(ValueError):
                impl.load(schema_type, data)
            return
        result = impl.load(schema_type, data)
        assert result == expected

    @pytest.mark.parametrize(
        ("schema_type", "data", "expected"),
        [
            pytest.param(dict[int, str], b'{"1":"x"}', {1: "x"}, id="int"),
            pytest.param(
                dict[uuid.UUID, str], b'{"12345678-1234-5678-1234-567812345678":"x"}', {_KEY_UUID: "x"}, id="uuid"
            ),
            pytest.param(dict[Priority, str], b'{"1":"x"}', {Priority.LOW: "x"}, id="int_enum"),
        ],
    )
    def test_key(self, impl: Serializer, schema_type: type, data: bytes, expected: object) -> None:
        if not impl.supports_root_non_dataclasses:
            with pytest.raises(ValueError):
                impl.load(schema_type, data)
            return
        result = impl.load(schema_type, data)
        assert result == expected

    @pytest.mark.parametrize(("schema_type", "obj", "json_data", "error_messages"), _ROOT_ERROR_CASES)
    def test_wrong_type(
        self, impl: Serializer, schema_type: type, obj: object, json_data: bytes, error_messages: dict[str, Any]
    ) -> None:
        if not impl.supports_root_non_dataclasses:
            with pytest.raises(ValueError):
                impl.load(schema_type, json_data)
            return
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(schema_type, json_data)
        assert exc.value.messages == error_messages

    @pytest.mark.parametrize(
        ("schema_type", "data", "error_messages"),
        [
            pytest.param(dict[str, int], b'{"a":null}', {"a": {"value": ["Field may not be null."]}}, id="null_value"),
            pytest.param(dict[str, int | None], b'{"a":null}', None, id="optional_value_allows_null"),
        ],
    )
    def test_null_value(
        self, impl: Serializer, schema_type: type, data: bytes, error_messages: dict[str, Any] | None
    ) -> None:
        if not impl.supports_root_non_dataclasses:
            with pytest.raises(ValueError):
                impl.load(schema_type, data)
            return
        if error_messages is None:
            assert impl.load(schema_type, data) == {"a": None}
            return
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(schema_type, data)
        assert exc.value.messages == error_messages
