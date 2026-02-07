import dataclasses
import datetime
import decimal
import uuid
from typing import Any, Optional

import marshmallow
import marshmallow_recipe as mr
import pytest

from .conftest import (
    Serializer,
    ValueOf,
    WithAnyDefault,
    WithAnyField,
    WithAnyMissing,
    WithAnyNamingCase,
    WithAnyTwoValidators,
    WithAnyValidation,
    WithDictAny,
    WithListAny,
    WithRequiredAny,
)


class TestAnyDump:
    def test_string(self, impl: Serializer) -> None:
        obj = WithAnyField(data="hello", name="test")
        result = impl.dump(WithAnyField, obj)
        assert result == b'{"data":"hello","name":"test"}'

    def test_int(self, impl: Serializer) -> None:
        obj = WithAnyField(data=42, name="test")
        result = impl.dump(WithAnyField, obj)
        assert result == b'{"data":42,"name":"test"}'

    def test_float(self, impl: Serializer) -> None:
        obj = WithAnyField(data=3.14, name="test")
        result = impl.dump(WithAnyField, obj)
        assert result == b'{"data":3.14,"name":"test"}'

    def test_bool(self, impl: Serializer) -> None:
        obj = WithAnyField(data=True, name="test")
        result = impl.dump(WithAnyField, obj)
        assert result == b'{"data":true,"name":"test"}'

    def test_none(self, impl: Serializer) -> None:
        obj = WithAnyField(data=None, name="test")
        result = impl.dump(WithAnyField, obj)
        assert result == b'{"name":"test"}'

    def test_list(self, impl: Serializer) -> None:
        obj = WithAnyField(data=[1, 2, 3], name="test")
        result = impl.dump(WithAnyField, obj)
        assert result == b'{"data":[1,2,3],"name":"test"}'

    def test_dict(self, impl: Serializer) -> None:
        obj = WithAnyField(data={"key": "value"}, name="test")
        result = impl.dump(WithAnyField, obj)
        assert result == b'{"data":{"key":"value"},"name":"test"}'

    def test_nested_structure(self, impl: Serializer) -> None:
        obj = WithAnyField(data={"items": [1, 2, {"nested": True}], "count": 3}, name="test")
        result = impl.dump(WithAnyField, obj)
        assert result == b'{"data":{"items":[1,2,{"nested":true}],"count":3},"name":"test"}'

    @pytest.mark.parametrize(
        ("obj", "expected"),
        [
            pytest.param(WithAnyField(data="", name="test"), b'{"data":"","name":"test"}', id="empty_string"),
            pytest.param(WithAnyField(data=0, name="test"), b'{"data":0,"name":"test"}', id="zero"),
            pytest.param(WithAnyField(data=False, name="test"), b'{"data":false,"name":"test"}', id="false"),
            pytest.param(WithAnyField(data=-42, name="test"), b'{"data":-42,"name":"test"}', id="negative_int"),
            pytest.param(WithAnyField(data=-3.14, name="test"), b'{"data":-3.14,"name":"test"}', id="negative_float"),
            pytest.param(WithAnyField(data=0.0, name="test"), b'{"data":0.0,"name":"test"}', id="zero_float"),
            pytest.param(
                WithAnyField(data={"a": {"b": {"c": {"d": 1}}}}, name="test"),
                b'{"data":{"a":{"b":{"c":{"d":1}}}},"name":"test"}',
                id="deeply_nested",
            ),
        ],
    )
    def test_value(self, impl: Serializer, obj: WithAnyField, expected: bytes) -> None:
        result = impl.dump(WithAnyField, obj)
        assert result == expected

    @pytest.mark.parametrize(
        ("obj", "expected"),
        [
            pytest.param(
                WithListAny(items=[[1, 2], [3, 4]], name="test"),
                b'{"items":[[1,2],[3,4]],"name":"test"}',
                id="nested_lists",
            ),
            pytest.param(
                WithListAny(items=["a", "b", "c"], name="test"), b'{"items":["a","b","c"],"name":"test"}', id="strings"
            ),
        ],
    )
    def test_list_any_value(self, impl: Serializer, obj: WithListAny, expected: bytes) -> None:
        result = impl.dump(WithListAny, obj)
        assert result == expected

    @pytest.mark.parametrize(
        ("obj", "expected"),
        [
            pytest.param(
                WithDictAny(data={"items": [1, 2, 3]}, name="test"),
                b'{"data":{"items":[1,2,3]},"name":"test"}',
                id="list_values",
            )
        ],
    )
    def test_dict_any_value(self, impl: Serializer, obj: WithDictAny, expected: bytes) -> None:
        result = impl.dump(WithDictAny, obj)
        assert result == expected

    def test_default_provided(self, impl: Serializer) -> None:
        obj = WithAnyDefault(data="custom", name="test")
        result = impl.dump(WithAnyDefault, obj)
        assert result == b'{"data":"custom","name":"test"}'

    @pytest.mark.parametrize(
        ("obj", "expected"),
        [
            pytest.param(WithAnyMissing(name="test"), b'{"name":"test"}', id="omitted"),
            pytest.param(WithAnyMissing(data="hello", name="test"), b'{"data":"hello","name":"test"}', id="provided"),
        ],
    )
    def test_missing(self, impl: Serializer, obj: WithAnyMissing, expected: bytes) -> None:
        result = impl.dump(WithAnyMissing, obj)
        assert result == expected

    def test_required_string(self, impl: Serializer) -> None:
        obj = WithRequiredAny(data="hello", name="test")
        result = impl.dump(WithRequiredAny, obj)
        assert result == b'{"data":"hello","name":"test"}'

    def test_required_dict(self, impl: Serializer) -> None:
        obj = WithRequiredAny(data={"key": "value"}, name="test")
        result = impl.dump(WithRequiredAny, obj)
        assert result == b'{"data":{"key":"value"},"name":"test"}'

    def test_required_list(self, impl: Serializer) -> None:
        obj = WithRequiredAny(data=[1, "two", 3.0], name="test")
        result = impl.dump(WithRequiredAny, obj)
        assert result == b'{"data":[1,"two",3.0],"name":"test"}'

    def test_list_any_mixed_types(self, impl: Serializer) -> None:
        obj = WithListAny(items=[1, "two", 3.0, True], name="test")
        result = impl.dump(WithListAny, obj)
        assert result == b'{"items":[1,"two",3.0,true],"name":"test"}'

    def test_list_any_nested_dicts(self, impl: Serializer) -> None:
        obj = WithListAny(items=[{"a": 1}, {"b": 2}], name="test")
        result = impl.dump(WithListAny, obj)
        assert result == b'{"items":[{"a":1},{"b":2}],"name":"test"}'

    def test_list_any_empty(self, impl: Serializer) -> None:
        obj = WithListAny(items=[], name="test")
        result = impl.dump(WithListAny, obj)
        assert result == b'{"items":[],"name":"test"}'

    def test_list_any_with_none_element(self, impl: Serializer) -> None:
        obj = WithListAny(items=[1, None, "three"], name="test")
        result = impl.dump(WithListAny, obj)
        assert result == b'{"items":[1,null,"three"],"name":"test"}'

    def test_list_any_all_none(self, impl: Serializer) -> None:
        obj = WithListAny(items=[None, None, None], name="test")
        result = impl.dump(WithListAny, obj)
        assert result == b'{"items":[null,null,null],"name":"test"}'

    def test_dict_any_mixed_values(self, impl: Serializer) -> None:
        obj = WithDictAny(data={"str": "hello", "int": 42, "float": 3.14, "bool": True}, name="test")
        result = impl.dump(WithDictAny, obj)
        assert result == b'{"data":{"str":"hello","int":42,"float":3.14,"bool":true},"name":"test"}'

    def test_dict_any_nested(self, impl: Serializer) -> None:
        obj = WithDictAny(data={"nested": {"deep": [1, 2, 3]}}, name="test")
        result = impl.dump(WithDictAny, obj)
        assert result == b'{"data":{"nested":{"deep":[1,2,3]}},"name":"test"}'

    def test_dict_any_empty(self, impl: Serializer) -> None:
        obj = WithDictAny(data={}, name="test")
        result = impl.dump(WithDictAny, obj)
        assert result == b'{"data":{},"name":"test"}'

    def test_dict_any_with_none_value(self, impl: Serializer) -> None:
        obj = WithDictAny(data={"key1": "value", "key2": None, "key3": 42}, name="test")
        result = impl.dump(WithDictAny, obj)
        assert result == b'{"data":{"key1":"value","key2":null,"key3":42},"name":"test"}'

    def test_dict_any_all_none(self, impl: Serializer) -> None:
        obj = WithDictAny(data={"a": None, "b": None}, name="test")
        result = impl.dump(WithDictAny, obj)
        assert result == b'{"data":{"a":null,"b":null},"name":"test"}'

    def test_camel_case(self, impl: Serializer) -> None:
        obj = WithAnyNamingCase(any_data={"key": "value"}, field_name="test")
        result = impl.dump(WithAnyNamingCase, obj, naming_case=mr.CAMEL_CASE)
        assert result == b'{"anyData":{"key":"value"},"fieldName":"test"}'

    def test_capital_camel_case(self, impl: Serializer) -> None:
        obj = WithAnyNamingCase(any_data=[1, 2, 3], field_name="test")
        result = impl.dump(WithAnyNamingCase, obj, naming_case=mr.CAPITAL_CAMEL_CASE)
        assert result == b'{"AnyData":[1,2,3],"FieldName":"test"}'

    def test_none_handling_ignore(self, impl: Serializer) -> None:
        obj = WithAnyField(data=None, name="test")
        result = impl.dump(WithAnyField, obj, none_value_handling=mr.NoneValueHandling.IGNORE)
        assert result == b'{"name":"test"}'

    def test_none_handling_include(self, impl: Serializer) -> None:
        obj = WithAnyField(data=None, name="test")
        result = impl.dump(WithAnyField, obj, none_value_handling=mr.NoneValueHandling.INCLUDE)
        assert result == b'{"data":null,"name":"test"}'

    def test_rejects_datetime(self, impl: Serializer) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.dump(ValueOf[Any], ValueOf[Any](value=datetime.datetime.now()))
        assert exc.value.messages == {"value": ["Not a valid JSON-serializable value."]}

    def test_rejects_date(self, impl: Serializer) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.dump(ValueOf[Any], ValueOf[Any](value=datetime.date.today()))
        assert exc.value.messages == {"value": ["Not a valid JSON-serializable value."]}

    def test_rejects_uuid(self, impl: Serializer) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.dump(ValueOf[Any], ValueOf[Any](value=uuid.uuid4()))
        assert exc.value.messages == {"value": ["Not a valid JSON-serializable value."]}

    def test_rejects_decimal(self, impl: Serializer) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.dump(ValueOf[Any], ValueOf[Any](value=decimal.Decimal("3.14")))
        assert exc.value.messages == {"value": ["Not a valid JSON-serializable value."]}

    def test_rejects_custom_object(self, impl: Serializer) -> None:
        @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
        class CustomObject:
            field: str

        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.dump(ValueOf[Any], ValueOf[Any](value=CustomObject(field="test")))
        assert exc.value.messages == {"value": ["Not a valid JSON-serializable value."]}

    def test_rejects_set(self, impl: Serializer) -> None:
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(ValueOf[Any], ValueOf[Any](value={1, 2, 3}))

    def test_rejects_tuple(self, impl: Serializer) -> None:
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(ValueOf[Any], ValueOf[Any](value=(1, 2, 3)))

    def test_rejects_bytes(self, impl: Serializer) -> None:
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(ValueOf[Any], ValueOf[Any](value=b"bytes"))

    def test_rejects_dict_with_non_string_keys(self, impl: Serializer) -> None:
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(ValueOf[Any], ValueOf[Any](value={1: "value"}))

    def test_rejects_list_with_invalid_items(self, impl: Serializer) -> None:
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(ValueOf[Any], ValueOf[Any](value=[1, 2, datetime.datetime.now()]))

    def test_rejects_nested_invalid_structures(self, impl: Serializer) -> None:
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(ValueOf[Any], ValueOf[Any](value={"nested": {"deeply": {"invalid": uuid.uuid4()}}}))

    def test_rejects_frozenset(self, impl: Serializer) -> None:
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(ValueOf[Any], ValueOf[Any](value=frozenset({1, 2})))

    def test_rejects_nested_list_invalid(self, impl: Serializer) -> None:
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(ValueOf[Any], ValueOf[Any](value=[1, [datetime.datetime.now()]]))

    def test_rejects_dict_tuple_value(self, impl: Serializer) -> None:
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(ValueOf[Any], ValueOf[Any](value={"key": (1, 2)}))

    def test_rejects_list_any_with_invalid_items(self, impl: Serializer) -> None:
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(WithListAny, WithListAny(items=[1, datetime.datetime.now()]))

    def test_rejects_nan_float(self, impl: Serializer) -> None:
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(ValueOf[Any], ValueOf[Any](value=float("nan")))

    def test_rejects_inf_float(self, impl: Serializer) -> None:
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(ValueOf[Any], ValueOf[Any](value=float("inf")))


class TestAnyLoad:
    def test_string(self, impl: Serializer) -> None:
        data = b'{"data":"hello","name":"test"}'
        result = impl.load(WithAnyField, data)
        assert result == WithAnyField(data="hello", name="test")

    def test_int(self, impl: Serializer) -> None:
        data = b'{"data":42,"name":"test"}'
        result = impl.load(WithAnyField, data)
        assert result == WithAnyField(data=42, name="test")

    def test_big_int(self, impl: Serializer) -> None:
        big_value = 9223372036854775808
        data = f'{{"data": {big_value}, "name": "test"}}'.encode()
        result = impl.load(WithAnyField, data)
        assert result == WithAnyField(data=big_value, name="test")

    def test_very_large_int(self, impl: Serializer) -> None:
        very_large = 2**100
        data = f'{{"data": {very_large}, "name": "test"}}'.encode()
        result = impl.load(WithAnyField, data)
        assert result == WithAnyField(data=very_large, name="test")

    def test_big_negative_int(self, impl: Serializer) -> None:
        big_negative = -9223372036854775809
        data = f'{{"data": {big_negative}, "name": "test"}}'.encode()
        result = impl.load(WithAnyField, data)
        assert result == WithAnyField(data=big_negative, name="test")

    def test_float(self, impl: Serializer) -> None:
        data = b'{"data":3.14,"name":"test"}'
        result = impl.load(WithAnyField, data)
        assert result == WithAnyField(data=3.14, name="test")

    def test_bool(self, impl: Serializer) -> None:
        data = b'{"data":true,"name":"test"}'
        result = impl.load(WithAnyField, data)
        assert result == WithAnyField(data=True, name="test")

    def test_none(self, impl: Serializer) -> None:
        data = b'{"data":null,"name":"test"}'
        result = impl.load(WithAnyField, data)
        assert result == WithAnyField(data=None, name="test")

    def test_list(self, impl: Serializer) -> None:
        data = b'{"data":[1,2,3],"name":"test"}'
        result = impl.load(WithAnyField, data)
        assert result == WithAnyField(data=[1, 2, 3], name="test")

    def test_dict(self, impl: Serializer) -> None:
        data = b'{"data":{"key":"value"},"name":"test"}'
        result = impl.load(WithAnyField, data)
        assert result == WithAnyField(data={"key": "value"}, name="test")

    def test_nested_structure(self, impl: Serializer) -> None:
        data = b'{"data":{"items":[1,2,{"nested":true}],"count":3},"name":"test"}'
        result = impl.load(WithAnyField, data)
        assert result == WithAnyField(data={"items": [1, 2, {"nested": True}], "count": 3}, name="test")

    @pytest.mark.parametrize(
        ("data", "expected"),
        [
            pytest.param(b'{"data":"","name":"test"}', WithAnyField(data="", name="test"), id="empty_string"),
            pytest.param(b'{"data":0,"name":"test"}', WithAnyField(data=0, name="test"), id="zero"),
            pytest.param(b'{"data":false,"name":"test"}', WithAnyField(data=False, name="test"), id="false"),
            pytest.param(b'{"data":-42,"name":"test"}', WithAnyField(data=-42, name="test"), id="negative_int"),
            pytest.param(b'{"data":-3.14,"name":"test"}', WithAnyField(data=-3.14, name="test"), id="negative_float"),
            pytest.param(b'{"data":0.0,"name":"test"}', WithAnyField(data=0.0, name="test"), id="zero_float"),
            pytest.param(
                b'{"data":{"a":{"b":{"c":{"d":1}}}},"name":"test"}',
                WithAnyField(data={"a": {"b": {"c": {"d": 1}}}}, name="test"),
                id="deeply_nested",
            ),
        ],
    )
    def test_value(self, impl: Serializer, data: bytes, expected: WithAnyField) -> None:
        result = impl.load(WithAnyField, data)
        assert result == expected

    @pytest.mark.parametrize(
        ("data", "expected"),
        [
            pytest.param(
                b'{"items":[[1,2],[3,4]],"name":"test"}',
                WithListAny(items=[[1, 2], [3, 4]], name="test"),
                id="nested_lists",
            ),
            pytest.param(
                b'{"items":["a","b","c"],"name":"test"}', WithListAny(items=["a", "b", "c"], name="test"), id="strings"
            ),
        ],
    )
    def test_list_any_value(self, impl: Serializer, data: bytes, expected: WithListAny) -> None:
        result = impl.load(WithListAny, data)
        assert result == expected

    @pytest.mark.parametrize(
        ("data", "expected"),
        [
            pytest.param(b'{"name":"test"}', WithAnyDefault(data="default_value", name="test"), id="omitted"),
            pytest.param(b'{"data":"custom","name":"test"}', WithAnyDefault(data="custom", name="test"), id="provided"),
        ],
    )
    def test_default(self, impl: Serializer, data: bytes, expected: WithAnyDefault) -> None:
        result = impl.load(WithAnyDefault, data)
        assert result == expected

    @pytest.mark.parametrize(
        ("data", "expected"),
        [
            pytest.param(b'{"name":"test"}', WithAnyMissing(name="test"), id="omitted"),
            pytest.param(b'{"data":"hello","name":"test"}', WithAnyMissing(data="hello", name="test"), id="provided"),
        ],
    )
    def test_missing(self, impl: Serializer, data: bytes, expected: WithAnyMissing) -> None:
        result = impl.load(WithAnyMissing, data)
        assert result == expected

    def test_required_string(self, impl: Serializer) -> None:
        data = b'{"data":"hello","name":"test"}'
        result = impl.load(WithRequiredAny, data)
        assert result == WithRequiredAny(data="hello", name="test")

    def test_required_dict(self, impl: Serializer) -> None:
        data = b'{"data":{"key":"value"},"name":"test"}'
        result = impl.load(WithRequiredAny, data)
        assert result == WithRequiredAny(data={"key": "value"}, name="test")

    def test_required_list(self, impl: Serializer) -> None:
        data = b'{"data":[1,"two",3.0],"name":"test"}'
        result = impl.load(WithRequiredAny, data)
        assert result == WithRequiredAny(data=[1, "two", 3.0], name="test")

    def test_list_any_mixed_types(self, impl: Serializer) -> None:
        data = b'{"items":[1,"two",3.0,true],"name":"test"}'
        result = impl.load(WithListAny, data)
        assert result == WithListAny(items=[1, "two", 3.0, True], name="test")

    def test_list_any_nested_dicts(self, impl: Serializer) -> None:
        data = b'{"items":[{"a":1},{"b":2}],"name":"test"}'
        result = impl.load(WithListAny, data)
        assert result == WithListAny(items=[{"a": 1}, {"b": 2}], name="test")

    def test_list_any_empty(self, impl: Serializer) -> None:
        data = b'{"items":[],"name":"test"}'
        result = impl.load(WithListAny, data)
        assert result == WithListAny(items=[], name="test")

    def test_list_any_with_none_element(self, impl: Serializer) -> None:
        data = b'{"items":[1,null,"three"],"name":"test"}'
        result = impl.load(WithListAny, data)
        assert result == WithListAny(items=[1, None, "three"], name="test")

    def test_list_any_all_none(self, impl: Serializer) -> None:
        data = b'{"items":[null,null,null],"name":"test"}'
        result = impl.load(WithListAny, data)
        assert result == WithListAny(items=[None, None, None], name="test")

    def test_list_any_with_big_int(self, impl: Serializer) -> None:
        big_value = 9223372036854775808
        data = f'{{"items": [1, {big_value}, "str"], "name": "test"}}'.encode()
        result = impl.load(WithListAny, data)
        assert result == WithListAny(items=[1, big_value, "str"], name="test")

    def test_dict_any_mixed_values(self, impl: Serializer) -> None:
        data = b'{"data":{"str":"hello","int":42,"float":3.14,"bool":true},"name":"test"}'
        result = impl.load(WithDictAny, data)
        assert result == WithDictAny(data={"str": "hello", "int": 42, "float": 3.14, "bool": True}, name="test")

    def test_dict_any_nested(self, impl: Serializer) -> None:
        data = b'{"data":{"nested":{"deep":[1,2,3]}},"name":"test"}'
        result = impl.load(WithDictAny, data)
        assert result == WithDictAny(data={"nested": {"deep": [1, 2, 3]}}, name="test")

    def test_dict_any_empty(self, impl: Serializer) -> None:
        data = b'{"data":{},"name":"test"}'
        result = impl.load(WithDictAny, data)
        assert result == WithDictAny(data={}, name="test")

    def test_dict_any_with_none_value(self, impl: Serializer) -> None:
        data = b'{"data":{"key1":"value","key2":null,"key3":42},"name":"test"}'
        result = impl.load(WithDictAny, data)
        assert result == WithDictAny(data={"key1": "value", "key2": None, "key3": 42}, name="test")

    def test_dict_any_all_none(self, impl: Serializer) -> None:
        data = b'{"data":{"a":null,"b":null},"name":"test"}'
        result = impl.load(WithDictAny, data)
        assert result == WithDictAny(data={"a": None, "b": None}, name="test")

    def test_camel_case(self, impl: Serializer) -> None:
        data = b'{"anyData":{"key":"value"},"fieldName":"test"}'
        result = impl.load(WithAnyNamingCase, data, naming_case=mr.CAMEL_CASE)
        assert result == WithAnyNamingCase(any_data={"key": "value"}, field_name="test")

    def test_capital_camel_case(self, impl: Serializer) -> None:
        data = b'{"AnyData":[1,2,3],"FieldName":"test"}'
        result = impl.load(WithAnyNamingCase, data, naming_case=mr.CAPITAL_CAMEL_CASE)
        assert result == WithAnyNamingCase(any_data=[1, 2, 3], field_name="test")

    def test_validation_pass(self, impl: Serializer) -> None:
        data = b'{"data":"hello"}'
        result = impl.load(WithAnyValidation, data)
        assert result == WithAnyValidation(data="hello")

    def test_validation_fail(self, impl: Serializer) -> None:
        data = b'{"data":42}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithAnyValidation, data)
        assert exc.value.messages == {"data": ["Invalid value."]}

    def test_two_validators_pass(self, impl: Serializer) -> None:
        data = b'{"data":"hello"}'
        result = impl.load(WithAnyTwoValidators, data)
        assert result == WithAnyTwoValidators(data="hello")

    def test_two_validators_second_fails(self, impl: Serializer) -> None:
        data = b'{"data":42}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithAnyTwoValidators, data)
        assert exc.value.messages == {"data": ["Invalid value."]}


class TestAnyTypeErrors:
    def test_optional_any_raises_error(self, impl: Serializer) -> None:
        @dataclasses.dataclass
        class WithOptionalAny:
            data: Optional[Any]

        with pytest.raises(ValueError) as exc_info:
            impl.dump(WithOptionalAny, WithOptionalAny(data=None))

        assert exc_info.value.args[0] == (
            "Any type cannot be used in Optional or Union (Any | None, Optional[Any], Union[Any, ...] are invalid)"
        )

    def test_any_or_none_raises_error(self, impl: Serializer) -> None:
        @dataclasses.dataclass
        class WithAnyOrNone:
            data: Any | None

        with pytest.raises(ValueError) as exc_info:
            impl.dump(WithAnyOrNone, WithAnyOrNone(data=None))

        assert exc_info.value.args[0] == (
            "Any type cannot be used in Optional or Union (Any | None, Optional[Any], Union[Any, ...] are invalid)"
        )

    def test_union_with_any_raises_error(self, impl: Serializer) -> None:
        @dataclasses.dataclass
        class WithUnionAny:
            data: int | Any

        with pytest.raises(ValueError) as exc_info:
            impl.dump(WithUnionAny, WithUnionAny(data=42))

        assert exc_info.value.args[0] == (
            "Any type cannot be used in Optional or Union (Any | None, Optional[Any], Union[Any, ...] are invalid)"
        )
