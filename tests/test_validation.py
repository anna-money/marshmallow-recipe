import dataclasses
import datetime
import decimal
import uuid
from typing import cast

import marshmallow as m
import pytest

import marshmallow_recipe as mr


def test_int_validation() -> None:
    @dataclasses.dataclass
    class Holder:
        value: int = dataclasses.field(metadata=mr.metadata(validate=lambda x: x != 0))

    with pytest.raises(m.ValidationError):
        mr.load(Holder, dict(value=0))

    mr.load(Holder, dict(value=42))


def test_float_validation() -> None:
    @dataclasses.dataclass
    class Holder:
        value: float = dataclasses.field(metadata=mr.metadata(validate=lambda x: x != 0))

    with pytest.raises(m.ValidationError):
        mr.load(Holder, dict(value=0))

    mr.load(Holder, dict(value=42))


def test_decimal_validation() -> None:
    @dataclasses.dataclass
    class Holder:
        value: decimal.Decimal = dataclasses.field(metadata=mr.metadata(validate=lambda x: x != 0))

    with pytest.raises(m.ValidationError):
        mr.load(Holder, dict(value="0"))

    mr.load(Holder, dict(value="42"))


def test_str_validation() -> None:
    @dataclasses.dataclass
    class Holder:
        value: str = dataclasses.field(metadata=mr.metadata(validate=lambda x: x != ""))

    with pytest.raises(m.ValidationError):
        mr.load(Holder, dict(value=""))

    mr.load(Holder, dict(value="42"))


def test_bool_validation() -> None:
    @dataclasses.dataclass
    class Holder:
        value: bool = dataclasses.field(metadata=mr.metadata(validate=lambda x: x is True))

    with pytest.raises(m.ValidationError):
        mr.load(Holder, dict(value="False"))

    mr.load(Holder, dict(value="True"))


def test_uuid_validation() -> None:
    invalid = uuid.uuid4()

    @dataclasses.dataclass
    class Holder:
        value: uuid.UUID = dataclasses.field(metadata=mr.metadata(validate=lambda x: x != invalid))

    with pytest.raises(m.ValidationError):
        mr.load(Holder, dict(value=str(invalid)))

    mr.load(Holder, dict(value=str(uuid.uuid4())))


def test_date_validation() -> None:
    invalid = datetime.date.today()

    @dataclasses.dataclass
    class Holder:
        value: datetime.date = dataclasses.field(metadata=mr.metadata(validate=lambda x: x != invalid))

    with pytest.raises(m.ValidationError):
        mr.load(Holder, dict(value=invalid.isoformat()))

    mr.load(Holder, dict(value=datetime.date(2001, 1, 2).isoformat()))


def test_datetime_validation() -> None:
    invalid = datetime.datetime.now().astimezone(datetime.timezone.utc)

    @dataclasses.dataclass
    class Holder:
        value: datetime.datetime = dataclasses.field(metadata=mr.metadata(validate=lambda x: x != invalid))

    with pytest.raises(m.ValidationError):
        mr.load(Holder, dict(value=invalid.isoformat()))

    mr.load(Holder, dict(value=datetime.datetime(2001, 1, 2).isoformat()))


def test_none_validation_with_default() -> None:
    @dataclasses.dataclass
    class Holder:
        value: str = "default"

    with pytest.raises(m.ValidationError):
        mr.load(Holder, dict(value=None))

    @dataclasses.dataclass
    class HolderWithNone:
        value: str | None = "default"

    mr.load(HolderWithNone, dict(value=None))


def test_list_item_validation() -> None:
    @dataclasses.dataclass
    class Holder:
        items: list[str] = dataclasses.field(metadata=mr.list_metadata(validate_item=lambda x: bool(x)))

    with pytest.raises(m.ValidationError):
        mr.load(Holder, dict(items=[""]))

    assert mr.load(Holder, dict(items=["1"])) == Holder(items=["1"])


def test_dump_invalid_value() -> None:
    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class UUIDContainer:
        uuid_field: uuid.UUID

    with pytest.raises(m.ValidationError) as exc_info:
        mr.dump(UUIDContainer(uuid_field=cast(uuid.UUID, "invalid")))

    assert exc_info.value.messages == {"uuid_field": ["Not a valid UUID."]}

    with pytest.raises(m.ValidationError) as exc_info:
        mr.dump(UUIDContainer(uuid_field=cast(uuid.UUID, None)))

    assert exc_info.value.messages == {"uuid_field": ["Missing data for required field."]}


def test_dump_many_invalid_value() -> None:
    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class UUIDContainer:
        uuid_field: uuid.UUID

    with pytest.raises(m.ValidationError) as exc_info:
        mr.dump_many([UUIDContainer(uuid_field=cast(uuid.UUID, "invalid"))])

    assert exc_info.value.messages == {0: {"uuid_field": ["Not a valid UUID."]}}

    with pytest.raises(m.ValidationError) as exc_info:
        mr.dump_many([UUIDContainer(uuid_field=cast(uuid.UUID, None))])

    assert exc_info.value.messages == {0: {"uuid_field": ["Missing data for required field."]}}


def test_dict_with_complex_value_load_fail() -> None:
    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class Container:
        values: dict[datetime.date, decimal.Decimal]

    with pytest.raises(m.ValidationError) as e:
        mr.load(Container, {"values": {"invalid": "invalid"}})

    assert e.value.messages == {"values": {"invalid": {"key": ["Not a valid date."], "value": ["Not a valid number."]}}}

    with pytest.raises(m.ValidationError) as e:
        mr.load(Container, {"values": None})

    assert e.value.messages == {"values": ["Field may not be null."]}

    with pytest.raises(m.ValidationError) as e:
        mr.load(Container, {"values": {"invalid": "invalid", "2020-01-01": 42}})

    assert e.value.messages == {"values": {"invalid": {"key": ["Not a valid date."], "value": ["Not a valid number."]}}}


@pytest.mark.skip("Bug in marshmallow")
def test_dump_invalid_int_value() -> None:
    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class IntContainer:
        int_field: int

    with pytest.raises(m.ValidationError):
        mr.dump(IntContainer(int_field=cast(int, "invalid")))
