import abc
import dataclasses
import datetime
import decimal
import enum
import json
import uuid
from collections.abc import Mapping, Sequence
from typing import Annotated, Any, NewType

import marshmallow
import pytest

import marshmallow_recipe as mr


class Serializer(abc.ABC):
    __slots__ = ()

    @property
    @abc.abstractmethod
    def supports_pre_load(self) -> bool:
        raise NotImplementedError

    @property
    def supports_many(self) -> bool:
        return False

    @property
    def supports_special_float_validation(self) -> bool:
        return True

    @property
    def supports_cyclic(self) -> bool:
        return True

    @property
    def supports_proper_validation_errors_on_dump(self) -> bool:
        return True

    @abc.abstractmethod
    def dump[T](
        self,
        schema_class: type[T],
        obj: T,
        naming_case: mr.NamingCase | None = None,
        none_value_handling: mr.NoneValueHandling | None = None,
        decimal_places: int | None = mr.MISSING,
        encoding: str = "utf-8",
    ) -> bytes:
        raise NotImplementedError

    def dump_many[T](
        self,
        schema_class: type[T],
        objs: list[T],
        naming_case: mr.NamingCase | None = None,
        none_value_handling: mr.NoneValueHandling | None = None,
        decimal_places: int | None = mr.MISSING,
    ) -> bytes:
        raise NotImplementedError

    @abc.abstractmethod
    def load[T](
        self,
        schema_class: type[T],
        data: bytes,
        naming_case: mr.NamingCase | None = None,
        decimal_places: int | None = mr.MISSING,
        encoding: str = "utf-8",
    ) -> T:
        raise NotImplementedError

    def load_many[T](
        self,
        schema_class: type[T],
        data: bytes,
        naming_case: mr.NamingCase | None = None,
        decimal_places: int | None = mr.MISSING,
    ) -> list[T]:
        raise NotImplementedError


class MarshmallowSerializer(Serializer):
    __slots__ = ()

    @property
    def supports_pre_load(self) -> bool:
        return True

    @property
    def supports_many(self) -> bool:
        return True

    @property
    def supports_proper_validation_errors_on_dump(self) -> bool:
        return False

    def dump[T](
        self,
        schema_class: type[T],
        obj: T,
        naming_case: mr.NamingCase | None = None,
        none_value_handling: mr.NoneValueHandling | None = None,
        decimal_places: int | None = mr.MISSING,
        encoding: str = "utf-8",
    ) -> bytes:
        result = mr.dump(
            schema_class,
            obj,
            naming_case=naming_case,
            none_value_handling=none_value_handling,
            decimal_places=decimal_places,
        )
        return json.dumps(result, separators=(",", ":")).encode(encoding)

    def dump_many[T](
        self,
        schema_class: type[T],
        objs: list[T],
        naming_case: mr.NamingCase | None = None,
        none_value_handling: mr.NoneValueHandling | None = None,
        decimal_places: int | None = mr.MISSING,
    ) -> bytes:
        result = mr.dump_many(
            schema_class,
            objs,
            naming_case=naming_case,
            none_value_handling=none_value_handling,
            decimal_places=decimal_places,
        )
        return json.dumps(result, separators=(",", ":")).encode()

    def load[T](
        self,
        schema_class: type[T],
        data: bytes,
        naming_case: mr.NamingCase | None = None,
        decimal_places: int | None = mr.MISSING,
        encoding: str = "utf-8",
    ) -> T:
        return mr.load(
            schema_class, json.loads(data.decode(encoding)), naming_case=naming_case, decimal_places=decimal_places
        )

    def load_many[T](
        self,
        schema_class: type[T],
        data: bytes,
        naming_case: mr.NamingCase | None = None,
        decimal_places: int | None = mr.MISSING,
    ) -> list[T]:
        return mr.load_many(schema_class, json.loads(data), naming_case=naming_case, decimal_places=decimal_places)


class NukedSerializer(Serializer):
    __slots__ = ()

    @property
    def supports_pre_load(self) -> bool:
        return False

    @property
    def supports_cyclic(self) -> bool:
        return False

    def dump[T](
        self,
        schema_class: type[T],
        obj: T,
        naming_case: mr.NamingCase | None = None,
        none_value_handling: mr.NoneValueHandling | None = None,
        decimal_places: int | None = mr.MISSING,
        encoding: str = "utf-8",
    ) -> bytes:
        result = mr.nuked.dump(
            schema_class,
            obj,
            naming_case=naming_case,
            none_value_handling=none_value_handling,
            decimal_places=decimal_places if decimal_places is not mr.MISSING else None,
        )
        return json.dumps(result, separators=(",", ":")).encode(encoding)

    def load[T](
        self,
        schema_class: type[T],
        data: bytes,
        naming_case: mr.NamingCase | None = None,
        decimal_places: int | None = mr.MISSING,
        encoding: str = "utf-8",
    ) -> T:
        return mr.nuked.load(
            schema_class,
            json.loads(data.decode(encoding)),
            naming_case=naming_case,
            decimal_places=decimal_places if decimal_places is not mr.MISSING else None,
        )


@pytest.fixture(params=[MarshmallowSerializer(), NukedSerializer()], ids=["marshmallow", "nuked"])
def impl(request: pytest.FixtureRequest) -> Serializer:
    return request.param


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class ValueOf[T]:
    value: T


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class OptionalValueOf[T]:
    value: T | None = None


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
class WithIntTwoValidators:
    value: int = dataclasses.field(metadata=mr.meta(validate=[lambda x: x > 0, lambda x: x < 100]))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithFloatValidation:
    value: float = dataclasses.field(metadata=mr.meta(validate=lambda x: x >= 0.0))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithFloatTwoValidators:
    value: float = dataclasses.field(metadata=mr.meta(validate=[lambda x: x >= 0.0, lambda x: x <= 100.0]))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithStrValidation:
    value: str = dataclasses.field(metadata=mr.meta(validate=lambda x: len(x) > 0))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithStrTwoValidators:
    value: str = dataclasses.field(metadata=mr.meta(validate=[lambda x: len(x) > 0, lambda x: len(x) < 100]))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithBoolValidation:
    value: bool = dataclasses.field(metadata=mr.meta(validate=lambda x: x is True))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithBoolTwoValidators:
    value: bool = dataclasses.field(metadata=mr.meta(validate=[lambda x: x is not None, lambda x: x is True]))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithDecimalValidation:
    value: decimal.Decimal = dataclasses.field(metadata=mr.meta(validate=lambda x: x > decimal.Decimal("0")))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithDecimalTwoValidators:
    value: decimal.Decimal = dataclasses.field(
        metadata=mr.meta(validate=[lambda x: x > decimal.Decimal("0"), lambda x: x < decimal.Decimal("1000")])
    )


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithListItemValidation:
    items: list[int] = dataclasses.field(metadata=mr.list_meta(validate_item=lambda x: x > 0))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithListItemTwoValidators:
    items: list[int] = dataclasses.field(metadata=mr.list_meta(validate_item=[lambda x: x > 0, lambda x: x < 100]))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithSetItemValidation:
    tags: set[str] = dataclasses.field(metadata=mr.set_meta(validate_item=lambda x: len(x) > 0))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithSetItemTwoValidators:
    tags: set[str] = dataclasses.field(
        metadata=mr.set_meta(validate_item=[lambda x: len(x) > 0, lambda x: len(x) < 50])
    )


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithTupleItemValidation:
    values: tuple[int, ...] = dataclasses.field(metadata=mr.tuple_meta(validate_item=lambda x: x != 0))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithTupleItemTwoValidators:
    values: tuple[int, ...] = dataclasses.field(
        metadata=mr.tuple_meta(validate_item=[lambda x: x > 0, lambda x: x < 100])
    )


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithFrozenSetItemValidation:
    codes: frozenset[str] = dataclasses.field(metadata=mr.frozenset_meta(validate_item=lambda x: len(x) == 3))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithFrozenSetItemTwoValidators:
    codes: frozenset[str] = dataclasses.field(
        metadata=mr.frozenset_meta(validate_item=[lambda x: len(x) >= 2, lambda x: len(x) <= 5])
    )


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithPostLoadTransform:
    name: str = dataclasses.field(metadata=mr.str_meta(post_load=str.upper))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithPostLoadAndStrip:
    value: str = dataclasses.field(metadata=mr.str_meta(strip_whitespaces=True, post_load=str.lower))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithDecimalNoPlaces:
    value: decimal.Decimal = dataclasses.field(metadata=mr.decimal_meta(places=None))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithDecimalPlacesZero:
    value: decimal.Decimal = dataclasses.field(metadata=mr.decimal_meta(places=0))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithDecimalPlacesAndRange:
    value: decimal.Decimal = dataclasses.field(
        metadata=mr.decimal_meta(places=2, validate=lambda x: decimal.Decimal("0") < x < decimal.Decimal("100"))
    )


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithDecimalRoundUp:
    value: decimal.Decimal = dataclasses.field(metadata=mr.decimal_meta(places=2, rounding=decimal.ROUND_UP))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithDecimalRoundDown:
    value: decimal.Decimal = dataclasses.field(metadata=mr.decimal_meta(places=2, rounding=decimal.ROUND_DOWN))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithDecimalRoundCeiling:
    value: decimal.Decimal = dataclasses.field(metadata=mr.decimal_meta(places=2, rounding=decimal.ROUND_CEILING))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithDecimalRoundFloor:
    value: decimal.Decimal = dataclasses.field(metadata=mr.decimal_meta(places=2, rounding=decimal.ROUND_FLOOR))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithDecimalRoundHalfUp:
    value: decimal.Decimal = dataclasses.field(metadata=mr.decimal_meta(places=2, rounding=decimal.ROUND_HALF_UP))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithDecimalRoundHalfDown:
    value: decimal.Decimal = dataclasses.field(metadata=mr.decimal_meta(places=2, rounding=decimal.ROUND_HALF_DOWN))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithDecimalRoundHalfEven:
    value: decimal.Decimal = dataclasses.field(metadata=mr.decimal_meta(places=2, rounding=decimal.ROUND_HALF_EVEN))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithAnnotatedDecimalPlaces:
    value: Annotated[decimal.Decimal, mr.decimal_metadata(places=4)]


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithAnnotatedDecimalRounding:
    value: Annotated[decimal.Decimal, mr.decimal_metadata(places=2, rounding=decimal.ROUND_UP)]


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithDateTimeCustomFormat:
    scheduled_at: datetime.datetime = dataclasses.field(metadata=mr.datetime_meta(format="%Y/%m/%d"))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithDateTimeCustomFormatFull:
    created_at: datetime.datetime = dataclasses.field(metadata=mr.datetime_meta(format="%Y-%m-%d %H:%M:%S"))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithDateTimeCustomFormatTimezone:
    created_at: datetime.datetime = dataclasses.field(metadata=mr.datetime_meta(format="%Y-%m-%dT%H:%M:%S%z"))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithDateTimeFormatIsoZ:
    created_at: datetime.datetime = dataclasses.field(metadata=mr.datetime_meta(format="%Y-%m-%dT%H:%M:%SZ"))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithDateTimeFormatIsoMicroseconds:
    created_at: datetime.datetime = dataclasses.field(metadata=mr.datetime_meta(format="%Y-%m-%dT%H:%M:%S.%f"))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithDateTimeFormatIsoMicrosecondsZ:
    created_at: datetime.datetime = dataclasses.field(metadata=mr.datetime_meta(format="%Y-%m-%dT%H:%M:%S.%fZ"))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithDateTimeFormatIsoNoTz:
    created_at: datetime.datetime = dataclasses.field(metadata=mr.datetime_meta(format="%Y-%m-%dT%H:%M:%S"))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithDateTimeFormatHumanReadable:
    created_at: datetime.datetime = dataclasses.field(metadata=mr.datetime_meta(format="%d %B %Y"))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithDateTimeFormatDateOnly:
    created_at: datetime.datetime = dataclasses.field(metadata=mr.datetime_meta(format="%Y-%m-%d"))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithDateTimeFormatIso:
    created_at: datetime.datetime = dataclasses.field(metadata=mr.datetime_meta(format="iso"))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithDateTimeFormatTimestamp:
    created_at: datetime.datetime = dataclasses.field(metadata=mr.datetime_meta(format="timestamp"))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithCustomRequiredError:
    name: str = dataclasses.field(metadata=mr.str_meta(required_error="Custom required message"))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithCustomInvalidError:
    age: int = dataclasses.field(metadata=mr.meta(invalid_error="Custom invalid message"))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithCustomNoneError:
    value: str = dataclasses.field(metadata=mr.str_meta(none_error="Custom none message"))


@dataclasses.dataclass(slots=True, kw_only=True)
class WithAnyField:
    data: Any = None
    name: str = ""


@dataclasses.dataclass(slots=True, kw_only=True)
class WithRequiredAny:
    data: Any
    name: str


@dataclasses.dataclass(slots=True, kw_only=True)
class WithListAny:
    items: list[Any]
    name: str = ""


@dataclasses.dataclass(slots=True, kw_only=True)
class WithDictAny:
    data: dict[str, Any]
    name: str = ""


@dataclasses.dataclass(slots=True, kw_only=True)
class WithAnyNamingCase:
    any_data: Any = None
    field_name: str = ""


@dataclasses.dataclass(slots=True, kw_only=True)
class WithAnyValidation:
    data: Any = dataclasses.field(metadata=mr.meta(validate=lambda x: isinstance(x, str)))


@dataclasses.dataclass(slots=True, kw_only=True)
class WithAnyTwoValidators:
    data: Any = dataclasses.field(metadata=mr.meta(validate=[lambda x: x is not None, lambda x: isinstance(x, str)]))


@dataclasses.dataclass(slots=True, kw_only=True)
class WithAnyMissing:
    data: Any = mr.MISSING
    name: str = ""


@dataclasses.dataclass(slots=True, kw_only=True)
class WithAnyDefault:
    data: Any = "default_value"
    name: str = ""


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class CollectionHolder[T]:
    items: T


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class ListOf[T]:
    items: list[T]


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class DictOf[K, V]:
    data: dict[K, V]


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class SetOf[T]:
    items: set[T]


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class FrozenSetOf[T]:
    items: frozenset[T]


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class TupleOf[T]:
    items: tuple[T, ...]


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class SequenceOf[T]:
    items: Sequence[T]


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class MappingOf[K, V]:
    data: Mapping[K, V]


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class OptionalListOf[T]:
    items: list[T] | None = None


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class OptionalDictOf[K, V]:
    data: dict[K, V] | None = None


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class OptionalSetOf[T]:
    items: set[T] | None = None


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class OptionalFrozenSetOf[T]:
    items: frozenset[T] | None = None


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class OptionalTupleOf[T]:
    items: tuple[T, ...] | None = None


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class OptionalSequenceOf[T]:
    items: Sequence[T] | None = None


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class OptionalMappingOf[K, V]:
    data: Mapping[K, V] | None = None


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithSequenceValidation:
    items: Sequence[int] = dataclasses.field(metadata=mr.sequence_meta(validate_item=lambda x: x > 0))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithSequenceTwoValidators:
    items: Sequence[int] = dataclasses.field(
        metadata=mr.sequence_meta(validate_item=[lambda x: x > 0, lambda x: x < 100])
    )


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithStrDefault:
    value: str = "default"


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithIntDefault:
    value: int = 42


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithBoolDefault:
    value: bool = True


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithFloatDefault:
    value: float = 3.14


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithStrRequiredError:
    value: str = dataclasses.field(metadata=mr.str_meta(required_error="Custom required message"))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithStrNoneError:
    value: str = dataclasses.field(metadata=mr.str_meta(none_error="Custom none message"))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithIntInvalidError:
    value: int = dataclasses.field(metadata=mr.meta(invalid_error="Custom invalid message"))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithStrInvalidError:
    value: str = dataclasses.field(metadata=mr.str_meta(invalid_error="Custom invalid message"))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithIntRequiredError:
    value: int = dataclasses.field(metadata=mr.meta(required_error="Custom required message"))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithIntNoneError:
    value: int = dataclasses.field(metadata=mr.meta(none_error="Custom none message"))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithFloatRequiredError:
    value: float = dataclasses.field(metadata=mr.meta(required_error="Custom required message"))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithFloatNoneError:
    value: float = dataclasses.field(metadata=mr.meta(none_error="Custom none message"))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithFloatInvalidError:
    value: float = dataclasses.field(metadata=mr.meta(invalid_error="Custom invalid message"))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithBoolRequiredError:
    value: bool = dataclasses.field(metadata=mr.meta(required_error="Custom required message"))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithBoolNoneError:
    value: bool = dataclasses.field(metadata=mr.meta(none_error="Custom none message"))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithBoolInvalidError:
    value: bool = dataclasses.field(metadata=mr.meta(invalid_error="Custom invalid message"))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithDecimalRequiredError:
    value: decimal.Decimal = dataclasses.field(metadata=mr.decimal_meta(required_error="Custom required message"))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithDecimalNoneError:
    value: decimal.Decimal = dataclasses.field(metadata=mr.decimal_meta(none_error="Custom none message"))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithDecimalInvalidError:
    value: decimal.Decimal = dataclasses.field(metadata=mr.decimal_meta(invalid_error="Custom invalid message"))


# Validation and custom errors for uuid
@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithUuidValidation:
    value: uuid.UUID = dataclasses.field(metadata=mr.meta(validate=lambda x: x.version == 4))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithUuidTwoValidators:
    value: uuid.UUID = dataclasses.field(
        metadata=mr.meta(validate=[lambda x: x.version == 4, lambda x: str(x).startswith("a")])
    )


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithUuidRequiredError:
    value: uuid.UUID = dataclasses.field(metadata=mr.meta(required_error="Custom required message"))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithUuidNoneError:
    value: uuid.UUID = dataclasses.field(metadata=mr.meta(none_error="Custom none message"))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithUuidInvalidError:
    value: uuid.UUID = dataclasses.field(metadata=mr.meta(invalid_error="Custom invalid message"))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithDatetimeValidation:
    value: datetime.datetime = dataclasses.field(metadata=mr.datetime_meta(validate=lambda x: x.year >= 2000))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithDatetimeTwoValidators:
    value: datetime.datetime = dataclasses.field(
        metadata=mr.datetime_meta(validate=[lambda x: x.year >= 2000, lambda x: x.year <= 2100])
    )


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithDatetimeRequiredError:
    value: datetime.datetime = dataclasses.field(metadata=mr.datetime_meta(required_error="Custom required message"))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithDatetimeNoneError:
    value: datetime.datetime = dataclasses.field(metadata=mr.datetime_meta(none_error="Custom none message"))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithDatetimeInvalidError:
    value: datetime.datetime = dataclasses.field(metadata=mr.datetime_meta(invalid_error="Custom invalid message"))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithDateValidation:
    value: datetime.date = dataclasses.field(metadata=mr.meta(validate=lambda x: x.year >= 2000))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithDateTwoValidators:
    value: datetime.date = dataclasses.field(
        metadata=mr.meta(validate=[lambda x: x.year >= 2000, lambda x: x.year <= 2100])
    )


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithDateRequiredError:
    value: datetime.date = dataclasses.field(metadata=mr.meta(required_error="Custom required message"))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithDateNoneError:
    value: datetime.date = dataclasses.field(metadata=mr.meta(none_error="Custom none message"))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithDateInvalidError:
    value: datetime.date = dataclasses.field(metadata=mr.meta(invalid_error="Custom invalid message"))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithTimeValidation:
    value: datetime.time = dataclasses.field(metadata=mr.time_metadata(validate=lambda x: x.hour >= 9 and x.hour < 18))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithTimeTwoValidators:
    value: datetime.time = dataclasses.field(
        metadata=mr.time_metadata(validate=[lambda x: x.hour >= 9, lambda x: x.hour < 18])
    )


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithTimeRequiredError:
    value: datetime.time = dataclasses.field(metadata=mr.time_metadata(required_error="Custom required message"))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithTimeNoneError:
    value: datetime.time = dataclasses.field(metadata=mr.time_metadata(none_error="Custom none message"))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithTimeInvalidError:
    value: datetime.time = dataclasses.field(metadata=mr.time_metadata(invalid_error="Custom invalid message"))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithListRequiredError:
    items: list[int] = dataclasses.field(metadata=mr.list_meta(required_error="Custom required message"))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithListNoneError:
    items: list[int] = dataclasses.field(metadata=mr.list_meta(none_error="Custom none message"))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithListInvalidError:
    items: list[int] = dataclasses.field(metadata=mr.list_meta(invalid_error="Custom invalid message"))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithSetRequiredError:
    items: set[int] = dataclasses.field(metadata=mr.set_meta(required_error="Custom required message"))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithSetNoneError:
    items: set[int] = dataclasses.field(metadata=mr.set_meta(none_error="Custom none message"))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithSetInvalidError:
    items: set[int] = dataclasses.field(metadata=mr.set_meta(invalid_error="Custom invalid message"))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithTupleRequiredError:
    items: tuple[int, ...] = dataclasses.field(metadata=mr.tuple_meta(required_error="Custom required message"))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithTupleNoneError:
    items: tuple[int, ...] = dataclasses.field(metadata=mr.tuple_meta(none_error="Custom none message"))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithTupleInvalidError:
    items: tuple[int, ...] = dataclasses.field(metadata=mr.tuple_meta(invalid_error="Custom invalid message"))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithFrozenSetRequiredError:
    items: frozenset[int] = dataclasses.field(metadata=mr.frozenset_meta(required_error="Custom required message"))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithFrozenSetNoneError:
    items: frozenset[int] = dataclasses.field(metadata=mr.frozenset_meta(none_error="Custom none message"))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithFrozenSetInvalidError:
    items: frozenset[int] = dataclasses.field(metadata=mr.frozenset_meta(invalid_error="Custom invalid message"))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithSequenceRequiredError:
    items: Sequence[int] = dataclasses.field(metadata=mr.sequence_meta(required_error="Custom required message"))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithSequenceNoneError:
    items: Sequence[int] = dataclasses.field(metadata=mr.sequence_meta(none_error="Custom none message"))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithSequenceInvalidError:
    items: Sequence[int] = dataclasses.field(metadata=mr.sequence_meta(invalid_error="Custom invalid message"))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithDictRequiredError:
    data: dict[str, int] = dataclasses.field(metadata=mr.meta(required_error="Custom required message"))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithDictNoneError:
    data: dict[str, int] = dataclasses.field(metadata=mr.meta(none_error="Custom none message"))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithDictInvalidError:
    data: dict[str, int] = dataclasses.field(metadata=mr.meta(invalid_error="Custom invalid message"))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithMappingRequiredError:
    data: Mapping[str, int] = dataclasses.field(metadata=mr.meta(required_error="Custom required message"))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithMappingNoneError:
    data: Mapping[str, int] = dataclasses.field(metadata=mr.meta(none_error="Custom none message"))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithMappingInvalidError:
    data: Mapping[str, int] = dataclasses.field(metadata=mr.meta(invalid_error="Custom invalid message"))


def _address_city_validator(address: Address) -> bool:
    if not address.city:
        raise marshmallow.ValidationError({"city": ["City cannot be empty"]})
    return True


def _address_zip_validator(address: Address) -> bool:
    if len(address.zip_code) != 5:
        raise marshmallow.ValidationError({"zip_code": ["Zip code must be 5 characters"]})
    return True


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class PersonWithAddressValidation:
    name: str
    address: Annotated[Address, mr.metadata(validate=_address_city_validator)]


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class PersonWithAddressTwoValidators:
    name: str
    address: Annotated[Address, mr.metadata(validate=[_address_city_validator, _address_zip_validator])]


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithDictValidation:
    data: dict[str, int] = dataclasses.field(metadata=mr.meta(validate=lambda x: len(x) > 0))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithDictTwoValidators:
    data: dict[str, int] = dataclasses.field(metadata=mr.meta(validate=[lambda x: len(x) > 0, lambda x: len(x) < 10]))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithMappingValidation:
    data: Mapping[str, int] = dataclasses.field(metadata=mr.meta(validate=lambda x: len(x) > 0))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithMappingTwoValidators:
    data: Mapping[str, int] = dataclasses.field(
        metadata=mr.meta(validate=[lambda x: len(x) > 0, lambda x: len(x) < 10])
    )


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithStrEnumValidation:
    status: Status = dataclasses.field(metadata=mr.meta(validate=lambda x: x != Status.INACTIVE))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithStrEnumTwoValidators:
    status: Status = dataclasses.field(
        metadata=mr.meta(validate=[lambda x: x != Status.INACTIVE, lambda x: x == Status.ACTIVE])
    )


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithIntEnumValidation:
    priority: Priority = dataclasses.field(metadata=mr.meta(validate=lambda x: x.value >= 2))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithIntEnumTwoValidators:
    priority: Priority = dataclasses.field(metadata=mr.meta(validate=[lambda x: x.value >= 2, lambda x: x.value <= 2]))


NewInt = NewType("NewInt", int)


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithNewTypeValidation:
    value: NewInt = dataclasses.field(metadata=mr.meta(validate=lambda x: x > 0))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithNewTypeTwoValidators:
    value: NewInt = dataclasses.field(metadata=mr.meta(validate=[lambda x: x > 0, lambda x: x < 100]))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithStrMissing:
    value: str = mr.MISSING


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithIntMissing:
    value: int = mr.MISSING


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithFloatMissing:
    value: float = mr.MISSING


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithBoolMissing:
    value: bool = mr.MISSING


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithDecimalMissing:
    value: decimal.Decimal = mr.MISSING


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithDecimalDefault:
    value: decimal.Decimal = decimal.Decimal("99.99")


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithDateMissing:
    value: datetime.date = mr.MISSING


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithDatetimeMissing:
    value: datetime.datetime = mr.MISSING


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithTimeMissing:
    value: datetime.time = mr.MISSING


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithUuidMissing:
    value: uuid.UUID = mr.MISSING


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithStrEnumMissing:
    status: Status = mr.MISSING


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithIntEnumMissing:
    priority: Priority = mr.MISSING


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithNewTypeMissing:
    value: NewInt = mr.MISSING


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithListMissing:
    items: list[int] = mr.MISSING


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithSetMissing:
    items: set[int] = mr.MISSING


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithFrozenSetMissing:
    items: frozenset[int] = mr.MISSING


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithTupleMissing:
    items: tuple[int, ...] = mr.MISSING


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithSequenceMissing:
    items: Sequence[int] = mr.MISSING


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithDictMissing:
    data: dict[str, int] = mr.MISSING


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithMappingMissing:
    data: Mapping[str, int] = mr.MISSING


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithNestedMissing:
    address: Address = mr.MISSING


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithUnionMissing:
    value: int | str = mr.MISSING


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithUnionStrInt:
    value: str | int


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithUnionIntFloat:
    value: int | float


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithUnionFloatInt:
    value: float | int


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithUnionStrDict:
    value: str | dict[str, Any]


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithUnionDictStr:
    value: dict[str, Any] | str


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Cyclic:
    marker: str
    child: "Cyclic | None" = None


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class CyclicParent:
    marker: str
    child: "CyclicChild"


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class CyclicChild:
    marker: str
    parent: CyclicParent | None = None


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class IntContainerWithDefault:
    value: int = 42


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithNestedDefault:
    int_container: IntContainerWithDefault = dataclasses.field(default_factory=IntContainerWithDefault)


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithListStripWhitespace:
    items: list[Annotated[str, mr.str_meta(strip_whitespaces=True)]]


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Inner:
    x: int


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithOptionalStrStripWhitespace:
    value: str | None = dataclasses.field(default=None, metadata=mr.str_meta(strip_whitespaces=True))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithListPostLoad:
    items: list[Annotated[str, mr.str_meta(post_load=str.upper)]]


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithUnionDictDataclass:
    value: dict[str, Inner] | str


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithStrMinLength:
    value: str = dataclasses.field(metadata=mr.str_meta(min_length=3))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithStrMaxLength:
    value: str = dataclasses.field(metadata=mr.str_meta(max_length=5))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithStrRegexp:
    value: str = dataclasses.field(metadata=mr.str_meta(regexp=r"^\d+$"))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithStrMinLengthCustomError:
    value: str = dataclasses.field(metadata=mr.str_meta(min_length=3, min_length_error="Too short"))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithStrMaxLengthCustomError:
    value: str = dataclasses.field(metadata=mr.str_meta(max_length=5, max_length_error="Too long"))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithStrRegexpCustomError:
    value: str = dataclasses.field(metadata=mr.str_meta(regexp=r"^\d+$", regexp_error="Must be digits"))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithStrAllValidators:
    value: str = dataclasses.field(metadata=mr.str_meta(min_length=2, max_length=10, regexp=r"^[a-z]+$"))


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class WithStrValidatorsAndStrip:
    value: str = dataclasses.field(metadata=mr.str_meta(strip_whitespaces=True, min_length=2, max_length=10))
