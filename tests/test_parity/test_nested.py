from typing import Any

from tests.test_parity.conftest import Address, Company, Department, Person


def test_nested_2_levels_dump(impl: Any) -> None:
    obj = Person(name="John Doe", age=30, address=Address(street="123 Main St", city="Boston", zip_code="02101"))
    result = impl.dump(Person, obj)
    expected = (
        '{"address": {"city": "Boston", "street": "123 Main St", "zip_code": "02101"}, '
        '"age": 30, "name": "John Doe"}'
    )
    assert result == expected


def test_nested_2_levels_load(impl: Any) -> None:
    data = (
        b'{"name": "John Doe", "age": 30, '
        b'"address": {"street": "123 Main St", "city": "Boston", "zip_code": "02101"}}'
    )
    result = impl.load(Person, data)
    assert result == Person(
        name="John Doe", age=30, address=Address(street="123 Main St", city="Boston", zip_code="02101")
    )


def test_nested_3_levels_dump(impl: Any) -> None:
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
    expected = (
        '{"department": {"head": {"address": {"city": "San Francisco", '
        '"street": "456 Tech Ave", "zip_code": "94102"}, "age": 40, '
        '"name": "Alice Smith"}, "name": "Engineering"}, "name": "ACME Corp"}'
    )
    assert result == expected


def test_nested_3_levels_load(impl: Any) -> None:
    data = (
        b'{"name": "ACME Corp", '
        b'"department": {"name": "Engineering", '
        b'"head": {"name": "Alice Smith", "age": 40, '
        b'"address": {"street": "456 Tech Ave", "city": "San Francisco", "zip_code": "94102"}}}}'
    )
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
