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
        ("value_type", "value", "expected"),
        [
            pytest.param(str, {"a": "x", "b": "y"}, b'{"data":{"a":"x","b":"y"}}', id="str"),
            pytest.param(int, {"a": 1, "b": 2}, b'{"data":{"a":1,"b":2}}', id="int"),
            pytest.param(float, {"a": 1.5, "b": 2.5}, b'{"data":{"a":1.5,"b":2.5}}', id="float"),
            pytest.param(bool, {"a": True, "b": False}, b'{"data":{"a":true,"b":false}}', id="bool"),
            pytest.param(
                decimal.Decimal,
                {"a": decimal.Decimal("1.23"), "b": decimal.Decimal("4.56")},
                b'{"data":{"a":"1.23","b":"4.56"}}',
                id="decimal",
            ),
            pytest.param(
                uuid.UUID,
                {"a": uuid.UUID("12345678-1234-5678-1234-567812345678")},
                b'{"data":{"a":"12345678-1234-5678-1234-567812345678"}}',
                id="uuid",
            ),
            pytest.param(
                datetime.datetime,
                {"a": datetime.datetime(2024, 1, 15, 10, 30, 0, tzinfo=datetime.UTC)},
                b'{"data":{"a":"2024-01-15T10:30:00+00:00"}}',
                id="datetime",
            ),
            pytest.param(datetime.date, {"a": datetime.date(2024, 1, 15)}, b'{"data":{"a":"2024-01-15"}}', id="date"),
            pytest.param(datetime.time, {"a": datetime.time(10, 30, 0)}, b'{"data":{"a":"10:30:00"}}', id="time"),
            pytest.param(
                Status,
                {"a": Status.ACTIVE, "b": Status.PENDING},
                b'{"data":{"a":"active","b":"pending"}}',
                id="str_enum",
            ),
            pytest.param(Priority, {"a": Priority.LOW, "b": Priority.HIGH}, b'{"data":{"a":1,"b":3}}', id="int_enum"),
        ],
    )
    def test_value(self, impl: Serializer, value_type: type, value: dict, expected: bytes) -> None:
        obj = MappingOf[str, value_type](data=value)
        result = impl.dump(MappingOf[str, value_type], obj)
        assert result == expected

    def test_dataclass_value(self, impl: Serializer) -> None:
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

    def test_single_key(self, impl: Serializer) -> None:
        obj = MappingOf[str, int](data={"only_key": 42})
        result = impl.dump(MappingOf[str, int], obj)
        assert result == b'{"data":{"only_key":42}}'

    def test_large_mapping(self, impl: Serializer) -> None:
        data = {f"key_{i}": i for i in range(200)}
        obj = MappingOf[str, int](data=data)
        result = impl.dump(MappingOf[str, int], obj)
        parsed = json.loads(result)
        assert parsed["data"] == data

    def test_deeply_nested(self, impl: Serializer) -> None:
        obj = MappingOf[str, Mapping[str, Mapping[str, int]]](data={"a": {"b": {"c": 1}}})
        result = impl.dump(MappingOf[str, Mapping[str, Mapping[str, int]]], obj)
        assert result == b'{"data":{"a":{"b":{"c":1}}}}'

    def test_optional_none(self, impl: Serializer) -> None:
        obj = OptionalMappingOf[str, int](data=None)
        result = impl.dump(OptionalMappingOf[str, int], obj)
        assert result == b"{}"

    def test_optional_value_present(self, impl: Serializer) -> None:
        obj = OptionalMappingOf[str, int](data={"a": 1})
        result = impl.dump(OptionalMappingOf[str, int], obj)
        assert result == b'{"data":{"a":1}}'

    def test_none_handling_ignore_explicit(self, impl: Serializer) -> None:
        obj = OptionalMappingOf[str, int](data=None)
        result = impl.dump(OptionalMappingOf[str, int], obj, none_value_handling=mr.NoneValueHandling.IGNORE)
        assert result == b"{}"

    def test_none_handling_include(self, impl: Serializer) -> None:
        obj = OptionalMappingOf[str, int](data=None)
        result = impl.dump(OptionalMappingOf[str, int], obj, none_value_handling=mr.NoneValueHandling.INCLUDE)
        assert result == b'{"data":null}'

    def test_none_handling_include_with_value(self, impl: Serializer) -> None:
        obj = OptionalMappingOf[str, int](data={"a": 1})
        result = impl.dump(OptionalMappingOf[str, int], obj, none_value_handling=mr.NoneValueHandling.INCLUDE)
        assert result == b'{"data":{"a":1}}'

    def test_missing(self, impl: Serializer) -> None:
        obj = WithMappingMissing()
        result = impl.dump(WithMappingMissing, obj)
        assert result == b"{}"

    def test_missing_with_value(self, impl: Serializer) -> None:
        obj = WithMappingMissing(data={"a": 1, "b": 2})
        result = impl.dump(WithMappingMissing, obj)
        assert result == b'{"data":{"a":1,"b":2}}'

    def test_unsubscripted(self, impl: Serializer) -> None:
        obj = CollectionHolder[Mapping](items={"a": 1, "b": "va"})
        result = impl.dump(CollectionHolder[Mapping], obj)
        assert result == b'{"items":{"a":1,"b":"va"}}'


class TestMappingLoad:
    @pytest.mark.parametrize(
        ("value_type", "data", "expected_data"),
        [
            pytest.param(str, b'{"data":{"a":"x","b":"y"}}', {"a": "x", "b": "y"}, id="str"),
            pytest.param(int, b'{"data":{"a":1,"b":2}}', {"a": 1, "b": 2}, id="int"),
            pytest.param(float, b'{"data":{"a":1.5,"b":2.5}}', {"a": 1.5, "b": 2.5}, id="float"),
            pytest.param(bool, b'{"data":{"a":true,"b":false}}', {"a": True, "b": False}, id="bool"),
            pytest.param(
                decimal.Decimal,
                b'{"data":{"a":"1.23","b":"4.56"}}',
                {"a": decimal.Decimal("1.23"), "b": decimal.Decimal("4.56")},
                id="decimal",
            ),
            pytest.param(
                uuid.UUID,
                b'{"data":{"a":"12345678-1234-5678-1234-567812345678"}}',
                {"a": uuid.UUID("12345678-1234-5678-1234-567812345678")},
                id="uuid",
            ),
            pytest.param(
                datetime.datetime,
                b'{"data":{"a":"2024-01-15T10:30:00+00:00"}}',
                {"a": datetime.datetime(2024, 1, 15, 10, 30, 0, tzinfo=datetime.UTC)},
                id="datetime",
            ),
            pytest.param(datetime.date, b'{"data":{"a":"2024-01-15"}}', {"a": datetime.date(2024, 1, 15)}, id="date"),
            pytest.param(datetime.time, b'{"data":{"a":"10:30:00"}}', {"a": datetime.time(10, 30, 0)}, id="time"),
            pytest.param(
                Status,
                b'{"data":{"a":"active","b":"pending"}}',
                {"a": Status.ACTIVE, "b": Status.PENDING},
                id="str_enum",
            ),
            pytest.param(Priority, b'{"data":{"a":1,"b":3}}', {"a": Priority.LOW, "b": Priority.HIGH}, id="int_enum"),
        ],
    )
    def test_value(self, impl: Serializer, value_type: type, data: bytes, expected_data: dict) -> None:
        result = impl.load(MappingOf[str, value_type], data)
        assert result == MappingOf[str, value_type](data=expected_data)

    def test_dataclass_value(self, impl: Serializer) -> None:
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

    def test_single_key(self, impl: Serializer) -> None:
        data = b'{"data":{"only_key":42}}'
        result = impl.load(MappingOf[str, int], data)
        assert result == MappingOf[str, int](data={"only_key": 42})

    def test_large_mapping(self, impl: Serializer) -> None:
        expected = {f"key_{i}": i for i in range(200)}
        data = json.dumps({"data": expected}).encode()
        result = impl.load(MappingOf[str, int], data)
        assert result == MappingOf[str, int](data=expected)

    def test_deeply_nested(self, impl: Serializer) -> None:
        data = b'{"data":{"a":{"b":{"c":1}}}}'
        result = impl.load(MappingOf[str, Mapping[str, Mapping[str, int]]], data)
        assert result == MappingOf[str, Mapping[str, Mapping[str, int]]](data={"a": {"b": {"c": 1}}})

    def test_optional_none(self, impl: Serializer) -> None:
        data = b"{}"
        result = impl.load(OptionalMappingOf[str, int], data)
        assert result == OptionalMappingOf[str, int](data=None)

    def test_optional_value_present(self, impl: Serializer) -> None:
        data = b'{"data":{"a":1}}'
        result = impl.load(OptionalMappingOf[str, int], data)
        assert result == OptionalMappingOf[str, int](data={"a": 1})

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
            b'{"data":{}}',  # first validator fails (empty)
            b'{"data":{"a":0,"b":1,"c":2,"d":3,"e":4,"f":5,"g":6,"h":7,"i":8,"j":9,"k":10}}',  # second validator fails (>10 items)
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

    @pytest.mark.parametrize("data", [b'{"data":"not_a_mapping"}', b'{"data":[1,2,3]}'])
    def test_wrong_type(self, impl: Serializer, data: bytes) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(MappingOf[str, int], data)
        assert exc.value.messages == {"data": ["Not a valid dict."]}

    def test_missing_required(self, impl: Serializer) -> None:
        data = b"{}"
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(MappingOf[str, int], data)
        assert exc.value.messages == {"data": ["Missing data for required field."]}

    def test_custom_required_error(self, impl: Serializer) -> None:
        data = b"{}"
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithMappingRequiredError, data)
        assert exc.value.messages == {"data": ["Custom required message"]}

    def test_custom_none_error(self, impl: Serializer) -> None:
        data = b'{"data":null}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithMappingNoneError, data)
        assert exc.value.messages == {"data": ["Custom none message"]}

    def test_custom_invalid_error(self, impl: Serializer) -> None:
        data = b'{"data":"not_a_mapping"}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithMappingInvalidError, data)
        assert exc.value.messages == {"data": ["Custom invalid message"]}

    def test_missing(self, impl: Serializer) -> None:
        data = b"{}"
        result = impl.load(WithMappingMissing, data)
        assert result == WithMappingMissing()

    def test_missing_with_value(self, impl: Serializer) -> None:
        data = b'{"data":{"a":1,"b":2}}'
        result = impl.load(WithMappingMissing, data)
        assert result == WithMappingMissing(data={"a": 1, "b": 2})


class TestMappingEdgeCases:
    """Test mapping edge cases with unicode keys, big ints, and special scenarios."""

    def test_unicode_keys(self, impl: Serializer) -> None:
        obj = MappingOf[str, int](data={"ключ": 1, "键": 2, "🔑": 3, "مفتاح": 4})
        result = impl.dump(MappingOf[str, int], obj)
        loaded = impl.load(MappingOf[str, int], result)
        assert loaded == obj

    def test_empty_string_key(self, impl: Serializer) -> None:
        obj = MappingOf[str, int](data={"": 42})
        result = impl.dump(MappingOf[str, int], obj)
        assert result == b'{"data":{"":42}}'

    def test_empty_string_key_load(self, impl: Serializer) -> None:
        data = b'{"data":{"":42}}'
        result = impl.load(MappingOf[str, int], data)
        assert result == MappingOf[str, int](data={"": 42})

    def test_whitespace_keys(self, impl: Serializer) -> None:
        obj = MappingOf[str, int](data={" ": 1, "\t": 2, "\n": 3})
        result = impl.dump(MappingOf[str, int], obj)
        loaded = impl.load(MappingOf[str, int], result)
        assert loaded == obj

    def test_big_int_values(self, impl: Serializer) -> None:
        big_val = 9223372036854775808
        obj = MappingOf[str, int](data={"big": big_val, "bigger": 2**100})
        result = impl.dump(MappingOf[str, int], obj)
        loaded = impl.load(MappingOf[str, int], result)
        assert loaded == obj

    def test_multiple_nulls_in_values(self, impl: Serializer) -> None:
        obj = MappingOf[str, int | None](data={"a": None, "b": None, "c": 1, "d": None})
        result = impl.dump(MappingOf[str, int | None], obj)
        assert result == b'{"data":{"a":null,"b":null,"c":1,"d":null}}'

    def test_4_level_nesting(self, impl: Serializer) -> None:
        obj = MappingOf[str, Mapping[str, Mapping[str, Mapping[str, int]]]](data={"a": {"b": {"c": {"d": 42}}}})
        result = impl.dump(MappingOf[str, Mapping[str, Mapping[str, Mapping[str, int]]]], obj)
        loaded = impl.load(MappingOf[str, Mapping[str, Mapping[str, Mapping[str, int]]]], result)
        assert loaded == obj

    def test_special_json_chars_in_keys(self, impl: Serializer) -> None:
        obj = MappingOf[str, int](data={'"quoted"': 1, "back\\slash": 2, "new\nline": 3})
        result = impl.dump(MappingOf[str, int], obj)
        loaded = impl.load(MappingOf[str, int], result)
        assert loaded == obj

    def test_numeric_string_keys(self, impl: Serializer) -> None:
        obj = MappingOf[str, int](data={"123": 1, "0": 2, "-1": 3, "3.14": 4})
        result = impl.dump(MappingOf[str, int], obj)
        loaded = impl.load(MappingOf[str, int], result)
        assert loaded == obj
