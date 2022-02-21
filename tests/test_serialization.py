import dataclasses
import datetime
import decimal
import uuid
from typing import Any, cast

import marshmallow_recipe as mr


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
        datetime_tz_utc_field: datetime.datetime
        optional_datetime_tz_utc_field: datetime.datetime | None
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
        datetime_tz_utc_field="2022-02-20T11:33:48.607289+00:00",
        optional_datetime_tz_utc_field="2022-02-20T11:33:48.607289+00:00",
        datetime_field="2022-02-20T11:33:48.607289",
        optional_datetime_field="2022-02-20T11:33:48.607289",
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
        datetime_tz_utc_field=datetime.datetime(2022, 2, 20, 11, 33, 48, 607289),
        optional_datetime_tz_utc_field=datetime.datetime(2022, 2, 20, 11, 33, 48, 607289),
        datetime_field=datetime.datetime(2022, 2, 20, 11, 33, 48, 607289),
        optional_datetime_field=datetime.datetime(2022, 2, 20, 11, 33, 48, 607289),
        date_field=datetime.date(2022, 2, 20),
        optional_date_field=datetime.date(2022, 2, 20),
        dict_field=dict(key="value"),
        optional_dict_field=dict(key="value"),
    )
    assert dumped == {
        **raw,
        "datetime_tz_utc_field": cast(Any, "2022-02-20T11:33:48.607289"),
        "optional_datetime_tz_utc_field": cast(Any, "2022-02-20T11:33:48.607289"),
    }
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
