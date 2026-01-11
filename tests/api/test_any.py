import dataclasses
import datetime
import decimal
import uuid
from typing import Any, Optional

import marshmallow
import pytest

import marshmallow_recipe as mr

from .conftest import Serializer, ValueOf, WithAnyField, WithAnyNamingCase, WithDictAny, WithListAny, WithRequiredAny


class TestAnyDump:
    @pytest.mark.parametrize(
        ("data", "expected"),
        [
            pytest.param("hello", b'{"data":"hello","name":"test"}', id="string"),
            pytest.param(42, b'{"data":42,"name":"test"}', id="int"),
            pytest.param(3.14, b'{"data":3.14,"name":"test"}', id="float"),
            pytest.param(True, b'{"data":true,"name":"test"}', id="bool"),
            pytest.param(None, b'{"name":"test"}', id="none"),
            pytest.param([1, 2, 3], b'{"data":[1,2,3],"name":"test"}', id="list"),
            pytest.param({"key": "value"}, b'{"data":{"key":"value"},"name":"test"}', id="dict"),
            pytest.param(
                {"items": [1, 2, {"nested": True}], "count": 3},
                b'{"data":{"items":[1,2,{"nested":true}],"count":3},"name":"test"}',
                id="nested_structure",
            ),
        ],
    )
    def test_value(self, impl: Serializer, data: object, expected: bytes) -> None:
        obj = WithAnyField(data=data, name="test")
        result = impl.dump(WithAnyField, obj)
        assert result == expected

    @pytest.mark.parametrize(
        ("data", "expected"),
        [
            pytest.param("hello", b'{"data":"hello","name":"test"}', id="string"),
            pytest.param({"key": "value"}, b'{"data":{"key":"value"},"name":"test"}', id="dict"),
            pytest.param([1, "two", 3.0], b'{"data":[1,"two",3.0],"name":"test"}', id="list"),
        ],
    )
    def test_required(self, impl: Serializer, data: object, expected: bytes) -> None:
        obj = WithRequiredAny(data=data, name="test")
        result = impl.dump(WithRequiredAny, obj)
        assert result == expected

    @pytest.mark.parametrize(
        ("items", "expected"),
        [
            pytest.param([1, "two", 3.0, True], b'{"items":[1,"two",3.0,true],"name":"test"}', id="mixed_types"),
            pytest.param([{"a": 1}, {"b": 2}], b'{"items":[{"a":1},{"b":2}],"name":"test"}', id="nested_dicts"),
            pytest.param([], b'{"items":[],"name":"test"}', id="empty"),
            pytest.param([1, None, "three"], b'{"items":[1,null,"three"],"name":"test"}', id="with_none_element"),
            pytest.param([None, None, None], b'{"items":[null,null,null],"name":"test"}', id="all_none"),
        ],
    )
    def test_list_any(self, impl: Serializer, items: list, expected: bytes) -> None:
        obj = WithListAny(items=items, name="test")
        result = impl.dump(WithListAny, obj)
        assert result == expected

    @pytest.mark.parametrize(
        ("data", "expected"),
        [
            pytest.param(
                {"str": "hello", "int": 42, "float": 3.14, "bool": True},
                b'{"data":{"str":"hello","int":42,"float":3.14,"bool":true},"name":"test"}',
                id="mixed_values",
            ),
            pytest.param(
                {"nested": {"deep": [1, 2, 3]}}, b'{"data":{"nested":{"deep":[1,2,3]}},"name":"test"}', id="nested"
            ),
            pytest.param({}, b'{"data":{},"name":"test"}', id="empty"),
            pytest.param(
                {"key1": "value", "key2": None, "key3": 42},
                b'{"data":{"key1":"value","key2":null,"key3":42},"name":"test"}',
                id="with_none_value",
            ),
            pytest.param({"a": None, "b": None}, b'{"data":{"a":null,"b":null},"name":"test"}', id="all_none"),
        ],
    )
    def test_dict_any(self, impl: Serializer, data: dict, expected: bytes) -> None:
        obj = WithDictAny(data=data, name="test")
        result = impl.dump(WithDictAny, obj)
        assert result == expected

    @pytest.mark.parametrize(
        ("naming_case", "any_data", "expected"),
        [
            pytest.param(
                mr.CAMEL_CASE, {"key": "value"}, b'{"anyData":{"key":"value"},"fieldName":"test"}', id="camel_case"
            ),
            pytest.param(
                mr.CAPITAL_CAMEL_CASE, [1, 2, 3], b'{"AnyData":[1,2,3],"FieldName":"test"}', id="capital_camel_case"
            ),
        ],
    )
    def test_naming_case(self, impl: Serializer, naming_case: mr.NamingCase, any_data: object, expected: bytes) -> None:
        obj = WithAnyNamingCase(any_data=any_data, field_name="test")
        result = impl.dump(WithAnyNamingCase, obj, naming_case=naming_case)
        assert result == expected

    @pytest.mark.parametrize(
        ("none_value_handling", "expected"),
        [
            pytest.param(mr.NoneValueHandling.IGNORE, b'{"name":"test"}', id="ignore"),
            pytest.param(mr.NoneValueHandling.INCLUDE, b'{"data":null,"name":"test"}', id="include"),
        ],
    )
    def test_none_handling(self, impl: Serializer, none_value_handling: mr.NoneValueHandling, expected: bytes) -> None:
        obj = WithAnyField(data=None, name="test")
        result = impl.dump(WithAnyField, obj, none_value_handling=none_value_handling)
        assert result == expected

    @pytest.mark.parametrize(
        "value",
        [
            pytest.param(datetime.datetime(2024, 1, 1, 12, 0, 0), id="datetime"),
            pytest.param(datetime.date(2024, 1, 1), id="date"),
            pytest.param(uuid.UUID("12345678-1234-5678-1234-567812345678"), id="uuid"),
            pytest.param(decimal.Decimal("3.14"), id="decimal"),
        ],
    )
    def test_rejects_non_json_type(self, impl: Serializer, value: object) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.dump(ValueOf[Any], ValueOf[Any](value=value))
        assert exc.value.messages == {"value": ["Not a valid JSON-serializable value."]}

    def test_rejects_custom_object(self, impl: Serializer) -> None:
        @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
        class CustomObject:
            field: str

        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.dump(ValueOf[Any], ValueOf[Any](value=CustomObject(field="test")))
        assert exc.value.messages == {"value": ["Not a valid JSON-serializable value."]}

    @pytest.mark.parametrize(
        "value",
        [
            pytest.param({1, 2, 3}, id="set"),
            pytest.param((1, 2, 3), id="tuple"),
            pytest.param(b"bytes", id="bytes"),
            pytest.param({1: "value"}, id="dict_with_non_string_keys"),
            pytest.param([1, 2, datetime.datetime(2024, 1, 1, 12, 0, 0)], id="list_with_invalid_items"),
            pytest.param(
                {"nested": {"deeply": {"invalid": uuid.UUID("12345678-1234-5678-1234-567812345678")}}},
                id="nested_invalid_structures",
            ),
        ],
    )
    def test_rejects_invalid_structure(self, impl: Serializer, value: object) -> None:
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(ValueOf[Any], ValueOf[Any](value=value))


class TestAnyLoad:
    @pytest.mark.parametrize(
        ("data", "expected_data"),
        [
            pytest.param(b'{"data":"hello","name":"test"}', "hello", id="string"),
            pytest.param(b'{"data":42,"name":"test"}', 42, id="int"),
            pytest.param(b'{"data":3.14,"name":"test"}', 3.14, id="float"),
            pytest.param(b'{"data":true,"name":"test"}', True, id="bool"),
            pytest.param(b'{"data":null,"name":"test"}', None, id="none"),
            pytest.param(b'{"data":[1,2,3],"name":"test"}', [1, 2, 3], id="list"),
            pytest.param(b'{"data":{"key":"value"},"name":"test"}', {"key": "value"}, id="dict"),
            pytest.param(
                b'{"data":{"items":[1,2,{"nested":true}],"count":3},"name":"test"}',
                {"items": [1, 2, {"nested": True}], "count": 3},
                id="nested_structure",
            ),
        ],
    )
    def test_value(self, impl: Serializer, data: bytes, expected_data: object) -> None:
        result = impl.load(WithAnyField, data)
        assert result == WithAnyField(data=expected_data, name="test")

    @pytest.mark.parametrize(
        ("value", "id"),
        [
            pytest.param(9223372036854775808, "big_int"),
            pytest.param(2**100, "very_large_int"),
            pytest.param(-9223372036854775809, "big_negative_int"),
        ],
    )
    def test_big_int(self, impl: Serializer, value: int, id: str) -> None:
        data = f'{{"data": {value}, "name": "test"}}'.encode()
        result = impl.load(WithAnyField, data)
        assert result == WithAnyField(data=value, name="test")

    @pytest.mark.parametrize(
        ("data", "expected_data"),
        [
            pytest.param(b'{"data":"hello","name":"test"}', "hello", id="string"),
            pytest.param(b'{"data":{"key":"value"},"name":"test"}', {"key": "value"}, id="dict"),
            pytest.param(b'{"data":[1,"two",3.0],"name":"test"}', [1, "two", 3.0], id="list"),
        ],
    )
    def test_required(self, impl: Serializer, data: bytes, expected_data: object) -> None:
        result = impl.load(WithRequiredAny, data)
        assert result == WithRequiredAny(data=expected_data, name="test")

    @pytest.mark.parametrize(
        ("data", "expected_items"),
        [
            pytest.param(b'{"items":[1,"two",3.0,true],"name":"test"}', [1, "two", 3.0, True], id="mixed_types"),
            pytest.param(b'{"items":[{"a":1},{"b":2}],"name":"test"}', [{"a": 1}, {"b": 2}], id="nested_dicts"),
            pytest.param(b'{"items":[],"name":"test"}', [], id="empty"),
            pytest.param(b'{"items":[1,null,"three"],"name":"test"}', [1, None, "three"], id="with_none_element"),
            pytest.param(b'{"items":[null,null,null],"name":"test"}', [None, None, None], id="all_none"),
        ],
    )
    def test_list_any(self, impl: Serializer, data: bytes, expected_items: list) -> None:
        result = impl.load(WithListAny, data)
        assert result == WithListAny(items=expected_items, name="test")

    def test_list_any_with_big_int(self, impl: Serializer) -> None:
        big_value = 9223372036854775808
        data = f'{{"items": [1, {big_value}, "str"], "name": "test"}}'.encode()
        result = impl.load(WithListAny, data)
        assert result == WithListAny(items=[1, big_value, "str"], name="test")

    @pytest.mark.parametrize(
        ("data", "expected_data"),
        [
            pytest.param(
                b'{"data":{"str":"hello","int":42,"float":3.14,"bool":true},"name":"test"}',
                {"str": "hello", "int": 42, "float": 3.14, "bool": True},
                id="mixed_values",
            ),
            pytest.param(
                b'{"data":{"nested":{"deep":[1,2,3]}},"name":"test"}', {"nested": {"deep": [1, 2, 3]}}, id="nested"
            ),
            pytest.param(b'{"data":{},"name":"test"}', {}, id="empty"),
            pytest.param(
                b'{"data":{"key1":"value","key2":null,"key3":42},"name":"test"}',
                {"key1": "value", "key2": None, "key3": 42},
                id="with_none_value",
            ),
            pytest.param(b'{"data":{"a":null,"b":null},"name":"test"}', {"a": None, "b": None}, id="all_none"),
        ],
    )
    def test_dict_any(self, impl: Serializer, data: bytes, expected_data: dict) -> None:
        result = impl.load(WithDictAny, data)
        assert result == WithDictAny(data=expected_data, name="test")

    @pytest.mark.parametrize(
        ("naming_case", "data", "expected_any_data"),
        [
            pytest.param(
                mr.CAMEL_CASE, b'{"anyData":{"key":"value"},"fieldName":"test"}', {"key": "value"}, id="camel_case"
            ),
            pytest.param(
                mr.CAPITAL_CAMEL_CASE, b'{"AnyData":[1,2,3],"FieldName":"test"}', [1, 2, 3], id="capital_camel_case"
            ),
        ],
    )
    def test_naming_case(
        self, impl: Serializer, naming_case: mr.NamingCase, data: bytes, expected_any_data: object
    ) -> None:
        result = impl.load(WithAnyNamingCase, data, naming_case=naming_case)
        assert result == WithAnyNamingCase(any_data=expected_any_data, field_name="test")


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


class TestAnyEdgeCases:
    """Test Any type edge cases with boundary values, unicode, and nested structures."""

    def test_deeply_nested_structure_5_levels(self, impl: Serializer) -> None:
        deep_data = {"l1": {"l2": {"l3": {"l4": {"l5": "deep_value"}}}}}
        obj = WithAnyField(data=deep_data, name="test")
        result = impl.dump(WithAnyField, obj)
        loaded = impl.load(WithAnyField, result)
        assert loaded == obj

    def test_unicode_keys_and_values(self, impl: Serializer) -> None:
        unicode_data = {"ключ": "значение", "键": "值", "🔑": "🎉"}
        obj = WithAnyField(data=unicode_data, name="test")
        result = impl.dump(WithAnyField, obj)
        loaded = impl.load(WithAnyField, result)
        assert loaded == obj

    def test_special_json_chars(self, impl: Serializer) -> None:
        special_data = {"quoted": '"value"', "backslash": "back\\slash", "newline": "new\nline"}
        obj = WithAnyField(data=special_data, name="test")
        result = impl.dump(WithAnyField, obj)
        loaded = impl.load(WithAnyField, result)
        assert loaded == obj

    def test_empty_string_key(self, impl: Serializer) -> None:
        data = {"": "empty_key_value", "normal": "value"}
        obj = WithAnyField(data=data, name="test")
        result = impl.dump(WithAnyField, obj)
        loaded = impl.load(WithAnyField, result)
        assert loaded == obj

    def test_whitespace_string_values(self, impl: Serializer) -> None:
        data = {"tab": "\t", "newline": "\n", "spaces": "   ", "mixed": " \t\n "}
        obj = WithAnyField(data=data, name="test")
        result = impl.dump(WithAnyField, obj)
        loaded = impl.load(WithAnyField, result)
        assert loaded == obj

    def test_mixed_types_in_list(self, impl: Serializer) -> None:
        mixed_list = [1, "two", 3.0, True, False, None, {"nested": "dict"}, [1, 2, 3]]
        obj = WithListAny(items=mixed_list, name="test")
        result = impl.dump(WithListAny, obj)
        loaded = impl.load(WithListAny, result)
        assert loaded == obj

    def test_big_int_values(self, impl: Serializer) -> None:
        big_ints = {"big": 9223372036854775808, "bigger": 2**100, "negative": -(2**63) - 1}
        obj = WithAnyField(data=big_ints, name="test")
        result = impl.dump(WithAnyField, obj)
        loaded = impl.load(WithAnyField, result)
        assert loaded == obj

    def test_float_edge_values(self, impl: Serializer) -> None:
        float_data = {"small": 5e-324, "large": 1.7976931348623157e308, "negative": -1e-100}
        obj = WithAnyField(data=float_data, name="test")
        result = impl.dump(WithAnyField, obj)
        loaded = impl.load(WithAnyField, result)
        assert loaded == obj

    def test_very_long_string(self, impl: Serializer) -> None:
        long_string = "x" * 100000
        obj = WithAnyField(data=long_string, name="test")
        result = impl.dump(WithAnyField, obj)
        loaded = impl.load(WithAnyField, result)
        assert loaded == obj

    def test_1000_element_list(self, impl: Serializer) -> None:
        items = list(range(1000))
        obj = WithListAny(items=items, name="test")
        result = impl.dump(WithListAny, obj)
        loaded = impl.load(WithListAny, result)
        assert loaded == obj

    def test_large_nested_dict(self, impl: Serializer) -> None:
        large_dict = {f"key_{i}": {"nested": i, "values": [i, i + 1, i + 2]} for i in range(100)}
        obj = WithDictAny(data=large_dict, name="test")
        result = impl.dump(WithDictAny, obj)
        loaded = impl.load(WithDictAny, result)
        assert loaded == obj

    def test_boolean_values(self, impl: Serializer) -> None:
        bool_data = {"true_val": True, "false_val": False, "list": [True, False, True]}
        obj = WithAnyField(data=bool_data, name="test")
        result = impl.dump(WithAnyField, obj)
        loaded = impl.load(WithAnyField, result)
        assert loaded == obj

    def test_null_values_in_nested_structure(self, impl: Serializer) -> None:
        null_data = {"a": None, "b": {"c": None, "d": [None, None]}, "e": [{"f": None}]}
        obj = WithAnyField(data=null_data, name="test")
        result = impl.dump(WithAnyField, obj)
        loaded = impl.load(WithAnyField, result)
        assert loaded == obj

    def test_empty_containers(self, impl: Serializer) -> None:
        empty_data = {"empty_dict": {}, "empty_list": [], "nested_empty": {"inner": {}}}
        obj = WithAnyField(data=empty_data, name="test")
        result = impl.dump(WithAnyField, obj)
        loaded = impl.load(WithAnyField, result)
        assert loaded == obj

    def test_zero_values(self, impl: Serializer) -> None:
        zero_data = {"int_zero": 0, "float_zero": 0.0, "negative_zero": -0.0}
        obj = WithAnyField(data=zero_data, name="test")
        result = impl.dump(WithAnyField, obj)
        loaded = impl.load(WithAnyField, result)
        # Note: -0.0 becomes 0.0 after JSON serialization
        assert loaded.data["int_zero"] == 0
        assert loaded.data["float_zero"] == 0.0

    def test_emoji_string(self, impl: Serializer) -> None:
        emoji_data = "🎉🚀💻🌟✨🔥💯👨‍👩‍👧‍👦"
        obj = WithAnyField(data=emoji_data, name="test")
        result = impl.dump(WithAnyField, obj)
        loaded = impl.load(WithAnyField, result)
        assert loaded == obj

    def test_null_bytes_in_string(self, impl: Serializer) -> None:
        null_byte_data = "before\x00after"
        obj = WithAnyField(data=null_byte_data, name="test")
        result = impl.dump(WithAnyField, obj)
        loaded = impl.load(WithAnyField, result)
        assert loaded == obj
