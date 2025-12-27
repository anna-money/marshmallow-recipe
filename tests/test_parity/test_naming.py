from typing import Any

import marshmallow_recipe as mr
from tests.test_parity.conftest import Address, Person, WithSnakeCase


def test_camel_case_dump(impl: Any) -> None:
    obj = WithSnakeCase(first_name="John", last_name="Doe", email_address="john@example.com")
    result = impl.dump(WithSnakeCase, obj, naming_case=mr.CAMEL_CASE)
    expected = '{"emailAddress": "john@example.com", "firstName": "John", "lastName": "Doe"}'
    assert result == expected


def test_camel_case_load(impl: Any) -> None:
    data = b'{"firstName": "Jane", "lastName": "Smith", "emailAddress": "jane@example.com"}'
    result = impl.load(WithSnakeCase, data, naming_case=mr.CAMEL_CASE)
    assert result == WithSnakeCase(first_name="Jane", last_name="Smith", email_address="jane@example.com")


def test_pascal_case_dump(impl: Any) -> None:
    obj = WithSnakeCase(first_name="Bob", last_name="Brown", email_address="bob@example.com")
    result = impl.dump(WithSnakeCase, obj, naming_case=mr.CAPITAL_CAMEL_CASE)
    expected = '{"EmailAddress": "bob@example.com", "FirstName": "Bob", "LastName": "Brown"}'
    assert result == expected


def test_pascal_case_load(impl: Any) -> None:
    data = b'{"FirstName": "Alice", "LastName": "Green", "EmailAddress": "alice@example.com"}'
    result = impl.load(WithSnakeCase, data, naming_case=mr.CAPITAL_CAMEL_CASE)
    assert result == WithSnakeCase(first_name="Alice", last_name="Green", email_address="alice@example.com")


def test_naming_case_nested(impl: Any) -> None:
    obj = Person(name="Test", age=25, address=Address(street="Main St", city="NYC", zip_code="10001"))
    result = impl.dump(Person, obj, naming_case=mr.CAMEL_CASE)
    expected = '{"address": {"city": "NYC", "street": "Main St", "zipCode": "10001"}, ' '"age": 25, "name": "Test"}'
    assert result == expected


def test_upper_snake_case_dump(impl: Any) -> None:
    obj = WithSnakeCase(first_name="Tom", last_name="Jones", email_address="tom@example.com")
    result = impl.dump(WithSnakeCase, obj, naming_case=mr.UPPER_SNAKE_CASE)
    expected = '{"EMAIL_ADDRESS": "tom@example.com", "FIRST_NAME": "Tom", "LAST_NAME": "Jones"}'
    assert result == expected


def test_upper_snake_case_load(impl: Any) -> None:
    data = b'{"FIRST_NAME": "Sarah", "LAST_NAME": "Wilson", "EMAIL_ADDRESS": "sarah@example.com"}'
    result = impl.load(WithSnakeCase, data, naming_case=mr.UPPER_SNAKE_CASE)
    assert result == WithSnakeCase(first_name="Sarah", last_name="Wilson", email_address="sarah@example.com")


def test_upper_snake_case_roundtrip(impl: Any) -> None:
    obj = WithSnakeCase(first_name="Mike", last_name="Davis", email_address="mike@example.com")
    dumped = impl.dump(WithSnakeCase, obj, naming_case=mr.UPPER_SNAKE_CASE)
    loaded = impl.load(
        WithSnakeCase, dumped.encode() if isinstance(dumped, str) else dumped, naming_case=mr.UPPER_SNAKE_CASE
    )
    assert loaded == obj
