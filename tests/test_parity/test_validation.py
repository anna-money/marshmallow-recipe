import decimal
from typing import Any

import marshmallow
import pytest

from tests.test_parity.conftest import (
    WithDecimalValidation,
    WithEmailValidation,
    WithFloatValidation,
    WithIntValidation,
    WithRegexValidation,
    WithStrValidation,
)


def test_int_validation_pass(impl: Any) -> None:
    data = b'{"value": 10}'
    result = impl.load(WithIntValidation, data)
    assert result == WithIntValidation(value=10)


def test_int_validation_fail(impl: Any) -> None:
    data = b'{"value": 0}'
    with pytest.raises(marshmallow.ValidationError):
        impl.load(WithIntValidation, data)


def test_int_validation_negative_fail(impl: Any) -> None:
    data = b'{"value": -5}'
    with pytest.raises(marshmallow.ValidationError):
        impl.load(WithIntValidation, data)


def test_float_validation_pass(impl: Any) -> None:
    data = b'{"value": 5.5}'
    result = impl.load(WithFloatValidation, data)
    assert result == WithFloatValidation(value=5.5)


def test_float_validation_zero_pass(impl: Any) -> None:
    data = b'{"value": 0.0}'
    result = impl.load(WithFloatValidation, data)
    assert result == WithFloatValidation(value=0.0)


def test_float_validation_negative_fail(impl: Any) -> None:
    data = b'{"value": -1.5}'
    with pytest.raises(marshmallow.ValidationError):
        impl.load(WithFloatValidation, data)


def test_str_validation_pass(impl: Any) -> None:
    data = b'{"value": "hello"}'
    result = impl.load(WithStrValidation, data)
    assert result == WithStrValidation(value="hello")


def test_str_validation_empty_fail(impl: Any) -> None:
    data = b'{"value": ""}'
    with pytest.raises(marshmallow.ValidationError):
        impl.load(WithStrValidation, data)


def test_decimal_validation_pass(impl: Any) -> None:
    data = b'{"value": "10.5"}'
    result = impl.load(WithDecimalValidation, data)
    assert result == WithDecimalValidation(value=decimal.Decimal("10.5"))


def test_decimal_validation_zero_fail(impl: Any) -> None:
    data = b'{"value": "0"}'
    with pytest.raises(marshmallow.ValidationError):
        impl.load(WithDecimalValidation, data)


def test_decimal_validation_negative_fail(impl: Any) -> None:
    data = b'{"value": "-5.5"}'
    with pytest.raises(marshmallow.ValidationError):
        impl.load(WithDecimalValidation, data)


def test_email_validation_pass(impl: Any) -> None:
    data = b'{"email": "test@example.com"}'
    result = impl.load(WithEmailValidation, data)
    assert result == WithEmailValidation(email="test@example.com")


def test_email_validation_invalid_fail(impl: Any) -> None:
    data = b'{"email": "not-an-email"}'
    with pytest.raises(marshmallow.ValidationError):
        impl.load(WithEmailValidation, data)


def test_email_validation_empty_fail(impl: Any) -> None:
    data = b'{"email": ""}'
    with pytest.raises(marshmallow.ValidationError):
        impl.load(WithEmailValidation, data)


def test_regex_validation_pass(impl: Any) -> None:
    data = b'{"code": "ABC"}'
    result = impl.load(WithRegexValidation, data)
    assert result == WithRegexValidation(code="ABC")


def test_regex_validation_lowercase_fail(impl: Any) -> None:
    data = b'{"code": "abc"}'
    with pytest.raises(marshmallow.ValidationError):
        impl.load(WithRegexValidation, data)


def test_regex_validation_wrong_length_fail(impl: Any) -> None:
    data = b'{"code": "AB"}'
    with pytest.raises(marshmallow.ValidationError):
        impl.load(WithRegexValidation, data)


def test_regex_validation_numbers_fail(impl: Any) -> None:
    data = b'{"code": "123"}'
    with pytest.raises(marshmallow.ValidationError):
        impl.load(WithRegexValidation, data)
