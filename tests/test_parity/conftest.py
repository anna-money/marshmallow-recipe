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


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class GenericContainer[T]:
    items: list[T]


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class GenericValue[T]:
    value: T


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class GenericPair[T1, T2]:
    first: T1
    second: T2


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class GenericParentBase[T]:
    t1: T


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class GenericChildWithConcreteParent[T](GenericParentBase[int]):
    t2: T


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class NonGenericChildFromGenericParent(GenericParentBase[str]):
    extra: str


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Value1:
    v1: str


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Value2(Value1):
    v2: str


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class GenericWithIterable[TItem]:
    value: Value1
    iterable: list[TItem]


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class GenericWithFieldOverride[TValue, TItem](GenericWithIterable[TItem]):
    value: TValue  # type: ignore[assignment]
    iterable: set[TItem]  # type: ignore[assignment]


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class GenericResult[TValue]:
    success: bool
    value: TValue | None = None
    error: str | None = None


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class GenericApiResponse[T]:
    request_id: str
    result: GenericResult[T]


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class User:
    id: int
    name: str
    email: str


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class GenericWithDict[T]:
    lookup: dict[str, T]


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class GenericWithSet[T]:
    unique_items: set[T]


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class GenericWithAnnotated[T]:
    value: T
    custom_name: T = dataclasses.field(metadata=mr.meta(name="renamed_field"))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithIntValidation:
    value: int = dataclasses.field(metadata=mr.meta(validate=lambda x: x > 0))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithFloatValidation:
    value: float = dataclasses.field(metadata=mr.meta(validate=lambda x: x >= 0.0))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithStrValidation:
    value: str = dataclasses.field(metadata=mr.meta(validate=lambda x: len(x) > 0))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithEmailValidation:
    email: str = dataclasses.field(metadata=mr.str_meta(validate=mr.email_validate()))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithRegexValidation:
    code: str = dataclasses.field(metadata=mr.str_meta(validate=mr.regexp_validate(r"^[A-Z]{3}$")))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithDecimalValidation:
    value: decimal.Decimal = dataclasses.field(metadata=mr.meta(validate=lambda x: x > decimal.Decimal("0")))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithListItemValidation:
    items: list[int] = dataclasses.field(metadata=mr.list_meta(validate_item=lambda x: x > 0))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithSetItemValidation:
    tags: set[str] = dataclasses.field(metadata=mr.set_meta(validate_item=lambda x: len(x) > 0))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithTupleItemValidation:
    values: tuple[int, ...] = dataclasses.field(metadata=mr.tuple_meta(validate_item=lambda x: x != 0))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithPostLoadTransform:
    name: str = dataclasses.field(metadata=mr.str_meta(post_load=str.upper))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithPostLoadAndStrip:
    value: str = dataclasses.field(metadata=mr.str_meta(strip_whitespaces=True, post_load=str.lower))
