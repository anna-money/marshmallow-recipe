import dataclasses
import datetime
import decimal
import enum
import uuid

import marshmallow_recipe as mr


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class SimpleTypes:
    name: str
    age: int


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class AllPrimitives:
    str_field: str
    int_field: int
    float_field: float
    bool_field: bool
    decimal_field: decimal.Decimal
    uuid_field: uuid.UUID
    datetime_field: datetime.datetime
    date_field: datetime.date
    time_field: datetime.time


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithDecimal:
    value: decimal.Decimal


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithCollections:
    list_int: list[int]
    list_str: list[str]
    dict_str_int: dict[str, int]
    set_str: set[str]
    frozenset_int: frozenset[int]
    tuple_str: tuple[str, ...]


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Address:
    street: str
    city: str
    zip_code: str


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Person:
    name: str
    age: int
    address: Address


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Department:
    name: str
    head: Person


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Company:
    name: str
    department: Department


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithOptional:
    required: str
    optional_int: int | None = None
    optional_str: str | None = None


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithDefaults:
    name: str
    count: int = 42
    flag: bool = True
    items: list[str] = dataclasses.field(default_factory=list)
    tags: set[str] = dataclasses.field(default_factory=set)


class Status(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"


class Priority(int, enum.Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithEnums:
    status: Status
    priority: Priority
    optional_status: Status | None = None


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithUnion:
    value: int | str
    optional_value: int | str | None = None


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithSnakeCase:
    first_name: str
    last_name: str
    email_address: str


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class ForEdgeCases:
    text: str
    number: int
    small_float: float


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithStripWhitespace:
    name: str = dataclasses.field(metadata=mr.str_meta(strip_whitespaces=True))
    email: str = dataclasses.field(metadata=mr.str_meta(strip_whitespaces=True))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithCustomName:
    internal_id: int = dataclasses.field(metadata=mr.meta(name="id"))
    user_email: str = dataclasses.field(metadata=mr.meta(name="email"))
