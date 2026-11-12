import decimal
from typing import Any

import pytest

import marshmallow_recipe as mr

from .conftest import (
    Address,
    Company,
    Department,
    GenericPair,
    NonGenericChildFromGenericParent,
    Person,
    Serializer,
    SimpleTypes,
    Value2,
    ValueOf,
    WithDecimal,
    WithOptional,
    WithSnakeCase,
)


@pytest.fixture
def skip_if_no_dump_without_cls(impl: Serializer) -> None:
    if not impl.supports_dump_without_cls:
        pytest.skip("dump without cls not supported")


@pytest.mark.usefixtures("skip_if_no_dump_without_cls")
class TestInferredTypeDump:
    @pytest.mark.parametrize(
        ("obj", "kwargs", "expected"),
        [
            (SimpleTypes(name="John", age=30), {}, b'{"name":"John","age":30}'),
            (
                Company(
                    name="Acme",
                    department=Department(
                        name="R&D",
                        head=Person(
                            name="Jane", age=40, address=Address(street="Main St", city="London", zip_code="12345")
                        ),
                    ),
                ),
                {},
                b'{"name":"Acme","department":{"name":"R&D","head":{"name":"Jane","age":40,'
                b'"address":{"street":"Main St","city":"London","zip_code":"12345"}}}}',
            ),
            (Value2(v1="a", v2="b"), {}, b'{"v1":"a","v2":"b"}'),
            (NonGenericChildFromGenericParent(t1="a", extra="b"), {}, b'{"t1":"a","extra":"b"}'),
            (
                WithSnakeCase(first_name="John", last_name="Doe", email_address="john@example.com"),
                {"naming_case": mr.CAMEL_CASE},
                b'{"firstName":"John","lastName":"Doe","emailAddress":"john@example.com"}',
            ),
            (
                WithOptional(required="x"),
                {"none_value_handling": mr.NoneValueHandling.INCLUDE},
                b'{"required":"x","optional_int":null,"optional_str":null}',
            ),
            (WithDecimal(value=decimal.Decimal("1.234")), {"decimal_places": 3}, b'{"value":"1.234"}'),
        ],
    )
    def test_dataclass(self, impl: Serializer, obj: Any, kwargs: dict[str, Any], expected: bytes) -> None:
        result = impl.dump_without_cls(obj, **kwargs)
        assert result == expected

    @pytest.mark.parametrize("obj", [ValueOf[int](value=1), GenericPair[int, str](first=1, second="a")])
    def test_generic_dataclass(self, impl: Serializer, obj: Any) -> None:
        with pytest.raises(ValueError) as exc_info:
            impl.dump_without_cls(obj)
        assert exc_info.value.args == (f"Explicit cls required for unsubscripted type {type(obj)}",)

    @pytest.mark.parametrize(
        "obj", [42, "John", None, [SimpleTypes(name="John", age=30)], {"name": "John"}, SimpleTypes]
    )
    def test_not_dataclass(self, impl: Serializer, obj: Any) -> None:
        with pytest.raises(ValueError) as exc_info:
            impl.dump_without_cls(obj)
        assert exc_info.value.args == (f"{type(obj)} is not a dataclass",)

    def test_not_dataclass_after_explicit_dump(self, impl: Serializer) -> None:
        if not impl.supports_root_non_dataclasses:
            pytest.skip("root non-dataclasses not supported")
        assert impl.dump(int, 42) == b"42"
        with pytest.raises(ValueError) as exc_info:
            impl.dump_without_cls(42)
        assert exc_info.value.args == ("<class 'int'> is not a dataclass",)
