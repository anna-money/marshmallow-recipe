import dataclasses
import datetime
import decimal
import uuid
from typing import Annotated

import marshmallow as m
import pytest

import marshmallow_recipe as mr


def test_int_validation() -> None:
    @dataclasses.dataclass
    class Holder:
        value: int = dataclasses.field(metadata=mr.meta(validate=lambda x: x != 0))

    with pytest.raises(m.ValidationError):
        mr.load(Holder, dict(value=0))

    mr.load(Holder, dict(value=42))


def test_float_validation() -> None:
    @dataclasses.dataclass
    class Holder:
        value: float = dataclasses.field(metadata=mr.meta(validate=lambda x: x != 0))

    with pytest.raises(m.ValidationError):
        mr.load(Holder, dict(value=0))

    mr.load(Holder, dict(value=42))


def test_decimal_validation() -> None:
    @dataclasses.dataclass
    class Holder:
        value: decimal.Decimal = dataclasses.field(metadata=mr.meta(validate=lambda x: x != 0))

    with pytest.raises(m.ValidationError):
        mr.load(Holder, dict(value="0"))

    mr.load(Holder, dict(value="42"))


def test_str_validation() -> None:
    @dataclasses.dataclass
    class Holder:
        value: str = dataclasses.field(metadata=mr.meta(validate=lambda x: x != ""))

    with pytest.raises(m.ValidationError):
        mr.load(Holder, dict(value=""))

    mr.load(Holder, dict(value="42"))


def test_bool_validation() -> None:
    @dataclasses.dataclass
    class Holder:
        value: bool = dataclasses.field(metadata=mr.meta(validate=lambda x: x is True))

    with pytest.raises(m.ValidationError):
        mr.load(Holder, dict(value="False"))

    mr.load(Holder, dict(value="True"))


def test_uuid_validation() -> None:
    invalid = uuid.uuid4()

    @dataclasses.dataclass
    class Holder:
        value: uuid.UUID = dataclasses.field(metadata=mr.meta(validate=lambda x: x != invalid))

    with pytest.raises(m.ValidationError):
        mr.load(Holder, dict(value=str(invalid)))

    mr.load(Holder, dict(value=str(uuid.uuid4())))


def test_date_validation() -> None:
    invalid = datetime.date.today()

    @dataclasses.dataclass
    class Holder:
        value: datetime.date = dataclasses.field(metadata=mr.meta(validate=lambda x: x != invalid))

    with pytest.raises(m.ValidationError):
        mr.load(Holder, dict(value=invalid.isoformat()))

    mr.load(Holder, dict(value=datetime.date(2001, 1, 2).isoformat()))


def test_datetime_validation() -> None:
    invalid = datetime.datetime.now().astimezone(datetime.timezone.utc)

    @dataclasses.dataclass
    class Holder:
        value: datetime.datetime = dataclasses.field(metadata=mr.meta(validate=lambda x: x != invalid))

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
        items: list[str] = dataclasses.field(metadata=mr.list_meta(validate_item=lambda x: bool(x)))

    with pytest.raises(m.ValidationError):
        mr.load(Holder, dict(items=[""]))

    assert mr.load(Holder, dict(items=["1"])) == Holder(items=["1"])


def test_set_item_validation() -> None:
    @dataclasses.dataclass
    class Holder:
        items: set[str] = dataclasses.field(metadata=mr.set_meta(validate_item=lambda x: bool(x)))

    with pytest.raises(m.ValidationError):
        mr.load(Holder, dict(items=[""]))

    assert mr.load(Holder, dict(items=["1"])) == Holder(items={"1"})


def test_tuple_item_validation() -> None:
    @dataclasses.dataclass
    class Holder:
        items: tuple[str, ...] = dataclasses.field(metadata=mr.tuple_meta(validate_item=lambda x: bool(x)))

    with pytest.raises(m.ValidationError):
        mr.load(Holder, dict(items=[""]))

    assert mr.load(Holder, dict(items=["1"])) == Holder(items=("1",))


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


def test_regexp_validate() -> None:
    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class StrContainer:
        value1: Annotated[str, mr.str_meta(validate=mr.regexp_validate(r"^[a-z]+$"))]
        value2: Annotated[
            str, mr.str_meta(validate=mr.regexp_validate(r"^[a-z]+$", error="String does not match ^[a-z]+$."))
        ]

    with pytest.raises(m.ValidationError) as exc_info:
        mr.dump(StrContainer(value1="42", value2="100500"))

    assert exc_info.value.messages == {
        "value1": ["String does not match expected pattern."],
        "value2": ["String does not match ^[a-z]+$."],
    }


def test_validate() -> None:
    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class IntContainer:
        value: Annotated[
            int,
            mr.str_meta(
                validate=mr.validate(lambda x: x < 0, error="Should be negative."),
            ),
        ]

    with pytest.raises(m.ValidationError) as exc_info:
        mr.dump(IntContainer(value=42))

    assert exc_info.value.messages == {"value": ["Should be negative."]}


def test_get_field_errors() -> None:
    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class NestedContainer:
        value: int
        values: list[int]

    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class Container:
        value: int
        values: list[int]
        nested: NestedContainer

    with pytest.raises(mr.ValidationError) as exc_info:
        mr.load(
            Container,
            {"value": "invalid", "values": ["invalid"], "nested": {"value": "invalid", "values": ["invalid"]}},
        )

    assert mr.get_validation_field_errors(exc_info.value) == [
        mr.ValidationFieldError(
            name="nested",
            nested_errors=[
                mr.ValidationFieldError(name="value", error="Not a valid integer."),
                mr.ValidationFieldError(
                    name="values",
                    nested_errors=[mr.ValidationFieldError(name="0", error="Not a valid integer.")],
                ),
            ],
        ),
        mr.ValidationFieldError(name="value", error="Not a valid integer."),
        mr.ValidationFieldError(
            name="values",
            nested_errors=[mr.ValidationFieldError(name="0", error="Not a valid integer.")],
        ),
    ]


def test_email_validate() -> None:
    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class UserContact:
        email: Annotated[str, mr.str_meta(validate=mr.email_validate())]
        backup_email: Annotated[str, mr.str_meta(validate=mr.email_validate(error="Invalid backup email: {input}"))]

    # Valid emails
    user = UserContact(email="user@example.com", backup_email="backup@domain.org")
    assert mr.dump(user) == {"email": "user@example.com", "backup_email": "backup@domain.org"}
    assert mr.load(UserContact, {"email": "user@example.com", "backup_email": "backup@domain.org"}) == user

    # Valid email with plus addressing
    user = UserContact(email="test.user+tag@domain.co.uk", backup_email="backup@domain.org")
    assert mr.dump(user) == {"email": "test.user+tag@domain.co.uk", "backup_email": "backup@domain.org"}

    # Valid email with localhost
    user = UserContact(email="user@localhost", backup_email="backup@domain.org")
    assert mr.dump(user) == {"email": "user@localhost", "backup_email": "backup@domain.org"}

    # Invalid email - empty string
    with pytest.raises(m.ValidationError) as exc_info:
        mr.dump(UserContact(email="", backup_email="backup@domain.org"))
    assert exc_info.value.messages == {"email": ["Not a valid email address."]}

    # Invalid email - no @ sign
    with pytest.raises(m.ValidationError) as exc_info:
        mr.dump(UserContact(email="notanemail", backup_email="backup@domain.org"))
    assert exc_info.value.messages == {"email": ["Not a valid email address."]}

    # Invalid email - missing domain
    with pytest.raises(m.ValidationError) as exc_info:
        mr.dump(UserContact(email="user@", backup_email="backup@domain.org"))
    assert exc_info.value.messages == {"email": ["Not a valid email address."]}

    # Invalid email - missing user part
    with pytest.raises(m.ValidationError) as exc_info:
        mr.dump(UserContact(email="@domain.com", backup_email="backup@domain.org"))
    assert exc_info.value.messages == {"email": ["Not a valid email address."]}

    # Invalid email - quoted local-part
    with pytest.raises(m.ValidationError) as exc_info:
        mr.dump(UserContact(email='"very.unusual.@.unusual.com"@example.com', backup_email="backup@domain.org"))
    assert exc_info.value.messages == {"email": ["Not a valid email address."]}

    # Custom error message
    with pytest.raises(m.ValidationError) as exc_info:
        mr.dump(UserContact(email="user@example.com", backup_email="invalid"))
    assert exc_info.value.messages == {"backup_email": ["Invalid backup email: invalid"]}

    # Test with load
    with pytest.raises(m.ValidationError) as exc_info:
        mr.load(UserContact, {"email": "notanemail", "backup_email": "backup@domain.org"})
    assert exc_info.value.messages == {"email": ["Not a valid email address."]}


def test_email_validate_with_strip_whitespaces() -> None:
    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class CleanedUser:
        email: Annotated[str, mr.str_meta(strip_whitespaces=True, validate=mr.email_validate())]

    # Whitespace should be stripped before validation
    user = mr.load(CleanedUser, {"email": "  user@example.com  "})
    assert user.email == "user@example.com"

    dumped = mr.dump(user)
    assert dumped == {"email": "user@example.com"}
