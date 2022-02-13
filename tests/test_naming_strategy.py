import pytest

import marshmallow_recipe


@pytest.mark.parametrize(
    "name, expected",
    [
        ("hello", "Hello"),
        ("hello_world", "HelloWorld"),
        ("answer_is_42", "AnswerIs42"),
        ("hello__world", "HelloWorld"),
    ],
)
def test_capital_camel_case(name: str, expected: str) -> None:
    assert expected == marshmallow_recipe.capital_camel_case(name)
