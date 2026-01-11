import pytest

import marshmallow_recipe as mr

from .conftest import Address, Person, Serializer, WithCustomName, WithSnakeCase


class TestNamingDump:
    @pytest.mark.parametrize(
        ("naming_case", "expected"),
        [
            (mr.CAMEL_CASE, b'{"firstName":"John","lastName":"Doe","emailAddress":"john@example.com"}'),
            (mr.CAPITAL_CAMEL_CASE, b'{"FirstName":"John","LastName":"Doe","EmailAddress":"john@example.com"}'),
            (mr.UPPER_SNAKE_CASE, b'{"FIRST_NAME":"John","LAST_NAME":"Doe","EMAIL_ADDRESS":"john@example.com"}'),
        ],
    )
    def test_naming_case(self, impl: Serializer, naming_case: mr.NamingCase, expected: bytes) -> None:
        obj = WithSnakeCase(first_name="John", last_name="Doe", email_address="john@example.com")
        result = impl.dump(WithSnakeCase, obj, naming_case=naming_case)
        assert result == expected

    def test_nested_camel_case(self, impl: Serializer) -> None:
        obj = Person(name="Test", age=25, address=Address(street="Main St", city="NYC", zip_code="10001"))
        result = impl.dump(Person, obj, naming_case=mr.CAMEL_CASE)
        expected = b'{"name":"Test","age":25,"address":{"street":"Main St","city":"NYC","zipCode":"10001"}}'
        assert result == expected

    def test_custom_name(self, impl: Serializer) -> None:
        obj = WithCustomName(internal_id=123, user_email="test@example.com")
        result = impl.dump(WithCustomName, obj)
        assert result == b'{"id":123,"email":"test@example.com"}'

    def test_custom_name_ignores_naming_case(self, impl: Serializer) -> None:
        obj = WithCustomName(internal_id=100, user_email="ignore@example.com")
        result = impl.dump(WithCustomName, obj, naming_case=mr.CAMEL_CASE)
        assert result == b'{"id":100,"email":"ignore@example.com"}'


class TestNamingLoad:
    @pytest.mark.parametrize(
        ("naming_case", "data"),
        [
            (mr.CAMEL_CASE, b'{"firstName":"Jane","lastName":"Smith","emailAddress":"jane@example.com"}'),
            (mr.CAPITAL_CAMEL_CASE, b'{"FirstName":"Jane","LastName":"Smith","EmailAddress":"jane@example.com"}'),
            (mr.UPPER_SNAKE_CASE, b'{"FIRST_NAME":"Jane","LAST_NAME":"Smith","EMAIL_ADDRESS":"jane@example.com"}'),
        ],
    )
    def test_naming_case(self, impl: Serializer, naming_case: mr.NamingCase, data: bytes) -> None:
        result = impl.load(WithSnakeCase, data, naming_case=naming_case)
        assert result == WithSnakeCase(first_name="Jane", last_name="Smith", email_address="jane@example.com")

    def test_custom_name(self, impl: Serializer) -> None:
        data = b'{"id":456,"email":"user@example.com"}'
        result = impl.load(WithCustomName, data)
        assert result == WithCustomName(internal_id=456, user_email="user@example.com")

    def test_custom_name_with_naming_case(self, impl: Serializer) -> None:
        data = b'{"id":200,"email":"load@example.com"}'
        result = impl.load(WithCustomName, data, naming_case=mr.CAMEL_CASE)
        assert result == WithCustomName(internal_id=200, user_email="load@example.com")
