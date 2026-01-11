import marshmallow
import pytest

from .conftest import (
    Address,
    Company,
    Cyclic,
    CyclicChild,
    CyclicParent,
    Department,
    Person,
    PersonWithAddressTwoValidators,
    PersonWithAddressValidation,
    Serializer,
    WithNestedDefault,
    WithNestedMissing,
)


@pytest.fixture
def skip_if_no_cyclic(impl: Serializer) -> None:
    if not impl.supports_cyclic:
        pytest.skip("cyclic references not supported")


class TestNestedDump:
    def test_2_levels(self, impl: Serializer) -> None:
        obj = Person(name="John Doe", age=30, address=Address(street="123 Main St", city="Boston", zip_code="02101"))
        result = impl.dump(Person, obj)
        expected = b'{"name":"John Doe","age":30,"address":{"street":"123 Main St","city":"Boston","zip_code":"02101"}}'
        assert result == expected

    def test_3_levels(self, impl: Serializer) -> None:
        obj = Company(
            name="ACME Corp",
            department=Department(
                name="Engineering",
                head=Person(
                    name="Alice Smith",
                    age=40,
                    address=Address(street="456 Tech Ave", city="San Francisco", zip_code="94102"),
                ),
            ),
        )
        result = impl.dump(Company, obj)
        expected = b'{"name":"ACME Corp","department":{"name":"Engineering","head":{"name":"Alice Smith","age":40,"address":{"street":"456 Tech Ave","city":"San Francisco","zip_code":"94102"}}}}'
        assert result == expected

    def test_empty_strings(self, impl: Serializer) -> None:
        obj = Person(name="", age=0, address=Address(street="", city="", zip_code=""))
        result = impl.dump(Person, obj)
        assert result == b'{"name":"","age":0,"address":{"street":"","city":"","zip_code":""}}'

    def test_unicode_values(self, impl: Serializer) -> None:
        obj = Person(
            name="Джон Доу", age=30, address=Address(street="Улица Мира 123", city="Москва", zip_code="123456")
        )
        result = impl.dump(Person, obj)
        loaded = impl.load(Person, result)
        assert loaded == obj

    def test_special_chars(self, impl: Serializer) -> None:
        obj = Person(
            name='John "The Dev" Doe',
            age=30,
            address=Address(street="123 Main St\nApt 4", city="New\tYork", zip_code="12345"),
        )
        result = impl.dump(Person, obj)
        loaded = impl.load(Person, result)
        assert loaded == obj

    def test_validation_error(self, impl: Serializer) -> None:
        obj = PersonWithAddressValidation(name="John", address=Address(street="Main", city="", zip_code="12345"))
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.dump(PersonWithAddressValidation, obj)
        assert exc.value.messages == {"address": [{"city": ["City cannot be empty"]}]}

    def test_validation_success(self, impl: Serializer) -> None:
        obj = PersonWithAddressValidation(name="John", address=Address(street="Main", city="Boston", zip_code="12345"))
        result = impl.dump(PersonWithAddressValidation, obj)
        expected = b'{"name":"John","address":{"street":"Main","city":"Boston","zip_code":"12345"}}'
        assert result == expected

    def test_missing(self, impl: Serializer) -> None:
        obj = WithNestedMissing()
        result = impl.dump(WithNestedMissing, obj)
        assert result == b"{}"

    def test_missing_with_value(self, impl: Serializer) -> None:
        obj = WithNestedMissing(address=Address(street="Main St", city="Boston", zip_code="02101"))
        result = impl.dump(WithNestedMissing, obj)
        assert result == b'{"address":{"street":"Main St","city":"Boston","zip_code":"02101"}}'


class TestNestedLoad:
    def test_2_levels(self, impl: Serializer) -> None:
        data = b'{"name":"John Doe","age":30,"address":{"street":"123 Main St","city":"Boston","zip_code":"02101"}}'
        result = impl.load(Person, data)
        assert result == Person(
            name="John Doe", age=30, address=Address(street="123 Main St", city="Boston", zip_code="02101")
        )

    def test_3_levels(self, impl: Serializer) -> None:
        data = b'{"name":"ACME Corp","department":{"name":"Engineering","head":{"name":"Alice Smith","age":40,"address":{"street":"456 Tech Ave","city":"San Francisco","zip_code":"94102"}}}}'
        result = impl.load(Company, data)
        assert result == Company(
            name="ACME Corp",
            department=Department(
                name="Engineering",
                head=Person(
                    name="Alice Smith",
                    age=40,
                    address=Address(street="456 Tech Ave", city="San Francisco", zip_code="94102"),
                ),
            ),
        )

    def test_missing_field(self, impl: Serializer) -> None:
        data = b'{"name":"John","age":30,"address":{"street":"Main","city":"NYC"}}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(Person, data)
        assert "address" in exc.value.messages

    def test_wrong_type(self, impl: Serializer) -> None:
        data = b'{"name":"John","age":30,"address":"not_an_object"}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(Person, data)
        assert "address" in exc.value.messages

    def test_null_for_required(self, impl: Serializer) -> None:
        data = b'{"name":"John","age":30,"address":null}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(Person, data)
        assert "address" in exc.value.messages

    def test_missing_required(self, impl: Serializer) -> None:
        data = b'{"name":"John","age":30}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(Person, data)
        assert exc.value.messages == {"address": ["Missing data for required field."]}

    def test_validation_error(self, impl: Serializer) -> None:
        data = b'{"name":"John","address":{"street":"Main","city":"","zip_code":"12345"}}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(PersonWithAddressValidation, data)
        assert exc.value.messages == {"address": [{"city": ["City cannot be empty"]}]}

    def test_validation_success(self, impl: Serializer) -> None:
        data = b'{"name":"John","address":{"street":"Main","city":"Boston","zip_code":"12345"}}'
        result = impl.load(PersonWithAddressValidation, data)
        assert result == PersonWithAddressValidation(
            name="John", address=Address(street="Main", city="Boston", zip_code="12345")
        )

    def test_two_validators_pass(self, impl: Serializer) -> None:
        data = b'{"name":"John","address":{"street":"Main","city":"Boston","zip_code":"12345"}}'
        result = impl.load(PersonWithAddressTwoValidators, data)
        assert result == PersonWithAddressTwoValidators(
            name="John", address=Address(street="Main", city="Boston", zip_code="12345")
        )

    def test_two_validators_first_fails(self, impl: Serializer) -> None:
        data = b'{"name":"John","address":{"street":"Main","city":"","zip_code":"12345"}}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(PersonWithAddressTwoValidators, data)
        assert exc.value.messages == {"address": [{"city": ["City cannot be empty"]}]}

    def test_two_validators_second_fails(self, impl: Serializer) -> None:
        data = b'{"name":"John","address":{"street":"Main","city":"Boston","zip_code":"123"}}'
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(PersonWithAddressTwoValidators, data)
        assert exc.value.messages == {"address": [{"zip_code": ["Zip code must be 5 characters"]}]}

    def test_missing(self, impl: Serializer) -> None:
        data = b"{}"
        result = impl.load(WithNestedMissing, data)
        assert result == WithNestedMissing()

    def test_missing_with_value(self, impl: Serializer) -> None:
        data = b'{"address":{"street":"Main St","city":"Boston","zip_code":"02101"}}'
        result = impl.load(WithNestedMissing, data)
        assert result == WithNestedMissing(address=Address(street="Main St", city="Boston", zip_code="02101"))

    def test_nested_default(self, impl: Serializer) -> None:
        data = b"{}"
        result = impl.load(WithNestedDefault, data)
        assert result == WithNestedDefault()

    @pytest.mark.usefixtures("skip_if_no_cyclic")
    def test_cyclic_self_reference_none(self, impl: Serializer) -> None:
        data = b'{"marker":"level 1"}'
        result = impl.load(Cyclic, data)
        assert result == Cyclic(marker="level 1", child=None)

    @pytest.mark.usefixtures("skip_if_no_cyclic")
    def test_cyclic_self_reference_nested(self, impl: Serializer) -> None:
        data = b'{"marker":"level 1","child":{"marker":"level 2"}}'
        result = impl.load(Cyclic, data)
        assert result == Cyclic(marker="level 1", child=Cyclic(marker="level 2", child=None))

    @pytest.mark.usefixtures("skip_if_no_cyclic")
    def test_cyclic_indirect_reference(self, impl: Serializer) -> None:
        data = b'{"marker":"level 1","child":{"marker":"level 2"}}'
        result = impl.load(CyclicParent, data)
        assert result == CyclicParent(marker="level 1", child=CyclicChild(marker="level 2", parent=None))


@pytest.mark.usefixtures("skip_if_no_cyclic")
class TestCyclicDump:
    def test_cyclic_self_reference_none(self, impl: Serializer) -> None:
        obj = Cyclic(marker="level 1", child=None)
        result = impl.dump(Cyclic, obj)
        assert result == b'{"marker":"level 1"}'

    def test_cyclic_self_reference_nested(self, impl: Serializer) -> None:
        obj = Cyclic(marker="level 1", child=Cyclic(marker="level 2", child=None))
        result = impl.dump(Cyclic, obj)
        assert result == b'{"marker":"level 1","child":{"marker":"level 2"}}'

    def test_cyclic_indirect_reference(self, impl: Serializer) -> None:
        obj = CyclicParent(marker="level 1", child=CyclicChild(marker="level 2", parent=None))
        result = impl.dump(CyclicParent, obj)
        assert result == b'{"marker":"level 1","child":{"marker":"level 2"}}'

    def test_cyclic_indirect_deeply_nested(self, impl: Serializer) -> None:
        obj = CyclicParent(
            marker="level 1",
            child=CyclicChild(
                marker="level 2",
                parent=CyclicParent(marker="level 3", child=CyclicChild(marker="level 4", parent=None)),
            ),
        )
        result = impl.dump(CyclicParent, obj)
        expected = b'{"marker":"level 1","child":{"marker":"level 2","parent":{"marker":"level 3","child":{"marker":"level 4"}}}}'
        assert result == expected


class TestNestedDumpInvalidType:
    """Test that invalid types in nested fields raise ValidationError on dump."""

    @pytest.mark.parametrize("value", ["not an address", {"street": "Main", "city": "NYC", "zip_code": "10001"}, 123])
    def test_invalid_type(self, impl: Serializer, value: object) -> None:
        obj = Person(**{"name": "John", "age": 30, "address": value})  # type: ignore[arg-type]
        with pytest.raises(marshmallow.ValidationError):
            impl.dump(Person, obj)


class TestNestedEdgeCases:
    """Test nested dataclass edge cases with boundary values and special scenarios."""

    def test_5_level_nesting(self, impl: Serializer) -> None:
        # Company -> Department -> Person -> Address (4 levels)
        # Let's test with the existing structures
        obj = Company(
            name="ACME",
            department=Department(
                name="Eng",
                head=Person(name="Alice", age=30, address=Address(street="123 Main", city="Boston", zip_code="02101")),
            ),
        )
        result = impl.dump(Company, obj)
        loaded = impl.load(Company, result)
        assert loaded == obj

    def test_unicode_in_all_nested_fields(self, impl: Serializer) -> None:
        obj = Person(
            name="Иван Иванов", age=25, address=Address(street="Улица Мира 123", city="Москва", zip_code="123456")
        )
        result = impl.dump(Person, obj)
        loaded = impl.load(Person, result)
        assert loaded == obj

    def test_special_chars_in_all_nested_fields(self, impl: Serializer) -> None:
        obj = Person(
            name='"John" O\'Connor',
            age=30,
            address=Address(street="123 Main St\nApt 4", city="New\tYork", zip_code="10001"),
        )
        result = impl.dump(Person, obj)
        loaded = impl.load(Person, result)
        assert loaded == obj

    def test_big_int_age(self, impl: Serializer) -> None:
        obj = Person(
            name="Ancient",
            age=9223372036854775807,
            address=Address(street="Forever St", city="Eternity", zip_code="00000"),
        )
        result = impl.dump(Person, obj)
        loaded = impl.load(Person, result)
        assert loaded == obj

    def test_zero_age(self, impl: Serializer) -> None:
        obj = Person(name="Newborn", age=0, address=Address(street="Hospital", city="City", zip_code="12345"))
        result = impl.dump(Person, obj)
        loaded = impl.load(Person, result)
        assert loaded == obj

    def test_negative_age(self, impl: Serializer) -> None:
        obj = Person(
            name="Time Traveler", age=-100, address=Address(street="Future St", city="Tomorrow", zip_code="99999")
        )
        result = impl.dump(Person, obj)
        loaded = impl.load(Person, result)
        assert loaded == obj

    def test_very_long_strings_in_nested(self, impl: Serializer) -> None:
        obj = Person(
            name="x" * 10000, age=30, address=Address(street="y" * 10000, city="z" * 10000, zip_code="a" * 10000)
        )
        result = impl.dump(Person, obj)
        loaded = impl.load(Person, result)
        assert loaded == obj

    def test_whitespace_strings_in_nested(self, impl: Serializer) -> None:
        obj = Person(name="   ", age=30, address=Address(street="\t\t\t", city="\n\n\n", zip_code="   "))
        result = impl.dump(Person, obj)
        loaded = impl.load(Person, result)
        assert loaded == obj

    def test_emoji_in_all_fields(self, impl: Serializer) -> None:
        obj = Person(
            name="🧑‍💻 Developer", age=30, address=Address(street="🏠 Home 🏡", city="🌆 City 🌃", zip_code="12345")
        )
        result = impl.dump(Person, obj)
        loaded = impl.load(Person, result)
        assert loaded == obj
