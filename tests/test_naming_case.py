import pytest

import marshmallow_recipe as mr


@pytest.mark.parametrize(
    "name, expected",
    [
        ("hello", "Hello"),
        ("hello_world", "HelloWorld"),
        ("answer_is_42", "AnswerIs42"),
        ("hello__world", "HelloWorld"),
        ("foo_bar", "FooBAR"),
    ],
)
def test_capital_camel_case(name: str, expected: str) -> None:
    capital_camel_case = mr.CapitalCamelCase(capitalize_words=frozenset(["bar"]))
    assert expected == capital_camel_case(name)


@pytest.mark.parametrize(
    "name, expected",
    [
        ("hello", "hello"),
        ("hello_world", "helloWorld"),
        ("answer_is_42", "answerIs42"),
        ("hello__world", "helloWorld"),
        ("foo_bar", "fooBAR"),
        ("bar_foo", "barFoo"),
    ],
)
def test_camel_case(name: str, expected: str) -> None:
    camel_case = mr.CamelCase(capitalize_words=frozenset(["bar"]))
    assert expected == camel_case(name)


@pytest.mark.parametrize(
    "name, expected",
    [
        ("hello", "HELLO"),
        ("hello_world", "HELLO_WORLD"),
        ("answer_is_42", "ANSWER_IS_42"),
        ("hello__world", "HELLO__WORLD"),
        ("foo_bar", "FOO_BAR"),
    ],
)
def test_upper_snake_case(name: str, expected: str) -> None:
    upper_snake_case = mr.UpperSnakeCase()
    assert expected == upper_snake_case(name)


@pytest.mark.parametrize(
    "first, second",
    [
        (mr.CAPITAL_CAMEL_CASE, mr.CAPITAL_CAMEL_CASE),
        (mr.CAMEL_CASE, mr.CAMEL_CASE),
        (
            mr.CapitalCamelCase(capitalize_words=frozenset(["hello"])),
            mr.CapitalCamelCase(capitalize_words=frozenset(["hello"])),
        ),
    ],
)
def test_naming_cases_equal(first: mr.NamingCase, second: mr.NamingCase) -> None:
    assert first == second


@pytest.mark.parametrize(
    "first, second",
    [
        (
            mr.CapitalCamelCase(capitalize_words=frozenset(["foo"])),
            mr.CapitalCamelCase(capitalize_words=frozenset(["bar"])),
        ),
        (mr.CAPITAL_CAMEL_CASE, mr.CapitalCamelCase(capitalize_words=frozenset(["bar"]))),
        (mr.CamelCase(capitalize_words=frozenset(["foo"])), mr.CamelCase(capitalize_words=frozenset(["bar"]))),
        (mr.CAMEL_CASE, mr.CamelCase(capitalize_words=frozenset(["bar"]))),
        (
            mr.CapitalCamelCase(capitalize_words=frozenset(["hello"])),
            mr.CamelCase(capitalize_words=frozenset(["hello"])),
        ),
    ],
)
def test_naming_cases_not_equal(first: mr.NamingCase, second: mr.NamingCase) -> None:
    assert first != second
