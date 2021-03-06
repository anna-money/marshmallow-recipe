import dataclasses
import datetime
import decimal
import uuid

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
