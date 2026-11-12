import datetime
import decimal
import uuid
from typing import Any

import marshmallow
import pytest

from .conftest import NoneDefaultOf, NoneDefaultOfNoSlots, Serializer, Value1

_HOLDERS = [pytest.param(NoneDefaultOf, id="slots"), pytest.param(NoneDefaultOfNoSlots, id="no_slots")]

_VALUES = [
    pytest.param(int, 42, b'{"value":42}', id="int"),
    pytest.param(str, "hello", b'{"value":"hello"}', id="str"),
    pytest.param(bool, True, b'{"value":true}', id="bool"),
    pytest.param(float, 3.14, b'{"value":3.14}', id="float"),
    pytest.param(decimal.Decimal, decimal.Decimal("1.23"), b'{"value":"1.23"}', id="decimal"),
    pytest.param(
        datetime.datetime,
        datetime.datetime(2025, 12, 26, 10, 30, 45, tzinfo=datetime.UTC),
        b'{"value":"2025-12-26T10:30:45+00:00"}',
        id="datetime",
    ),
    pytest.param(datetime.date, datetime.date(2025, 12, 26), b'{"value":"2025-12-26"}', id="date"),
    pytest.param(
        uuid.UUID,
        uuid.UUID("12345678-1234-5678-1234-567812345678"),
        b'{"value":"12345678-1234-5678-1234-567812345678"}',
        id="uuid",
    ),
    pytest.param(Value1, Value1(v1="a"), b'{"value":{"v1":"a"}}', id="nested"),
    pytest.param(list[int], [1, 2], b'{"value":[1,2]}', id="list"),
    pytest.param(dict[str, int], {"a": 1}, b'{"value":{"a":1}}', id="dict"),
    pytest.param(int | str, "a", b'{"value":"a"}', id="union"),
    pytest.param(Any, {"a": [1]}, b'{"value":{"a":[1]}}', id="any"),
]

_TYPES = [pytest.param(v.values[0], id=v.id) for v in _VALUES]


class TestNoneDefaultDump:
    @pytest.mark.parametrize("holder", _HOLDERS)
    @pytest.mark.parametrize("value_type", _TYPES)
    def test_none(self, impl: Serializer, holder: Any, value_type: Any) -> None:
        result = impl.dump(holder[value_type], holder[value_type]())
        assert result == b"{}"

    @pytest.mark.parametrize("holder", _HOLDERS)
    @pytest.mark.parametrize(("value_type", "value", "data"), _VALUES)
    def test_value(self, impl: Serializer, holder: Any, value_type: Any, value: Any, data: bytes) -> None:
        result = impl.dump(holder[value_type], holder[value_type](value=value))
        assert result == data


class TestNoneDefaultLoad:
    @pytest.mark.parametrize("holder", _HOLDERS)
    @pytest.mark.parametrize("value_type", _TYPES)
    def test_absent(self, impl: Serializer, holder: Any, value_type: Any) -> None:
        result = impl.load(holder[value_type], b"{}")
        assert result == holder[value_type]()

    @pytest.mark.parametrize("holder", _HOLDERS)
    @pytest.mark.parametrize(("value_type", "value", "data"), _VALUES)
    def test_value(self, impl: Serializer, holder: Any, value_type: Any, value: Any, data: bytes) -> None:
        result = impl.load(holder[value_type], data)
        assert result == holder[value_type](value=value)

    @pytest.mark.parametrize("holder", _HOLDERS)
    @pytest.mark.parametrize("value_type", [t for t in _TYPES if t.id != "any"])
    def test_null(self, impl: Serializer, holder: Any, value_type: Any) -> None:
        with pytest.raises(marshmallow.ValidationError) as exc:
            impl.load(holder[value_type], b'{"value":null}')
        assert exc.value.messages == {"value": ["Field may not be null."]}
