import marshmallow
import pytest

import marshmallow_recipe as mr

from .conftest import (
    Address,
    Person,
    Serializer,
    WithCollections,
    WithCustomName,
    WithNestedList,
    WithRenamedValidated,
    WithSnakeCase,
)


class TestNamingDump:
    @pytest.mark.parametrize(
        ("naming_case", "error_messages"),
        [
            pytest.param(None, {"id": ["Invalid value."]}, id="custom_name"),
            pytest.param(mr.CAMEL_CASE, {"id": ["Invalid value."]}, id="custom_name_camel_case"),
        ],
    )
    def test_error_keys(
        self, impl: Serializer, naming_case: mr.NamingCase | None, error_messages: dict[str, list[str]]
    ) -> None:
        obj = WithRenamedValidated(internal_id=-1, user_age=1)
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.dump(WithRenamedValidated, obj, naming_case=naming_case)
        assert exc.value.messages == error_messages

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

    def test_collections_camel_case(self, impl: Serializer) -> None:
        obj = WithCollections(
            list_int=[1, 2],
            list_str=["a"],
            dict_str_int={"key": 1},
            set_str={"x"},
            frozenset_int=frozenset([7]),
            tuple_str=("t",),
        )
        result = impl.dump(WithCollections, obj, naming_case=mr.CAMEL_CASE)
        expected = (
            b'{"listInt":[1,2],"listStr":["a"],"dictStrInt":{"key":1},'
            b'"setStr":["x"],"frozensetInt":[7],"tupleStr":["t"]}'
        )
        assert result == expected

    def test_nested_list_camel_case(self, impl: Serializer) -> None:
        obj = WithNestedList(
            display_name="Team", home_addresses=[Address(street="Main St", city="NYC", zip_code="10001")]
        )
        result = impl.dump(WithNestedList, obj, naming_case=mr.CAMEL_CASE)
        expected = b'{"displayName":"Team","homeAddresses":[{"street":"Main St","city":"NYC","zipCode":"10001"}]}'
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
        ("data", "naming_case", "error_messages"),
        [
            pytest.param(
                b'{"id":"x","user_age":"y"}',
                None,
                {"id": ["Not a valid integer."], "user_age": ["Not a valid integer."]},
                id="invalid_type",
            ),
            pytest.param(
                b'{"id":"x","userAge":"y"}',
                mr.CAMEL_CASE,
                {"id": ["Not a valid integer."], "userAge": ["Not a valid integer."]},
                id="invalid_type_camel_case",
            ),
            pytest.param(
                b"{}",
                mr.CAMEL_CASE,
                {"id": ["Missing data for required field."], "userAge": ["Missing data for required field."]},
                id="missing_camel_case",
            ),
            pytest.param(b'{"id":-1,"userAge":1}', mr.CAMEL_CASE, {"id": ["Invalid value."]}, id="validate_camel_case"),
        ],
    )
    def test_error_keys(
        self, impl: Serializer, data: bytes, naming_case: mr.NamingCase | None, error_messages: dict[str, list[str]]
    ) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(WithRenamedValidated, data, naming_case=naming_case)
        assert exc.value.messages == error_messages

    def test_nested_error_keys_camel_case(self, impl: Serializer) -> None:
        data = b'{"name":"Test","age":25,"address":{"street":"Main St","city":"NYC","zipCode":1}}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(Person, data, naming_case=mr.CAMEL_CASE)
        assert exc.value.messages == {"address": {"zipCode": ["Not a valid string."]}}

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

    def test_collections_camel_case(self, impl: Serializer) -> None:
        data = (
            b'{"listInt":[1,2],"listStr":["a"],"dictStrInt":{"key":1},'
            b'"setStr":["x"],"frozensetInt":[7],"tupleStr":["t"]}'
        )
        result = impl.load(WithCollections, data, naming_case=mr.CAMEL_CASE)
        assert result == WithCollections(
            list_int=[1, 2],
            list_str=["a"],
            dict_str_int={"key": 1},
            set_str={"x"},
            frozenset_int=frozenset([7]),
            tuple_str=("t",),
        )

    def test_nested_list_camel_case(self, impl: Serializer) -> None:
        data = b'{"displayName":"Team","homeAddresses":[{"street":"Main St","city":"NYC","zipCode":"10001"}]}'
        result = impl.load(WithNestedList, data, naming_case=mr.CAMEL_CASE)
        assert result == WithNestedList(
            display_name="Team", home_addresses=[Address(street="Main St", city="NYC", zip_code="10001")]
        )

    def test_custom_name(self, impl: Serializer) -> None:
        data = b'{"id":456,"email":"user@example.com"}'
        result = impl.load(WithCustomName, data)
        assert result == WithCustomName(internal_id=456, user_email="user@example.com")

    def test_custom_name_with_naming_case(self, impl: Serializer) -> None:
        data = b'{"id":200,"email":"load@example.com"}'
        result = impl.load(WithCustomName, data, naming_case=mr.CAMEL_CASE)
        assert result == WithCustomName(internal_id=200, user_email="load@example.com")
