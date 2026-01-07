import marshmallow_recipe as mr

from .conftest import Address, Person, Serializer, WithCustomName, WithSnakeCase


class TestNamingDump:
    def test_camel_case(self, impl: Serializer) -> None:
        obj = WithSnakeCase(first_name="John", last_name="Doe", email_address="john@example.com")
        result = impl.dump(WithSnakeCase, obj, naming_case=mr.CAMEL_CASE)
        expected = b'{"firstName":"John","lastName":"Doe","emailAddress":"john@example.com"}'
        assert result == expected

    def test_pascal_case(self, impl: Serializer) -> None:
        obj = WithSnakeCase(first_name="Bob", last_name="Brown", email_address="bob@example.com")
        result = impl.dump(WithSnakeCase, obj, naming_case=mr.CAPITAL_CAMEL_CASE)
        expected = b'{"FirstName":"Bob","LastName":"Brown","EmailAddress":"bob@example.com"}'
        assert result == expected

    def test_upper_snake_case(self, impl: Serializer) -> None:
        obj = WithSnakeCase(first_name="Tom", last_name="Jones", email_address="tom@example.com")
        result = impl.dump(WithSnakeCase, obj, naming_case=mr.UPPER_SNAKE_CASE)
        expected = b'{"FIRST_NAME":"Tom","LAST_NAME":"Jones","EMAIL_ADDRESS":"tom@example.com"}'
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
    def test_camel_case(self, impl: Serializer) -> None:
        data = b'{"firstName":"Jane","lastName":"Smith","emailAddress":"jane@example.com"}'
        result = impl.load(WithSnakeCase, data, naming_case=mr.CAMEL_CASE)
        assert result == WithSnakeCase(first_name="Jane", last_name="Smith", email_address="jane@example.com")

    def test_pascal_case(self, impl: Serializer) -> None:
        data = b'{"FirstName":"Alice","LastName":"Green","EmailAddress":"alice@example.com"}'
        result = impl.load(WithSnakeCase, data, naming_case=mr.CAPITAL_CAMEL_CASE)
        assert result == WithSnakeCase(first_name="Alice", last_name="Green", email_address="alice@example.com")

    def test_upper_snake_case(self, impl: Serializer) -> None:
        data = b'{"FIRST_NAME":"Sarah","LAST_NAME":"Wilson","EMAIL_ADDRESS":"sarah@example.com"}'
        result = impl.load(WithSnakeCase, data, naming_case=mr.UPPER_SNAKE_CASE)
        assert result == WithSnakeCase(first_name="Sarah", last_name="Wilson", email_address="sarah@example.com")

    def test_custom_name(self, impl: Serializer) -> None:
        data = b'{"id":456,"email":"user@example.com"}'
        result = impl.load(WithCustomName, data)
        assert result == WithCustomName(internal_id=456, user_email="user@example.com")

    def test_custom_name_with_naming_case(self, impl: Serializer) -> None:
        data = b'{"id":200,"email":"load@example.com"}'
        result = impl.load(WithCustomName, data, naming_case=mr.CAMEL_CASE)
        assert result == WithCustomName(internal_id=200, user_email="load@example.com")
