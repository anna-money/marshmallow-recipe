import decimal
from typing import Any

import marshmallow
import pytest

from tests.test_parity.conftest import SimpleTypes, WithDecimal


def test_dump_simple(impl: Any) -> None:
    obj = SimpleTypes(name="test", age=30)
    result = impl.dump(SimpleTypes, obj)
    assert result == '{"age": 30, "name": "test"}'


def test_load_simple(impl: Any) -> None:
    data = b'{"name": "test", "age": 30}'
    result = impl.load(SimpleTypes, data)
    assert result == SimpleTypes(name="test", age=30)


def test_load_missing_required_field(impl: Any) -> None:
    data = b'{"name": "test"}'
    with pytest.raises(marshmallow.ValidationError) as exc:
        impl.load(SimpleTypes, data)
    assert exc.value.messages == {"age": ["Missing data for required field."]}


def test_decimal_dump_with_places(impl: Any) -> None:
    obj = WithDecimal(value=decimal.Decimal("123.456"))
    result = impl.dump(WithDecimal, obj, decimal_places=2)
    assert result == '{"value": "123.46"}'


def test_decimal_dump_no_places(impl: Any) -> None:
    obj = WithDecimal(value=decimal.Decimal("123.456"))
    result = impl.dump(WithDecimal, obj)
    assert result == '{"value": "123.46"}'
