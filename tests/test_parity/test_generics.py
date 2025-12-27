from typing import Any

from tests.test_parity.conftest import (
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
    User,
    Value1,
    Value2,
)


def test_basic_generic_int(impl: Any) -> None:
    obj = GenericContainer[int](items=[1, 2, 3])
    result = impl.dump(GenericContainer[int], obj)
    assert result == '{"items": [1, 2, 3]}'


def test_basic_generic_str(impl: Any) -> None:
    obj = GenericContainer[str](items=["a", "b", "c"])
    result = impl.dump(GenericContainer[str], obj)
    assert result == '{"items": ["a", "b", "c"]}'


def test_basic_generic_int_load(impl: Any) -> None:
    data = b'{"items": [10, 20, 30]}'
    result = impl.load(GenericContainer[int], data)
    assert result == GenericContainer[int](items=[10, 20, 30])


def test_basic_generic_str_load(impl: Any) -> None:
    data = b'{"items": ["x", "y", "z"]}'
    result = impl.load(GenericContainer[str], data)
    assert result == GenericContainer[str](items=["x", "y", "z"])


def test_generic_value_int(impl: Any) -> None:
    obj = GenericValue[int](value=42)
    result = impl.dump(GenericValue[int], obj)
    assert result == '{"value": 42}'


def test_generic_value_str(impl: Any) -> None:
    obj = GenericValue[str](value="hello")
    result = impl.dump(GenericValue[str], obj)
    assert result == '{"value": "hello"}'


def test_generic_value_load(impl: Any) -> None:
    data = b'{"value": 100}'
    result = impl.load(GenericValue[int], data)
    assert result == GenericValue[int](value=100)


def test_generic_pair(impl: Any) -> None:
    obj = GenericPair[int, str](first=1, second="one")
    result = impl.dump(GenericPair[int, str], obj)
    assert result == '{"first": 1, "second": "one"}'


def test_generic_pair_load(impl: Any) -> None:
    data = b'{"first": 99, "second": "test"}'
    result = impl.load(GenericPair[int, str], data)
    assert result == GenericPair[int, str](first=99, second="test")


def test_generic_pair_reversed_types(impl: Any) -> None:
    obj = GenericPair[str, int](first="two", second=2)
    result = impl.dump(GenericPair[str, int], obj)
    assert result == '{"first": "two", "second": 2}'


def test_generic_child_with_concrete_parent_dump(impl: Any) -> None:
    obj = GenericChildWithConcreteParent[str](t1=1, t2="test")
    result = impl.dump(GenericChildWithConcreteParent[str], obj)
    assert result == '{"t1": 1, "t2": "test"}'


def test_generic_child_with_concrete_parent_load(impl: Any) -> None:
    data = b'{"t1": 5, "t2": "value"}'
    result = impl.load(GenericChildWithConcreteParent[str], data)
    assert result == GenericChildWithConcreteParent[str](t1=5, t2="value")


def test_non_generic_child_from_generic_parent_dump(impl: Any) -> None:
    obj = NonGenericChildFromGenericParent(t1="inherited", extra="child")
    result = impl.dump(NonGenericChildFromGenericParent, obj)
    assert result == '{"extra": "child", "t1": "inherited"}'


def test_non_generic_child_from_generic_parent_load(impl: Any) -> None:
    data = b'{"t1": "parent_value", "extra": "child_value"}'
    result = impl.load(NonGenericChildFromGenericParent, data)
    assert result == NonGenericChildFromGenericParent(t1="parent_value", extra="child_value")


def test_generic_with_iterable_dump(impl: Any) -> None:
    obj = GenericWithIterable[int](value=Value1(v1="test"), iterable=[1, 2, 3])
    result = impl.dump(GenericWithIterable[int], obj)
    assert result == '{"iterable": [1, 2, 3], "value": {"v1": "test"}}'


def test_generic_with_iterable_load(impl: Any) -> None:
    data = b'{"value": {"v1": "loaded"}, "iterable": [4, 5, 6]}'
    result = impl.load(GenericWithIterable[int], data)
    assert result == GenericWithIterable[int](value=Value1(v1="loaded"), iterable=[4, 5, 6])


def test_generic_with_field_override_dump(impl: Any) -> None:
    obj = GenericWithFieldOverride[Value2, int](value=Value2(v1="base", v2="derived"), iterable={3, 4, 5})
    result = impl.dump(GenericWithFieldOverride[Value2, int], obj)
    assert result == '{"iterable": [3, 4, 5], "value": {"v1": "base", "v2": "derived"}}'


def test_generic_with_field_override_load(impl: Any) -> None:
    data = b'{"value": {"v1": "a", "v2": "b"}, "iterable": [7, 8, 9]}'
    result = impl.load(GenericWithFieldOverride[Value2, int], data)
    assert result == GenericWithFieldOverride[Value2, int](value=Value2(v1="a", v2="b"), iterable={7, 8, 9})


def test_generic_result_success(impl: Any) -> None:
    obj = GenericResult[str](success=True, value="result_data", error=None)
    result = impl.dump(GenericResult[str], obj)
    assert result == '{"success": true, "value": "result_data"}'


def test_generic_result_success_load(impl: Any) -> None:
    data = b'{"success": true, "value": "loaded_data"}'
    result = impl.load(GenericResult[str], data)
    assert result == GenericResult[str](success=True, value="loaded_data", error=None)


def test_generic_result_error(impl: Any) -> None:
    obj = GenericResult[str](success=False, value=None, error="Something failed")
    result = impl.dump(GenericResult[str], obj)
    assert result == '{"error": "Something failed", "success": false}'


def test_generic_result_error_load(impl: Any) -> None:
    data = b'{"success": false, "error": "Failed to load"}'
    result = impl.load(GenericResult[str], data)
    assert result == GenericResult[str](success=False, value=None, error="Failed to load")


def test_nested_generics_dump(impl: Any) -> None:
    user = User(id=1, name="John", email="john@example.com")
    result_obj = GenericResult[User](success=True, value=user, error=None)
    response = GenericApiResponse[User](request_id="req-123", result=result_obj)
    result = impl.dump(GenericApiResponse[User], response)
    assert (
        result
        == '{"request_id": "req-123", "result": {"success": true, "value": {"email": "john@example.com", "id": 1, "name": "John"}}}'
    )


def test_nested_generics_load(impl: Any) -> None:
    data = b'{"request_id": "req-456", "result": {"success": true, "value": {"id": 2, "name": "Alice", "email": "alice@example.com"}}}'
    result = impl.load(GenericApiResponse[User], data)
    expected_user = User(id=2, name="Alice", email="alice@example.com")
    expected_result = GenericResult[User](success=True, value=expected_user, error=None)
    expected = GenericApiResponse[User](request_id="req-456", result=expected_result)
    assert result == expected


def test_nested_generics_with_error(impl: Any) -> None:
    result_obj = GenericResult[User](success=False, value=None, error="User not found")
    response = GenericApiResponse[User](request_id="req-789", result=result_obj)
    result = impl.dump(GenericApiResponse[User], response)
    assert result == '{"request_id": "req-789", "result": {"error": "User not found", "success": false}}'


def test_generic_container_roundtrip(impl: Any) -> None:
    obj = GenericContainer[str](items=["round", "trip"])
    dumped = impl.dump(GenericContainer[str], obj)
    loaded = impl.load(GenericContainer[str], dumped.encode() if isinstance(dumped, str) else dumped)
    assert loaded == obj


def test_generic_pair_roundtrip(impl: Any) -> None:
    obj = GenericPair[int, str](first=42, second="answer")
    dumped = impl.dump(GenericPair[int, str], obj)
    loaded = impl.load(GenericPair[int, str], dumped.encode() if isinstance(dumped, str) else dumped)
    assert loaded == obj


def test_nested_generic_roundtrip(impl: Any) -> None:
    user = User(id=99, name="Bob", email="bob@example.com")
    result_obj = GenericResult[User](success=True, value=user, error=None)
    response = GenericApiResponse[User](request_id="req-999", result=result_obj)
    dumped = impl.dump(GenericApiResponse[User], response)
    loaded = impl.load(GenericApiResponse[User], dumped.encode() if isinstance(dumped, str) else dumped)
    assert loaded == response


def test_generic_with_dict_int_dump(impl: Any) -> None:
    obj = GenericWithDict[int](lookup={"a": 1, "b": 2, "c": 3})
    result = impl.dump(GenericWithDict[int], obj)
    assert result == '{"lookup": {"a": 1, "b": 2, "c": 3}}'


def test_generic_with_dict_str_dump(impl: Any) -> None:
    obj = GenericWithDict[str](lookup={"x": "hello", "y": "world"})
    result = impl.dump(GenericWithDict[str], obj)
    assert result == '{"lookup": {"x": "hello", "y": "world"}}'


def test_generic_with_dict_int_load(impl: Any) -> None:
    data = b'{"lookup": {"one": 1, "two": 2}}'
    result = impl.load(GenericWithDict[int], data)
    assert result == GenericWithDict[int](lookup={"one": 1, "two": 2})


def test_generic_with_dict_user_dump(impl: Any) -> None:
    users = {
        "admin": User(id=1, name="Admin", email="admin@example.com"),
        "user": User(id=2, name="User", email="user@example.com"),
    }
    obj = GenericWithDict[User](lookup=users)
    result = impl.dump(GenericWithDict[User], obj)
    assert (
        result
        == '{"lookup": {"admin": {"email": "admin@example.com", "id": 1, "name": "Admin"}, "user": {"email": "user@example.com", "id": 2, "name": "User"}}}'
    )


def test_generic_with_dict_user_load(impl: Any) -> None:
    data = b'{"lookup": {"admin": {"id": 1, "name": "Admin", "email": "admin@example.com"}}}'
    result = impl.load(GenericWithDict[User], data)
    expected = GenericWithDict[User](lookup={"admin": User(id=1, name="Admin", email="admin@example.com")})
    assert result == expected


def test_generic_with_set_int_dump(impl: Any) -> None:
    obj = GenericWithSet[int](unique_items={1, 2, 3})
    result = impl.dump(GenericWithSet[int], obj)
    assert result == '{"unique_items": [1, 2, 3]}'


def test_generic_with_set_str_dump(impl: Any) -> None:
    obj = GenericWithSet[str](unique_items={"a", "b", "c"})
    result = impl.dump(GenericWithSet[str], obj)
    assert result in [
        '{"unique_items": ["a", "b", "c"]}',
        '{"unique_items": ["a", "c", "b"]}',
        '{"unique_items": ["b", "a", "c"]}',
        '{"unique_items": ["b", "c", "a"]}',
        '{"unique_items": ["c", "a", "b"]}',
        '{"unique_items": ["c", "b", "a"]}',
    ]


def test_generic_with_set_int_load(impl: Any) -> None:
    data = b'{"unique_items": [4, 5, 6]}'
    result = impl.load(GenericWithSet[int], data)
    assert result == GenericWithSet[int](unique_items={4, 5, 6})


def test_generic_with_set_str_load(impl: Any) -> None:
    data = b'{"unique_items": ["x", "y", "z"]}'
    result = impl.load(GenericWithSet[str], data)
    assert result == GenericWithSet[str](unique_items={"x", "y", "z"})


def test_generic_with_annotated_int_dump(impl: Any) -> None:
    obj = GenericWithAnnotated[int](value=42, custom_name=100)
    result = impl.dump(GenericWithAnnotated[int], obj)
    assert result == '{"renamed_field": 100, "value": 42}'


def test_generic_with_annotated_str_dump(impl: Any) -> None:
    obj = GenericWithAnnotated[str](value="hello", custom_name="world")
    result = impl.dump(GenericWithAnnotated[str], obj)
    assert result == '{"renamed_field": "world", "value": "hello"}'


def test_generic_with_annotated_int_load(impl: Any) -> None:
    data = b'{"value": 99, "renamed_field": 200}'
    result = impl.load(GenericWithAnnotated[int], data)
    assert result == GenericWithAnnotated[int](value=99, custom_name=200)


def test_generic_with_annotated_str_load(impl: Any) -> None:
    data = b'{"value": "foo", "renamed_field": "bar"}'
    result = impl.load(GenericWithAnnotated[str], data)
    assert result == GenericWithAnnotated[str](value="foo", custom_name="bar")
