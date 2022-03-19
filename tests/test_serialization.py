import dataclasses
import datetime
import decimal
import enum
import uuid
from typing import Any, cast

import marshmallow as m
import pytest

import marshmallow_recipe as mr


class Parity(str, enum.Enum):
    ODD = "ODD"
    EVEN = "EVEN"


def test_simple_types() -> None:
    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class SimpleTypesContainers:
        str_field: str
        optional_str_field: str | None
        bool_field: bool
        optional_bool_field: bool | None
        decimal_field: decimal.Decimal
        optional_decimal_field: decimal.Decimal | None
        int_field: int
        optional_int_field: int | None
        float_field: float
        optional_float_field: float | None
        uuid_field: uuid.UUID
        optional_uuid_field: uuid.UUID | None
        datetime_field: datetime.datetime
        optional_datetime_field: datetime.datetime | None
        date_field: datetime.date
        optional_date_field: datetime.date | None
        dict_field: dict[str, Any]
        optional_dict_field: dict[str, Any] | None

    raw = dict(
        str_field="42",
        optional_str_field="42",
        bool_field=True,
        optional_bool_field=True,
        decimal_field="42.00",
        optional_decimal_field="42.00",
        int_field=42,
        optional_int_field=42,
        float_field=42.0,
        optional_float_field=42.0,
        uuid_field="15f75b02-1c34-46a2-92a5-18363aadea05",
        optional_uuid_field="15f75b02-1c34-46a2-92a5-18363aadea05",
        datetime_field="2022-02-20T11:33:48.607289+00:00",
        optional_datetime_field="2022-02-20T11:33:48.607289+00:00",
        date_field="2022-02-20",
        optional_date_field="2022-02-20",
        dict_field=dict(key="value"),
        optional_dict_field=dict(key="value"),
    )

    loaded = mr.load(SimpleTypesContainers, raw)
    dumped = mr.dump(loaded)

    assert loaded == SimpleTypesContainers(
        str_field="42",
        optional_str_field="42",
        bool_field=True,
        optional_bool_field=True,
        decimal_field=decimal.Decimal("42.00"),
        optional_decimal_field=decimal.Decimal("42.00"),
        int_field=42,
        optional_int_field=42,
        float_field=42.0,
        optional_float_field=42.0,
        uuid_field=uuid.UUID("15f75b02-1c34-46a2-92a5-18363aadea05"),
        optional_uuid_field=uuid.UUID("15f75b02-1c34-46a2-92a5-18363aadea05"),
        datetime_field=datetime.datetime(2022, 2, 20, 11, 33, 48, 607289, datetime.timezone.utc),
        optional_datetime_field=datetime.datetime(2022, 2, 20, 11, 33, 48, 607289, datetime.timezone.utc),
        date_field=datetime.date(2022, 2, 20),
        optional_date_field=datetime.date(2022, 2, 20),
        dict_field=dict(key="value"),
        optional_dict_field=dict(key="value"),
    )
    assert dumped == raw
    assert mr.schema(SimpleTypesContainers) is mr.schema(SimpleTypesContainers)


def test_nested_dataclass() -> None:
    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class BoolContainer:
        bool_field: bool

    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class Container:
        bool_container_field: BoolContainer

    raw = dict(bool_container_field=dict(bool_field=True))
    loaded = mr.load(Container, raw)
    dumped = mr.dump(loaded)

    assert loaded == Container(bool_container_field=BoolContainer(bool_field=True))
    assert dumped == raw

    assert mr.schema(Container) is mr.schema(Container)


def test_custom_name() -> None:
    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class BoolContainer:
        bool_field: bool = dataclasses.field(metadata=mr.metadata(name="BoolField"))

    raw = dict(BoolField=False)

    loaded = mr.load(BoolContainer, raw)
    dumped = mr.dump(loaded)

    assert loaded == BoolContainer(bool_field=False)
    assert dumped == raw

    assert mr.schema(BoolContainer) is mr.schema(BoolContainer)


def test_unknown_field() -> None:
    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class BoolContainer:
        bool_field: bool

    loaded = mr.load(BoolContainer, dict(bool_field=True, int_field=42))
    dumped = mr.dump(loaded)

    assert loaded == BoolContainer(bool_field=True)
    assert dumped == dict(bool_field=True)

    assert mr.schema(BoolContainer) is mr.schema(BoolContainer)


def test_schema_with_default_case():
    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class DataClass:
        str_field: str

    origin = dict(str_field="foobar")
    loaded = mr.load(DataClass, origin, naming_case=mr.DEFAULT_CASE)
    dumped = mr.dump(loaded, naming_case=mr.DEFAULT_CASE)

    assert loaded == DataClass(str_field="foobar")
    assert dumped == origin


def test_schema_with_capital_camel_case():
    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class DataClass:
        str_field: str

    origin = dict(StrField="foobar")
    loaded = mr.load(DataClass, origin, naming_case=mr.CAPITAL_CAMEL_CASE)
    dumped = mr.dump(loaded, naming_case=mr.CAPITAL_CAMEL_CASE)

    assert loaded == DataClass(str_field="foobar")
    assert dumped == origin


def test_schema_with_camel_case():
    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class DataClass:
        str_field: str

    origin = dict(strField="foobar")
    loaded = mr.load(DataClass, origin, naming_case=mr.CAMEL_CASE)
    dumped = mr.dump(loaded, naming_case=mr.CAMEL_CASE)

    assert loaded == DataClass(str_field="foobar")
    assert dumped == origin


@pytest.mark.parametrize(
    "raw, dt",
    [
        ("2022-02-20T11:33:48.607289+00:00", datetime.datetime(2022, 2, 20, 11, 33, 48, 607289, datetime.timezone.utc)),
        ("2022-02-20T11:33:48.607289", datetime.datetime(2022, 2, 20, 11, 33, 48, 607289, datetime.timezone.utc)),
    ],
)
def test_datetime_field_load(raw: str, dt: datetime.datetime) -> None:
    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class DateTimeContainer:
        datetime_field: datetime.datetime

    loaded = mr.load(DateTimeContainer, dict(datetime_field=raw))
    assert loaded == DateTimeContainer(datetime_field=dt)


@pytest.mark.parametrize(
    "dt, raw",
    [
        (datetime.datetime(2022, 2, 20, 11, 33, 48, 607289, datetime.timezone.utc), "2022-02-20T11:33:48.607289+00:00"),
        (datetime.datetime(2022, 2, 20, 11, 33, 48, 607289, None), "2022-02-20T11:33:48.607289+00:00"),
    ],
)
def test_datetime_field_dump(dt: datetime.datetime, raw: str) -> None:
    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class DateTimeContainer:
        datetime_field: datetime.datetime

    dumped = mr.dump(DateTimeContainer(datetime_field=dt))
    assert dumped == dict(datetime_field=raw)


@pytest.mark.parametrize(
    "value, raw",
    [
        (Parity.ODD, "ODD"),
        (Parity.EVEN, "EVEN"),
    ],
)
def test_enum_field_dump(value: Parity, raw: str) -> None:
    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class EnumContainer:
        enum_field: Parity

    dumped = mr.dump(EnumContainer(enum_field=value))
    assert dumped == dict(enum_field=raw)


@pytest.mark.parametrize(
    "raw, value",
    [
        ("ODD", Parity.ODD),
        ("EVEN", Parity.EVEN),
    ],
)
def test_enum_field_load(value: Parity, raw: str) -> None:
    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class EnumContainer:
        enum_field: Parity

    dumped = mr.load(EnumContainer, dict(enum_field=raw))
    assert dumped == EnumContainer(enum_field=value)


@pytest.mark.skip("Bug in marshmallow")
def test_dump_invalid_int_value():
    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class IntContainer:
        int_field: int

    with pytest.raises(m.ValidationError):
        mr.dump(IntContainer(int_field=cast(int, "invalid")))


def test_dump_invalid_value():
    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class UUIDContainer:
        uuid_field: uuid.UUID

    with pytest.raises(m.ValidationError) as exc_info:
        mr.dump(UUIDContainer(uuid_field=cast(uuid.UUID, "invalid")))

    assert exc_info.value.messages == {"uuid_field": ["Not a valid UUID."]}


def test_dump_many_invalid_value():
    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class UUIDContainer:
        uuid_field: uuid.UUID

    with pytest.raises(m.ValidationError) as exc_info:
        mr.dump_many([UUIDContainer(uuid_field=cast(uuid.UUID, "invalid"))])

    assert exc_info.value.messages == {0: {"uuid_field": ["Not a valid UUID."]}}
