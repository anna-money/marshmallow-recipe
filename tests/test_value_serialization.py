import dataclasses
import datetime
import decimal
import uuid
from typing import Any

import marshmallow as m
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
        # Optional primitives (T | None)
        (int | None, 42, 42),
        (int | None, None, None),
        (str | None, "hello", "hello"),
        (str | None, None, None),
        (str | None, "", ""),
        (bool | None, True, True),
        (bool | None, None, None),
        (float | None, 3.14, 3.14),
        (float | None, None, None),
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


def test_load_value_invalid_int() -> None:
    with pytest.raises(m.ValidationError) as e:
        mr.load_value(int, "not_a_number")
    assert e.value.messages == ["Not a valid integer."]


def test_load_value_int_none() -> None:
    with pytest.raises(m.ValidationError) as e:
        mr.load_value(int, None)
    assert e.value.messages == ["Field may not be null."]


def test_load_value_list_invalid_item() -> None:
    with pytest.raises(m.ValidationError) as e:
        mr.load_value(list[int], [1, "invalid", 3])
    assert e.value.messages == {1: ["Not a valid integer."]}


def test_load_value_dict_invalid_value() -> None:
    with pytest.raises(m.ValidationError):
        mr.load_value(dict[str, int], {"a": "invalid"})


def test_load_value_dict_complex_invalid() -> None:
    with pytest.raises(m.ValidationError):
        mr.load_value(dict[datetime.date, decimal.Decimal], {"invalid": "invalid"})


def test_load_value_invalid_uuid() -> None:
    with pytest.raises(m.ValidationError):
        mr.load_value(uuid.UUID, "not-a-uuid")


def test_load_value_invalid_datetime() -> None:
    with pytest.raises(m.ValidationError):
        mr.load_value(datetime.datetime, "not-a-date")


def test_load_value_invalid_decimal() -> None:
    with pytest.raises(m.ValidationError):
        mr.load_value(decimal.Decimal, "not-a-number")


def test_load_value_optional_invalid() -> None:
    with pytest.raises(m.ValidationError):
        mr.load_value(int | None, "invalid")  # type: ignore[arg-type]


def test_load_value_nested_dataclass_invalid() -> None:
    with pytest.raises(m.ValidationError):
        mr.load_value(list[Holder[int]], [{"value": "invalid"}])


def test_load_value_nested_list_invalid() -> None:
    with pytest.raises(m.ValidationError):
        mr.load_value(list[list[int]], [[1, 2], ["invalid"]])


def test_load_value_union_valid() -> None:
    assert mr.load_value(int | str, 42) == 42  # type: ignore[arg-type]
    assert mr.load_value(int | str, "hello") == "hello"  # type: ignore[arg-type]


def test_load_value_union_invalid() -> None:
    with pytest.raises(m.ValidationError):
        mr.load_value(int | str, [1, 2, 3])  # type: ignore[arg-type]


def test_load_value_union_list_or_none_invalid() -> None:
    with pytest.raises(m.ValidationError):
        mr.load_value(list[int] | None, [1, "invalid"])  # type: ignore[arg-type]


def test_dump_value_invalid_int() -> None:
    with pytest.raises(m.ValidationError):
        mr.dump_value(int, "not_an_int")


def test_dump_value_int_none() -> None:
    with pytest.raises(m.ValidationError):
        mr.dump_value(int, None)
