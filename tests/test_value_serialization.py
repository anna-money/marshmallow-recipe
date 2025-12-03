import dataclasses
import datetime
import decimal
import uuid
from typing import Any

import pytest

import marshmallow_recipe as mr


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Holder[T]:
    value: T


UUID1 = uuid.UUID("12345678-1234-5678-1234-567812345678")
UUID2 = uuid.UUID("87654321-4321-8765-4321-876543218765")
DT1 = datetime.datetime(2024, 1, 1, 12, 0, 0, tzinfo=datetime.UTC)
DT2 = datetime.datetime(2024, 1, 2, 12, 0, 0, tzinfo=datetime.UTC)


@pytest.mark.parametrize(
    ("value_type", "input_data", "expected_output"),
    [
        # Primitives
        (int, 42, 42),
        (int, 0, 0),
        (int, -1, -1),
        (str, "hello", "hello"),
        (str, "", ""),
        (bool, True, True),
        (bool, False, False),
        (float, 3.14, 3.14),
        (float, 0.0, 0.0),
        # Empty collections
        (list[int], [], []),
        (dict[str, int], {}, {}),
        (set[int], set(), []),
        (frozenset[str], frozenset(), []),
        (tuple[int, ...], (), []),
        (list[list[int]], [], []),
        (dict[str, list[int]], {}, {}),
        # Non-empty collections
        (list[int], [1, 2, 3], [1, 2, 3]),
        (list[str], ["a", "b", "c"], ["a", "b", "c"]),
        (dict[str, int], {"a": 1, "b": 2}, {"a": 1, "b": 2}),
        (dict[int, str], {1: "a", 2: "b"}, {1: "a", 2: "b"}),
        (set[int], {1, 2, 3}, [1, 2, 3]),
        (frozenset[str], frozenset(["a", "b", "c"]), ["a", "b", "c"]),
        (tuple[int, ...], (1, 2, 3), [1, 2, 3]),
        (list[list[int]], [[1, 2], [3, 4]], [[1, 2], [3, 4]]),
        (dict[str, list[int]], {"a": [1, 2], "b": [3, 4]}, {"a": [1, 2], "b": [3, 4]}),
        (dict[str, Any], {"a": 1, "b": "test", "c": [1, 2, 3]}, {"a": 1, "b": "test", "c": [1, 2, 3]}),
        (list[int | None], [1, None, 3], [1, None, 3]),
        (list[int] | None, None, None),
        (list[decimal.Decimal], [decimal.Decimal("1.23"), decimal.Decimal("4.56")], ["1.23", "4.56"]),
        (list[uuid.UUID], [UUID1, UUID2], [str(UUID1), str(UUID2)]),
        (list[datetime.datetime], [DT1, DT2], ["2024-01-01T12:00:00+00:00", "2024-01-02T12:00:00+00:00"]),
        (
            list[Holder[int]],
            [Holder(value=1), Holder(value=2), Holder(value=3)],
            [{"value": 1}, {"value": 2}, {"value": 3}],
        ),
        (
            dict[str, Holder[str]],
            {"h1": Holder(value="a"), "h2": Holder(value="b")},
            {"h1": {"value": "a"}, "h2": {"value": "b"}},
        ),
        (list[Holder[Holder[str]]], [Holder(value=Holder(value="nested"))], [{"value": {"value": "nested"}}]),
    ],
)
def test_value_serialization(value_type: type, input_data: Any, expected_output: Any) -> None:
    dumped = mr.dump_value(value_type, input_data)
    if isinstance(input_data, set | frozenset):
        assert sorted(dumped) == sorted(expected_output)
    else:
        assert dumped == expected_output

    loaded = mr.load_value(value_type, dumped)
    assert loaded == input_data


def test_dump_value_rejects_dataclass() -> None:
    with pytest.raises(ValueError, match="dump_value does not support dataclasses"):
        mr.dump_value(Holder[int], Holder(value=42))


def test_load_value_rejects_dataclass() -> None:
    with pytest.raises(ValueError, match="load_value does not support dataclasses"):
        mr.load_value(Holder[int], {"value": 42})
