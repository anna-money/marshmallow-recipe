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
    capital_camel_case = mr.capital_camel_case_factory(capitalize_words={"bar"})
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
    camel_case = mr.camel_case_factory(capitalize_words={"bar"})
    assert expected == camel_case(name)
