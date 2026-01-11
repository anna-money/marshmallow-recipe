import json

import pytest

from .conftest import (
    GenericApiResponse,
    GenericChildWithConcreteParent,
    GenericContainer,
    GenericPair,
    GenericResult,
    GenericValue,
    GenericWithAnnotated,
    GenericWithDict,
    GenericWithFieldOverride,
    GenericWithIterable,
    GenericWithSet,
    NonGenericChildFromGenericParent,
    Serializer,
    User,
    Value1,
    Value2,
)


class TestGenericsDump:
    @pytest.mark.parametrize(
        ("type_arg", "items", "expected"),
        [(int, [1, 2, 3], b'{"items":[1,2,3]}'), (str, ["a", "b", "c"], b'{"items":["a","b","c"]}')],
    )
    def test_container(self, impl: Serializer, type_arg: type, items: list, expected: bytes) -> None:
        obj = GenericContainer[type_arg](items=items)
        result = impl.dump(GenericContainer[type_arg], obj)
        assert result == expected

    def test_container_empty(self, impl: Serializer) -> None:
        obj = GenericContainer[int](items=[])
        result = impl.dump(GenericContainer[int], obj)
        assert result == b'{"items":[]}'

    def test_container_single(self, impl: Serializer) -> None:
        obj = GenericContainer[str](items=["only"])
        result = impl.dump(GenericContainer[str], obj)
        assert result == b'{"items":["only"]}'

    def test_container_large(self, impl: Serializer) -> None:
        items = list(range(100))
        obj = GenericContainer[int](items=items)
        result = impl.dump(GenericContainer[int], obj)
        parsed = json.loads(result)
        assert parsed["items"] == items

    @pytest.mark.parametrize(
        ("type_arg", "value", "expected"), [(int, 42, b'{"value":42}'), (str, "hello", b'{"value":"hello"}')]
    )
    def test_value(self, impl: Serializer, type_arg: type, value: object, expected: bytes) -> None:
        obj = GenericValue[type_arg](value=value)
        result = impl.dump(GenericValue[type_arg], obj)
        assert result == expected

    @pytest.mark.parametrize(
        ("first_type", "second_type", "first", "second", "expected"),
        [(int, str, 1, "one", b'{"first":1,"second":"one"}'), (str, int, "two", 2, b'{"first":"two","second":2}')],
    )
    def test_pair(
        self, impl: Serializer, first_type: type, second_type: type, first: object, second: object, expected: bytes
    ) -> None:
        obj = GenericPair[first_type, second_type](first=first, second=second)
        result = impl.dump(GenericPair[first_type, second_type], obj)
        assert result == expected

    def test_child_with_concrete_parent(self, impl: Serializer) -> None:
        obj = GenericChildWithConcreteParent[str](t1=1, t2="test")
        result = impl.dump(GenericChildWithConcreteParent[str], obj)
        assert result == b'{"t1":1,"t2":"test"}'

    def test_non_generic_child_from_generic_parent(self, impl: Serializer) -> None:
        obj = NonGenericChildFromGenericParent(t1="inherited", extra="child")
        result = impl.dump(NonGenericChildFromGenericParent, obj)
        assert result == b'{"t1":"inherited","extra":"child"}'

    def test_with_iterable(self, impl: Serializer) -> None:
        obj = GenericWithIterable[int](value=Value1(v1="test"), iterable=[1, 2, 3])
        result = impl.dump(GenericWithIterable[int], obj)
        assert result == b'{"value":{"v1":"test"},"iterable":[1,2,3]}'

    def test_with_field_override(self, impl: Serializer) -> None:
        obj = GenericWithFieldOverride[Value2, int](value=Value2(v1="base", v2="derived"), iterable={3, 4, 5})
        result = impl.dump(GenericWithFieldOverride[Value2, int], obj)
        assert result == b'{"value":{"v1":"base","v2":"derived"},"iterable":[3,4,5]}'

    @pytest.mark.parametrize(
        ("success", "value", "error", "expected"),
        [
            (True, "result_data", None, b'{"success":true,"value":"result_data"}'),
            (False, None, "Something failed", b'{"success":false,"error":"Something failed"}'),
        ],
    )
    def test_result(
        self, impl: Serializer, success: bool, value: str | None, error: str | None, expected: bytes
    ) -> None:
        obj = GenericResult[str](success=success, value=value, error=error)
        result = impl.dump(GenericResult[str], obj)
        assert result == expected

    def test_nested_generics(self, impl: Serializer) -> None:
        user = User(id=1, name="John", email="john@example.com")
        result_obj = GenericResult[User](success=True, value=user, error=None)
        response = GenericApiResponse[User](request_id="req-123", result=result_obj)
        result = impl.dump(GenericApiResponse[User], response)
        assert (
            result
            == b'{"request_id":"req-123","result":{"success":true,"value":{"id":1,"name":"John","email":"john@example.com"}}}'
        )

    def test_nested_generics_with_error(self, impl: Serializer) -> None:
        result_obj = GenericResult[User](success=False, value=None, error="User not found")
        response = GenericApiResponse[User](request_id="req-789", result=result_obj)
        result = impl.dump(GenericApiResponse[User], response)
        assert result == b'{"request_id":"req-789","result":{"success":false,"error":"User not found"}}'

    @pytest.mark.parametrize(
        ("type_arg", "lookup", "expected"),
        [
            (int, {"a": 1, "b": 2, "c": 3}, b'{"lookup":{"a":1,"b":2,"c":3}}'),
            (str, {"x": "hello", "y": "world"}, b'{"lookup":{"x":"hello","y":"world"}}'),
        ],
    )
    def test_with_dict(self, impl: Serializer, type_arg: type, lookup: dict, expected: bytes) -> None:
        obj = GenericWithDict[type_arg](lookup=lookup)
        result = impl.dump(GenericWithDict[type_arg], obj)
        assert result == expected

    def test_with_dict_user(self, impl: Serializer) -> None:
        users = {
            "admin": User(id=1, name="Admin", email="admin@example.com"),
            "user": User(id=2, name="User", email="user@example.com"),
        }
        obj = GenericWithDict[User](lookup=users)
        result = impl.dump(GenericWithDict[User], obj)
        assert (
            result
            == b'{"lookup":{"admin":{"id":1,"name":"Admin","email":"admin@example.com"},"user":{"id":2,"name":"User","email":"user@example.com"}}}'
        )

    def test_with_set_int(self, impl: Serializer) -> None:
        obj = GenericWithSet[int](unique_items={1, 2, 3})
        result = impl.dump(GenericWithSet[int], obj)
        assert result == b'{"unique_items":[1,2,3]}'

    def test_with_set_str(self, impl: Serializer) -> None:
        obj = GenericWithSet[str](unique_items={"a", "b", "c"})
        result = impl.dump(GenericWithSet[str], obj)
        assert result in [
            b'{"unique_items":["a","b","c"]}',
            b'{"unique_items":["a","c","b"]}',
            b'{"unique_items":["b","a","c"]}',
            b'{"unique_items":["b","c","a"]}',
            b'{"unique_items":["c","a","b"]}',
            b'{"unique_items":["c","b","a"]}',
        ]

    @pytest.mark.parametrize(
        ("type_arg", "value", "custom_name", "expected"),
        [
            (int, 42, 100, b'{"value":42,"renamed_field":100}'),
            (str, "hello", "world", b'{"value":"hello","renamed_field":"world"}'),
        ],
    )
    def test_with_annotated(
        self, impl: Serializer, type_arg: type, value: object, custom_name: object, expected: bytes
    ) -> None:
        obj = GenericWithAnnotated[type_arg](value=value, custom_name=custom_name)
        result = impl.dump(GenericWithAnnotated[type_arg], obj)
        assert result == expected


class TestGenericsLoad:
    @pytest.mark.parametrize(
        ("type_arg", "data", "expected_items"),
        [(int, b'{"items":[10,20,30]}', [10, 20, 30]), (str, b'{"items":["x","y","z"]}', ["x", "y", "z"])],
    )
    def test_container(self, impl: Serializer, type_arg: type, data: bytes, expected_items: list) -> None:
        result = impl.load(GenericContainer[type_arg], data)
        assert result == GenericContainer[type_arg](items=expected_items)

    def test_container_empty(self, impl: Serializer) -> None:
        data = b'{"items":[]}'
        result = impl.load(GenericContainer[int], data)
        assert result == GenericContainer[int](items=[])

    def test_container_single(self, impl: Serializer) -> None:
        data = b'{"items":["only"]}'
        result = impl.load(GenericContainer[str], data)
        assert result == GenericContainer[str](items=["only"])

    def test_container_large(self, impl: Serializer) -> None:
        items = list(range(100))
        data = json.dumps({"items": items}).encode()
        result = impl.load(GenericContainer[int], data)
        assert result == GenericContainer[int](items=items)

    def test_value(self, impl: Serializer) -> None:
        data = b'{"value":100}'
        result = impl.load(GenericValue[int], data)
        assert result == GenericValue[int](value=100)

    def test_pair(self, impl: Serializer) -> None:
        data = b'{"first":99,"second":"test"}'
        result = impl.load(GenericPair[int, str], data)
        assert result == GenericPair[int, str](first=99, second="test")

    def test_child_with_concrete_parent(self, impl: Serializer) -> None:
        data = b'{"t1":5,"t2":"value"}'
        result = impl.load(GenericChildWithConcreteParent[str], data)
        assert result == GenericChildWithConcreteParent[str](t1=5, t2="value")

    def test_non_generic_child_from_generic_parent(self, impl: Serializer) -> None:
        data = b'{"t1":"parent_value","extra":"child_value"}'
        result = impl.load(NonGenericChildFromGenericParent, data)
        assert result == NonGenericChildFromGenericParent(t1="parent_value", extra="child_value")

    def test_with_iterable(self, impl: Serializer) -> None:
        data = b'{"value":{"v1":"loaded"},"iterable":[4,5,6]}'
        result = impl.load(GenericWithIterable[int], data)
        assert result == GenericWithIterable[int](value=Value1(v1="loaded"), iterable=[4, 5, 6])

    def test_with_field_override(self, impl: Serializer) -> None:
        data = b'{"value":{"v1":"a","v2":"b"},"iterable":[7,8,9]}'
        result = impl.load(GenericWithFieldOverride[Value2, int], data)
        assert result == GenericWithFieldOverride[Value2, int](value=Value2(v1="a", v2="b"), iterable={7, 8, 9})

    @pytest.mark.parametrize(
        ("data", "success", "value", "error"),
        [
            (b'{"success":true,"value":"loaded_data"}', True, "loaded_data", None),
            (b'{"success":false,"error":"Failed to load"}', False, None, "Failed to load"),
        ],
    )
    def test_result(self, impl: Serializer, data: bytes, success: bool, value: str | None, error: str | None) -> None:
        result = impl.load(GenericResult[str], data)
        assert result == GenericResult[str](success=success, value=value, error=error)

    def test_nested_generics(self, impl: Serializer) -> None:
        data = b'{"request_id":"req-456","result":{"success":true,"value":{"id":2,"name":"Alice","email":"alice@example.com"}}}'
        result = impl.load(GenericApiResponse[User], data)
        expected_user = User(id=2, name="Alice", email="alice@example.com")
        expected_result = GenericResult[User](success=True, value=expected_user, error=None)
        expected = GenericApiResponse[User](request_id="req-456", result=expected_result)
        assert result == expected

    @pytest.mark.parametrize(
        ("type_arg", "data", "expected_lookup"), [(int, b'{"lookup":{"one":1,"two":2}}', {"one": 1, "two": 2})]
    )
    def test_with_dict(self, impl: Serializer, type_arg: type, data: bytes, expected_lookup: dict) -> None:
        result = impl.load(GenericWithDict[type_arg], data)
        assert result == GenericWithDict[type_arg](lookup=expected_lookup)

    def test_with_dict_user(self, impl: Serializer) -> None:
        data = b'{"lookup":{"admin":{"id":1,"name":"Admin","email":"admin@example.com"}}}'
        result = impl.load(GenericWithDict[User], data)
        expected = GenericWithDict[User](lookup={"admin": User(id=1, name="Admin", email="admin@example.com")})
        assert result == expected

    @pytest.mark.parametrize(
        ("type_arg", "data", "expected_items"),
        [(int, b'{"unique_items":[4,5,6]}', {4, 5, 6}), (str, b'{"unique_items":["x","y","z"]}', {"x", "y", "z"})],
    )
    def test_with_set(self, impl: Serializer, type_arg: type, data: bytes, expected_items: set) -> None:
        result = impl.load(GenericWithSet[type_arg], data)
        assert result == GenericWithSet[type_arg](unique_items=expected_items)

    @pytest.mark.parametrize(
        ("type_arg", "data", "expected_value", "expected_custom_name"),
        [
            (int, b'{"value":99,"renamed_field":200}', 99, 200),
            (str, b'{"value":"foo","renamed_field":"bar"}', "foo", "bar"),
        ],
    )
    def test_with_annotated(
        self, impl: Serializer, type_arg: type, data: bytes, expected_value: object, expected_custom_name: object
    ) -> None:
        result = impl.load(GenericWithAnnotated[type_arg], data)
        assert result == GenericWithAnnotated[type_arg](value=expected_value, custom_name=expected_custom_name)


class TestGenericsEdgeCases:
    """Test generics edge cases with complex nested types and boundary values."""

    def test_container_with_big_ints(self, impl: Serializer) -> None:
        big_vals = [9223372036854775808, -(2**100), 2**127]
        obj = GenericContainer[int](items=big_vals)
        result = impl.dump(GenericContainer[int], obj)
        loaded = impl.load(GenericContainer[int], result)
        assert loaded.items == big_vals

    def test_container_with_unicode(self, impl: Serializer) -> None:
        unicode_vals = ["Привет", "你好", "🎉🎊", "مرحبا"]
        obj = GenericContainer[str](items=unicode_vals)
        result = impl.dump(GenericContainer[str], obj)
        loaded = impl.load(GenericContainer[str], result)
        assert loaded.items == unicode_vals

    def test_container_with_special_chars(self, impl: Serializer) -> None:
        special_vals = ['"quoted"', "back\\slash", "new\nline"]
        obj = GenericContainer[str](items=special_vals)
        result = impl.dump(GenericContainer[str], obj)
        loaded = impl.load(GenericContainer[str], result)
        assert loaded.items == special_vals

    def test_container_1000_items(self, impl: Serializer) -> None:
        items = list(range(1000))
        obj = GenericContainer[int](items=items)
        result = impl.dump(GenericContainer[int], obj)
        loaded = impl.load(GenericContainer[int], result)
        assert loaded.items == items

    def test_nested_generic_container(self, impl: Serializer) -> None:
        obj = GenericContainer[list[list[int]]](items=[[[1, 2], [3, 4]], [[5, 6], [7, 8]]])
        result = impl.dump(GenericContainer[list[list[int]]], obj)
        loaded = impl.load(GenericContainer[list[list[int]]], result)
        assert loaded == obj

    def test_value_with_none(self, impl: Serializer) -> None:
        obj = GenericValue[int | None](value=None)
        result = impl.dump(GenericValue[int | None], obj)
        # None values are omitted by default
        assert result == b"{}"

    def test_pair_with_same_types(self, impl: Serializer) -> None:
        obj = GenericPair[str, str](first="hello", second="world")
        result = impl.dump(GenericPair[str, str], obj)
        assert result == b'{"first":"hello","second":"world"}'

    def test_pair_with_complex_types(self, impl: Serializer) -> None:
        obj = GenericPair[list[int], dict[str, str]](first=[1, 2, 3], second={"a": "b"})
        result = impl.dump(GenericPair[list[int], dict[str, str]], obj)
        loaded = impl.load(GenericPair[list[int], dict[str, str]], result)
        assert loaded == obj

    def test_result_with_nested_user(self, impl: Serializer) -> None:
        user = User(id=2**63, name="Тест", email="test@example.com")
        obj = GenericResult[User](success=True, value=user, error=None)
        result = impl.dump(GenericResult[User], obj)
        loaded = impl.load(GenericResult[User], result)
        assert loaded == obj

    def test_dict_with_empty_key(self, impl: Serializer) -> None:
        obj = GenericWithDict[int](lookup={"": 42, "a": 1})
        result = impl.dump(GenericWithDict[int], obj)
        loaded = impl.load(GenericWithDict[int], result)
        assert loaded == obj

    def test_set_with_big_ints(self, impl: Serializer) -> None:
        big_vals = {9223372036854775808, 2**100, -(2**99)}
        obj = GenericWithSet[int](unique_items=big_vals)
        result = impl.dump(GenericWithSet[int], obj)
        loaded = impl.load(GenericWithSet[int], result)
        assert loaded.unique_items == big_vals
