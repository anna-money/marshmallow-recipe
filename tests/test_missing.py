import dataclasses
import datetime
import decimal
import enum
import uuid

import marshmallow_recipe as mr


def test_simple_types() -> None:
    class EnumType(str, enum.Enum):
        A = "A"
        B = "B"

        def __str__(self) -> str:
            return self.value

    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class TypeWithMissing:
        str_field: str = mr.MISSING
        int_field: int = mr.MISSING
        decimal_field: decimal.Decimal = mr.MISSING
        date_field: datetime.date = mr.MISSING
        datetime_field: datetime.datetime = mr.MISSING
        uuid_field: uuid.UUID = mr.MISSING
        bool_field: bool = mr.MISSING
        float_field: float = mr.MISSING
        enum_field: EnumType = mr.MISSING
        int_float_union: int | float = mr.MISSING
        str_bool_union: str | bool = mr.MISSING

    dumped = mr.dump(TypeWithMissing())
    assert dumped == {}
    loaded = mr.load(TypeWithMissing, dumped)
    assert loaded == TypeWithMissing()

    filled_data = TypeWithMissing(
        str_field="str_field",
        int_field=10,
        decimal_field=decimal.Decimal("1.12"),
        date_field=datetime.date.today(),
        datetime_field=datetime.datetime.now(datetime.UTC),
        uuid_field=uuid.uuid4(),
        bool_field=True,
        float_field=12.5,
        enum_field=EnumType.B,
    )
    dumped = mr.dump(filled_data)
    loaded = mr.load(TypeWithMissing, dumped)
    assert loaded == filled_data


def test_optional_simple_types() -> None:
    class EnumType(str, enum.Enum):
        A = "A"
        B = "B"

        def __str__(self) -> str:
            return self.value

    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    @mr.options(none_value_handling=mr.NoneValueHandling.INCLUDE)
    class TypeWithMissing:
        str_field: str | None = mr.MISSING
        int_field: int | None = mr.MISSING
        decimal_field: decimal.Decimal | None = mr.MISSING
        date_field: datetime.date | None = mr.MISSING
        datetime_field: datetime.datetime | None = mr.MISSING
        uuid_field: uuid.UUID | None = mr.MISSING
        bool_field: bool | None = mr.MISSING
        float_field: float | None = mr.MISSING
        enum_field: EnumType | None = mr.MISSING

    dumped = mr.dump(TypeWithMissing())
    assert dumped == {}
    loaded = mr.load(TypeWithMissing, dumped)
    assert loaded == TypeWithMissing()

    filled_data = TypeWithMissing(
        str_field="str_field",
        int_field=10,
        decimal_field=decimal.Decimal("1.12"),
        date_field=datetime.date.today(),
        datetime_field=datetime.datetime.now(datetime.UTC),
        uuid_field=uuid.uuid4(),
        bool_field=True,
        float_field=12.5,
        enum_field=EnumType.B,
    )
    dumped = mr.dump(filled_data)
    loaded = mr.load(TypeWithMissing, dumped)
    assert loaded == filled_data

    filled_data = TypeWithMissing(
        str_field=None,
        int_field=None,
        decimal_field=None,
        date_field=None,
        datetime_field=None,
        uuid_field=None,
        bool_field=None,
        float_field=None,
        enum_field=None,
    )
    dumped = mr.dump(filled_data)
    assert len(dumped) == 9
    loaded = mr.load(TypeWithMissing, dumped)
    assert loaded == filled_data


def test_list() -> None:
    class EnumType(str, enum.Enum):
        A = "A"
        B = "B"

        def __str__(self) -> str:
            return self.value

    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class TypeWithMissing:
        str_field: list[str] = mr.MISSING
        int_field: list[int] = mr.MISSING
        decimal_field: list[decimal.Decimal] = mr.MISSING
        date_field: list[datetime.date] = mr.MISSING
        datetime_field: list[datetime.datetime] = mr.MISSING
        uuid_field: list[uuid.UUID] = mr.MISSING
        bool_field: list[bool] = mr.MISSING
        float_field: list[float] = mr.MISSING
        enum_field: list[EnumType] = mr.MISSING

    dumped = mr.dump(TypeWithMissing())
    assert dumped == {}
    loaded = mr.load(TypeWithMissing, dumped)
    assert loaded == TypeWithMissing()

    filled_data = TypeWithMissing(
        str_field=["str_field"],
        int_field=[10],
        decimal_field=[decimal.Decimal("1.12")],
        date_field=[datetime.date.today()],
        datetime_field=[datetime.datetime.now(datetime.UTC)],
        uuid_field=[uuid.uuid4()],
        bool_field=[True],
        float_field=[12.5],
        enum_field=[EnumType.B],
    )
    dumped = mr.dump(filled_data)
    loaded = mr.load(TypeWithMissing, dumped)
    assert loaded == filled_data


def test_optional_list() -> None:
    class EnumType(str, enum.Enum):
        A = "A"
        B = "B"

        def __str__(self) -> str:
            return self.value

    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    @mr.options(none_value_handling=mr.NoneValueHandling.INCLUDE)
    class TypeWithMissing:
        str_field: list[str] | None = mr.MISSING
        int_field: list[int] | None = mr.MISSING
        decimal_field: list[decimal.Decimal] | None = mr.MISSING
        date_field: list[datetime.date] | None = mr.MISSING
        datetime_field: list[datetime.datetime] | None = mr.MISSING
        uuid_field: list[uuid.UUID] | None = mr.MISSING
        bool_field: list[bool] | None = mr.MISSING
        float_field: list[float] | None = mr.MISSING
        enum_field: list[EnumType] | None = mr.MISSING

    dumped = mr.dump(TypeWithMissing())
    assert dumped == {}
    loaded = mr.load(TypeWithMissing, dumped)
    assert loaded == TypeWithMissing()

    filled_data = TypeWithMissing(
        str_field=["str_field"],
        int_field=[10],
        decimal_field=[decimal.Decimal("1.12")],
        date_field=[datetime.date.today()],
        datetime_field=[datetime.datetime.now(datetime.UTC)],
        uuid_field=[uuid.uuid4()],
        bool_field=[True],
        float_field=[12.5],
        enum_field=[EnumType.B],
    )
    dumped = mr.dump(filled_data)
    loaded = mr.load(TypeWithMissing, dumped)
    assert loaded == filled_data

    filled_data = TypeWithMissing(
        str_field=None,
        int_field=None,
        decimal_field=None,
        date_field=None,
        datetime_field=None,
        uuid_field=None,
        bool_field=None,
        float_field=None,
        enum_field=None,
    )
    dumped = mr.dump(filled_data)
    assert len(dumped) == 9
    loaded = mr.load(TypeWithMissing, dumped)
    assert loaded == filled_data


def test_nested() -> None:
    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class Nested:
        str_field: str

    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class TypeWithMissing:
        nested_field: Nested = mr.MISSING

    dumped = mr.dump(TypeWithMissing())
    assert dumped == {}
    loaded = mr.load(TypeWithMissing, dumped)
    assert loaded == TypeWithMissing()

    filled_data = TypeWithMissing(nested_field=Nested(str_field="str"))
    dumped = mr.dump(filled_data)
    loaded = mr.load(TypeWithMissing, dumped)
    assert loaded == filled_data


def test_optional_nested() -> None:
    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class Nested:
        str_field: str

    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    @mr.options(none_value_handling=mr.NoneValueHandling.INCLUDE)
    class TypeWithMissing:
        nested_field: Nested | None = mr.MISSING

    dumped = mr.dump(TypeWithMissing())
    assert dumped == {}
    loaded = mr.load(TypeWithMissing, dumped)
    assert loaded == TypeWithMissing()

    filled_data = TypeWithMissing(nested_field=Nested(str_field="str"))
    dumped = mr.dump(filled_data)
    loaded = mr.load(TypeWithMissing, dumped)
    assert loaded == filled_data

    filled_data = TypeWithMissing(nested_field=None)
    dumped = mr.dump(filled_data)
    assert len(dumped) == 1
    loaded = mr.load(TypeWithMissing, dumped)
    assert loaded == filled_data


def test_nested_list() -> None:
    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class Nested:
        str_field: str

    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class TypeWithMissing:
        nested_field: list[Nested] = mr.MISSING

    dumped = mr.dump(TypeWithMissing())
    assert dumped == {}
    loaded = mr.load(TypeWithMissing, dumped)
    assert loaded == TypeWithMissing()

    filled_data = TypeWithMissing(nested_field=[Nested(str_field="str")])
    dumped = mr.dump(filled_data)
    loaded = mr.load(TypeWithMissing, dumped)
    assert loaded == filled_data


def test_optional_nested_list() -> None:
    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class Nested:
        str_field: str

    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    @mr.options(none_value_handling=mr.NoneValueHandling.INCLUDE)
    class TypeWithMissing:
        nested_field: list[Nested] | None = mr.MISSING

    dumped = mr.dump(TypeWithMissing())
    assert dumped == {}
    loaded = mr.load(TypeWithMissing, dumped)
    assert loaded == TypeWithMissing()

    filled_data = TypeWithMissing(nested_field=[Nested(str_field="str")])
    dumped = mr.dump(filled_data)
    loaded = mr.load(TypeWithMissing, dumped)
    assert loaded == filled_data

    filled_data = TypeWithMissing(nested_field=None)
    dumped = mr.dump(filled_data)
    assert len(dumped) == 1
    loaded = mr.load(TypeWithMissing, dumped)
    assert loaded == filled_data


def test_nested_with_missing() -> None:
    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class NestedWithMissing:
        str_field: str = mr.MISSING

    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class TypeWithNested:
        nested_field: NestedWithMissing | None = None

    dumped = mr.dump(TypeWithNested())
    assert dumped == {}
    loaded = mr.load(TypeWithNested, dumped)
    assert loaded == TypeWithNested()

    dumped = mr.dump(TypeWithNested(nested_field=NestedWithMissing()))
    assert dumped == {"nested_field": {}}
    loaded = mr.load(TypeWithNested, dumped)
    assert loaded == TypeWithNested(nested_field=NestedWithMissing())

    filled_data = TypeWithNested(nested_field=NestedWithMissing(str_field="str"))
    dumped = mr.dump(filled_data)
    loaded = mr.load(TypeWithNested, dumped)
    assert loaded == filled_data


def test_meaningful_default() -> None:
    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class WithDefault:
        field_str: str
        field_bool: bool
        field_int: int
        field_str_default: str = "default"
        field_bool_default: bool = False
        field_int_default: int = 1

    loaded = mr.load(WithDefault, {"field_str": "str", "field_bool": True, "field_int": 0})
    assert loaded == WithDefault(field_str="str", field_bool=True, field_int=0)
    assert loaded.field_int_default == 1
    assert loaded.field_bool_default is False
    assert loaded.field_str_default == "default"
