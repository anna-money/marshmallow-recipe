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
    capital_camel_case = mr.CapitalCamelCase(capitalize_words={"bar"})
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
    camel_case = mr.CamelCase(capitalize_words={"bar"})
    assert expected == camel_case(name)


@pytest.mark.parametrize(
    "first, second",
    [
        (mr.CAPITAL_CAMEL_CASE, mr.CAPITAL_CAMEL_CASE),
        (mr.CAMEL_CASE, mr.CAMEL_CASE),
        (mr.CapitalCamelCase(capitalize_words={"hello"}), mr.CapitalCamelCase(capitalize_words={"hello"})),
    ],
)
def test_naming_cases_equal(first: mr.NamingCase, second: mr.NamingCase) -> None:
    assert first == second


@pytest.mark.parametrize(
    "first, second",
    [
        (mr.CAPITAL_CAMEL_CASE, mr.DEFAULT_CASE),
        (mr.CAMEL_CASE, mr.DEFAULT_CASE),
        (mr.CapitalCamelCase(capitalize_words={"foo"}), mr.CapitalCamelCase(capitalize_words={"bar"})),
        (mr.CAPITAL_CAMEL_CASE, mr.CapitalCamelCase(capitalize_words={"bar"})),
        (mr.CamelCase(capitalize_words={"foo"}), mr.CamelCase(capitalize_words={"bar"})),
        (mr.CAMEL_CASE, mr.CamelCase(capitalize_words={"bar"})),
        (mr.CapitalCamelCase(capitalize_words={"hello"}), mr.CamelCase(capitalize_words={"hello"})),
    ],
)
def test_naming_cases_not_equal(first: mr.NamingCase, second: mr.NamingCase) -> None:
    assert first != second
