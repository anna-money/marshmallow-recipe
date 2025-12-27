import decimal
from typing import Any

from tests.test_parity.conftest import WithDecimalRoundDown, WithDecimalRoundUp


def test_round_up_dump(impl: Any) -> None:
    obj = WithDecimalRoundUp(value=decimal.Decimal("1.234"))
    result = impl.dump(WithDecimalRoundUp, obj)
    assert result == '{"value": "1.24"}'


def test_round_up_edge_case(impl: Any) -> None:
    obj = WithDecimalRoundUp(value=decimal.Decimal("1.235"))
    result = impl.dump(WithDecimalRoundUp, obj)
    assert result == '{"value": "1.24"}'


def test_round_up_already_rounded(impl: Any) -> None:
    obj = WithDecimalRoundUp(value=decimal.Decimal("1.20"))
    result = impl.dump(WithDecimalRoundUp, obj)
    assert result == '{"value": "1.20"}'


def test_round_down_dump(impl: Any) -> None:
    obj = WithDecimalRoundDown(value=decimal.Decimal("1.239"))
    result = impl.dump(WithDecimalRoundDown, obj)
    assert result == '{"value": "1.23"}'


def test_round_down_edge_case(impl: Any) -> None:
    obj = WithDecimalRoundDown(value=decimal.Decimal("1.235"))
    result = impl.dump(WithDecimalRoundDown, obj)
    assert result == '{"value": "1.23"}'


def test_round_up_load(impl: Any) -> None:
    data = b'{"value": "9.876"}'
    result = impl.load(WithDecimalRoundUp, data)
    assert result == WithDecimalRoundUp(value=decimal.Decimal("9.88"))


def test_round_down_load(impl: Any) -> None:
    data = b'{"value": "7.654"}'
    result = impl.load(WithDecimalRoundDown, data)
    assert result == WithDecimalRoundDown(value=decimal.Decimal("7.65"))
