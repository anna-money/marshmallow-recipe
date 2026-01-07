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
    def test_container_int(self, impl: Serializer) -> None:
        obj = GenericContainer[int](items=[1, 2, 3])
        result = impl.dump(GenericContainer[int], obj)
        assert result == b'{"items":[1,2,3]}'

    def test_container_str(self, impl: Serializer) -> None:
        obj = GenericContainer[str](items=["a", "b", "c"])
        result = impl.dump(GenericContainer[str], obj)
        assert result == b'{"items":["a","b","c"]}'

    def test_value_int(self, impl: Serializer) -> None:
        obj = GenericValue[int](value=42)
        result = impl.dump(GenericValue[int], obj)
        assert result == b'{"value":42}'

    def test_value_str(self, impl: Serializer) -> None:
        obj = GenericValue[str](value="hello")
        result = impl.dump(GenericValue[str], obj)
        assert result == b'{"value":"hello"}'

    def test_pair(self, impl: Serializer) -> None:
        obj = GenericPair[int, str](first=1, second="one")
        result = impl.dump(GenericPair[int, str], obj)
        assert result == b'{"first":1,"second":"one"}'

    def test_pair_reversed_types(self, impl: Serializer) -> None:
        obj = GenericPair[str, int](first="two", second=2)
        result = impl.dump(GenericPair[str, int], obj)
        assert result == b'{"first":"two","second":2}'

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

    def test_result_success(self, impl: Serializer) -> None:
        obj = GenericResult[str](success=True, value="result_data", error=None)
        result = impl.dump(GenericResult[str], obj)
        assert result == b'{"success":true,"value":"result_data"}'

    def test_result_error(self, impl: Serializer) -> None:
        obj = GenericResult[str](success=False, value=None, error="Something failed")
        result = impl.dump(GenericResult[str], obj)
        assert result == b'{"success":false,"error":"Something failed"}'

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

    def test_with_dict_int(self, impl: Serializer) -> None:
        obj = GenericWithDict[int](lookup={"a": 1, "b": 2, "c": 3})
        result = impl.dump(GenericWithDict[int], obj)
        assert result == b'{"lookup":{"a":1,"b":2,"c":3}}'

    def test_with_dict_str(self, impl: Serializer) -> None:
        obj = GenericWithDict[str](lookup={"x": "hello", "y": "world"})
        result = impl.dump(GenericWithDict[str], obj)
        assert result == b'{"lookup":{"x":"hello","y":"world"}}'

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

    def test_with_annotated_int(self, impl: Serializer) -> None:
        obj = GenericWithAnnotated[int](value=42, custom_name=100)
        result = impl.dump(GenericWithAnnotated[int], obj)
        assert result == b'{"value":42,"renamed_field":100}'

    def test_with_annotated_str(self, impl: Serializer) -> None:
        obj = GenericWithAnnotated[str](value="hello", custom_name="world")
        result = impl.dump(GenericWithAnnotated[str], obj)
        assert result == b'{"value":"hello","renamed_field":"world"}'


class TestGenericsLoad:
    def test_container_int(self, impl: Serializer) -> None:
        data = b'{"items":[10,20,30]}'
        result = impl.load(GenericContainer[int], data)
        assert result == GenericContainer[int](items=[10, 20, 30])

    def test_container_str(self, impl: Serializer) -> None:
        data = b'{"items":["x","y","z"]}'
        result = impl.load(GenericContainer[str], data)
        assert result == GenericContainer[str](items=["x", "y", "z"])

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

    def test_result_success(self, impl: Serializer) -> None:
        data = b'{"success":true,"value":"loaded_data"}'
        result = impl.load(GenericResult[str], data)
        assert result == GenericResult[str](success=True, value="loaded_data", error=None)

    def test_result_error(self, impl: Serializer) -> None:
        data = b'{"success":false,"error":"Failed to load"}'
        result = impl.load(GenericResult[str], data)
        assert result == GenericResult[str](success=False, value=None, error="Failed to load")

    def test_nested_generics(self, impl: Serializer) -> None:
        data = b'{"request_id":"req-456","result":{"success":true,"value":{"id":2,"name":"Alice","email":"alice@example.com"}}}'
        result = impl.load(GenericApiResponse[User], data)
        expected_user = User(id=2, name="Alice", email="alice@example.com")
        expected_result = GenericResult[User](success=True, value=expected_user, error=None)
        expected = GenericApiResponse[User](request_id="req-456", result=expected_result)
        assert result == expected

    def test_with_dict_int(self, impl: Serializer) -> None:
        data = b'{"lookup":{"one":1,"two":2}}'
        result = impl.load(GenericWithDict[int], data)
        assert result == GenericWithDict[int](lookup={"one": 1, "two": 2})

    def test_with_dict_user(self, impl: Serializer) -> None:
        data = b'{"lookup":{"admin":{"id":1,"name":"Admin","email":"admin@example.com"}}}'
        result = impl.load(GenericWithDict[User], data)
        expected = GenericWithDict[User](lookup={"admin": User(id=1, name="Admin", email="admin@example.com")})
        assert result == expected

    def test_with_set_int(self, impl: Serializer) -> None:
        data = b'{"unique_items":[4,5,6]}'
        result = impl.load(GenericWithSet[int], data)
        assert result == GenericWithSet[int](unique_items={4, 5, 6})

    def test_with_set_str(self, impl: Serializer) -> None:
        data = b'{"unique_items":["x","y","z"]}'
        result = impl.load(GenericWithSet[str], data)
        assert result == GenericWithSet[str](unique_items={"x", "y", "z"})

    def test_with_annotated_int(self, impl: Serializer) -> None:
        data = b'{"value":99,"renamed_field":200}'
        result = impl.load(GenericWithAnnotated[int], data)
        assert result == GenericWithAnnotated[int](value=99, custom_name=200)

    def test_with_annotated_str(self, impl: Serializer) -> None:
        data = b'{"value":"foo","renamed_field":"bar"}'
        result = impl.load(GenericWithAnnotated[str], data)
        assert result == GenericWithAnnotated[str](value="foo", custom_name="bar")
