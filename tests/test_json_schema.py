from __future__ import annotations

import dataclasses
import datetime
import decimal
import enum
import uuid
from typing import Annotated, Generic, Literal, TypeVar

import pytest

import marshmallow_recipe as mr

T = TypeVar("T")
TData = TypeVar("TData")
K = TypeVar("K")
V = TypeVar("V")


def test_simple_types() -> None:
    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class SimpleTypes:
        str_field: str
        int_field: int
        float_field: float
        bool_field: bool

    schema = mr.json_schema(SimpleTypes)

    assert schema == {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "title": "SimpleTypes",
        "properties": {
            "str_field": {"type": "string"},
            "int_field": {"type": "integer"},
            "float_field": {"type": "number"},
            "bool_field": {"type": "boolean"},
        },
        "required": ["str_field", "int_field", "float_field", "bool_field"],
    }


def test_optional_fields() -> None:
    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class OptionalFields:
        required_str: str
        optional_str: str | None
        optional_int: int | None

    schema = mr.json_schema(OptionalFields)

    assert schema == {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "title": "OptionalFields",
        "properties": {
            "required_str": {"type": "string"},
            "optional_str": {"type": "string"},
            "optional_int": {"type": "integer"},
        },
        "required": ["required_str"],
    }


def test_fields_with_defaults() -> None:
    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class WithDefaults:
        str_with_default: str = "hello"
        int_with_default: int = 42
        bool_with_default: bool = True

    schema = mr.json_schema(WithDefaults)

    assert schema == {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "title": "WithDefaults",
        "properties": {
            "str_with_default": {"type": "string", "default": "hello"},
            "int_with_default": {"type": "integer", "default": 42},
            "bool_with_default": {"type": "boolean", "default": True},
        },
        "required": [],
    }


def test_default_factory() -> None:
    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class WithFactories:
        id: uuid.UUID = dataclasses.field(default_factory=uuid.uuid4)
        tags: list[str] = dataclasses.field(default_factory=list)
        name: str = "default_name"

    schema = mr.json_schema(WithFactories)

    assert schema == {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "title": "WithFactories",
        "properties": {
            "id": {"type": "string", "format": "uuid"},
            "tags": {"type": "array", "items": {"type": "string"}},
            "name": {"type": "string", "default": "default_name"},
        },
        "required": [],
    }


def test_description_metadata() -> None:
    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class WithDescriptions:
        name: Annotated[str, mr.meta(description="User's full name")]
        age: Annotated[int, mr.meta(description="Age in years")]
        email: str  # No description

    schema = mr.json_schema(WithDescriptions)

    assert schema == {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "title": "WithDescriptions",
        "properties": {
            "name": {"type": "string", "description": "User's full name"},
            "age": {"type": "integer", "description": "Age in years"},
            "email": {"type": "string"},
        },
        "required": ["name", "age", "email"],
    }


def test_datetime_types() -> None:
    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class DateTimeTypes:
        dt: datetime.datetime
        d: datetime.date
        t: datetime.time
        uid: uuid.UUID

    schema = mr.json_schema(DateTimeTypes)

    assert schema == {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "title": "DateTimeTypes",
        "properties": {
            "dt": {"type": "string", "format": "date-time"},
            "d": {"type": "string", "format": "date"},
            "t": {"type": "string", "format": "time"},
            "uid": {"type": "string", "format": "uuid"},
        },
        "required": ["dt", "d", "t", "uid"],
    }


def test_union_types() -> None:
    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class UnionTypes:
        str_or_int: str | int
        str_or_int_or_bool: str | int | bool

    schema = mr.json_schema(UnionTypes)

    assert schema == {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "title": "UnionTypes",
        "properties": {
            "str_or_int": {"anyOf": [{"type": "string"}, {"type": "integer"}]},
            "str_or_int_or_bool": {"anyOf": [{"type": "string"}, {"type": "integer"}, {"type": "boolean"}]},
        },
        "required": ["str_or_int", "str_or_int_or_bool"],
    }


def test_naming_case() -> None:
    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class NamingCase:
        user_name: str
        user_age: int

    schema = mr.json_schema(NamingCase, naming_case=mr.CAMEL_CASE)

    assert schema == {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "title": "NamingCase",
        "properties": {"userName": {"type": "string"}, "userAge": {"type": "integer"}},
        "required": ["userName", "userAge"],
    }


def test_schema_description_in_options() -> None:
    @mr.options(description="A user in the system")
    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class UserWithDescription:
        name: str
        age: int

    schema = mr.json_schema(UserWithDescription)

    assert schema == {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "title": "UserWithDescription",
        "description": "A user in the system",
        "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
        "required": ["name", "age"],
    }


def test_schema_title_in_options() -> None:
    @mr.options(title="User Profile", description="A user in the system")
    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class UserWithTitle:
        name: str
        age: int

    schema = mr.json_schema(UserWithTitle)

    assert schema == {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "title": "User Profile",
        "description": "A user in the system",
        "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
        "required": ["name", "age"],
    }

    schema_override = mr.json_schema(UserWithTitle, title="Overridden Title")
    assert schema_override == {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "title": "Overridden Title",
        "description": "A user in the system",
        "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
        "required": ["name", "age"],
    }

    schema_empty = mr.json_schema(UserWithTitle, title="")
    assert schema_empty == {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "title": "",
        "description": "A user in the system",
        "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
        "required": ["name", "age"],
    }


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class _Address:
    street: Annotated[str, mr.meta(description="Street name")]
    city: str


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class _Person:
    name: Annotated[str, mr.meta(description="Person's name")]
    address: Annotated[_Address, mr.meta(description="Person's address")]


def test_nested_dataclass() -> None:
    schema = mr.json_schema(_Person)

    assert schema == {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "title": "_Person",
        "properties": {
            "name": {"type": "string", "description": "Person's name"},
            "address": {"$ref": "#/$defs/_Address", "description": "Person's address"},
        },
        "required": ["name", "address"],
        "$defs": {
            "_Address": {
                "type": "object",
                "title": "_Address",
                "properties": {"street": {"type": "string", "description": "Street name"}, "city": {"type": "string"}},
                "required": ["street", "city"],
            }
        },
    }


@mr.options(description="A contact address")
@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class _Contact:
    email: str
    phone: str


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class _User:
    name: str
    contacts: Annotated[list[_Contact], mr.meta(description="List of user contacts")]


def test_list_of_dataclasses() -> None:
    schema = mr.json_schema(_User)

    assert schema == {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "title": "_User",
        "properties": {
            "name": {"type": "string"},
            "contacts": {
                "type": "array",
                "items": {"$ref": "#/$defs/_Contact"},
                "description": "List of user contacts",
            },
        },
        "required": ["name", "contacts"],
        "$defs": {
            "_Contact": {
                "type": "object",
                "title": "_Contact",
                "description": "A contact address",
                "properties": {"email": {"type": "string"}, "phone": {"type": "string"}},
                "required": ["email", "phone"],
            }
        },
    }


def test_list_of_strings() -> None:
    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class TaggedItem:
        name: str
        tags: Annotated[list[str], mr.meta(description="Item tags for categorization")]

    schema = mr.json_schema(TaggedItem)

    assert schema == {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "title": "TaggedItem",
        "properties": {
            "name": {"type": "string"},
            "tags": {"type": "array", "items": {"type": "string"}, "description": "Item tags for categorization"},
        },
        "required": ["name", "tags"],
    }


def test_list_item_description() -> None:
    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class TaggedItem:
        tags: Annotated[list[str], mr.list_meta(description="Item tags", item_description="A tag value")]

    schema = mr.json_schema(TaggedItem)

    assert schema == {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "title": "TaggedItem",
        "properties": {
            "tags": {
                "type": "array",
                "items": {"type": "string", "description": "A tag value"},
                "description": "Item tags",
            }
        },
        "required": ["tags"],
    }


def test_list_min_max_length() -> None:
    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class BoundedList:
        items: Annotated[list[int], mr.list_meta(min_length=1, max_length=10)]

    schema = mr.json_schema(BoundedList)

    assert schema == {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "title": "BoundedList",
        "properties": {"items": {"type": "array", "items": {"type": "integer"}, "minItems": 1, "maxItems": 10}},
        "required": ["items"],
    }


def test_list_min_length_only() -> None:
    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class MinLengthList:
        items: Annotated[list[str], mr.list_meta(min_length=2)]

    schema = mr.json_schema(MinLengthList)

    assert schema == {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "title": "MinLengthList",
        "properties": {"items": {"type": "array", "items": {"type": "string"}, "minItems": 2}},
        "required": ["items"],
    }


def test_list_max_length_only() -> None:
    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class MaxLengthList:
        items: Annotated[list[str], mr.list_meta(max_length=5)]

    schema = mr.json_schema(MaxLengthList)

    assert schema == {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "title": "MaxLengthList",
        "properties": {"items": {"type": "array", "items": {"type": "string"}, "maxItems": 5}},
        "required": ["items"],
    }


def test_str_min_max_length() -> None:
    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class BoundedStr:
        value: Annotated[str, mr.str_meta(min_length=1, max_length=100)]

    schema = mr.json_schema(BoundedStr)

    assert schema == {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "title": "BoundedStr",
        "properties": {"value": {"type": "string", "minLength": 1, "maxLength": 100}},
        "required": ["value"],
    }


def test_str_min_length_only() -> None:
    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class MinLengthStr:
        value: Annotated[str, mr.str_meta(min_length=3)]

    schema = mr.json_schema(MinLengthStr)

    assert schema == {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "title": "MinLengthStr",
        "properties": {"value": {"type": "string", "minLength": 3}},
        "required": ["value"],
    }


def test_str_max_length_only() -> None:
    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class MaxLengthStr:
        value: Annotated[str, mr.str_meta(max_length=50)]

    schema = mr.json_schema(MaxLengthStr)

    assert schema == {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "title": "MaxLengthStr",
        "properties": {"value": {"type": "string", "maxLength": 50}},
        "required": ["value"],
    }


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class _CyclicNode:
    value: int
    next_node: _CyclicNode | None = None


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class _RecursivePerson:
    name: str
    spouse: _RecursivePerson | None = None
    friends: list[_RecursivePerson] = dataclasses.field(default_factory=list)


def test_cyclic_references() -> None:
    schema = mr.json_schema(_CyclicNode)

    assert schema == {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "title": "_CyclicNode",
        "properties": {"value": {"type": "integer"}, "next_node": {"$ref": "#/$defs/_CyclicNode", "default": None}},
        "required": ["value"],
        "$defs": {
            "_CyclicNode": {
                "type": "object",
                "title": "_CyclicNode",
                "properties": {
                    "value": {"type": "integer"},
                    "next_node": {"$ref": "#/$defs/_CyclicNode", "default": None},
                },
                "required": ["value"],
            }
        },
    }


def test_mutually_recursive_types() -> None:
    schema = mr.json_schema(_RecursivePerson)

    assert schema == {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "title": "_RecursivePerson",
        "properties": {
            "name": {"type": "string"},
            "spouse": {"$ref": "#/$defs/_RecursivePerson", "default": None},
            "friends": {"type": "array", "items": {"$ref": "#/$defs/_RecursivePerson"}},
        },
        "required": ["name"],
        "$defs": {
            "_RecursivePerson": {
                "type": "object",
                "title": "_RecursivePerson",
                "properties": {
                    "name": {"type": "string"},
                    "spouse": {"$ref": "#/$defs/_RecursivePerson", "default": None},
                    "friends": {"type": "array", "items": {"$ref": "#/$defs/_RecursivePerson"}},
                },
                "required": ["name"],
            }
        },
    }


class _Status(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"


class _Priority(int, enum.Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class _Task:
    title: str
    status: _Status
    priority: _Priority
    optional_status: _Status | None = None


def test_enum_types() -> None:
    schema = mr.json_schema(_Task)

    assert schema == {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "title": "_Task",
        "properties": {
            "title": {"type": "string"},
            "status": {"type": "string", "enum": ["active", "inactive", "pending"]},
            "priority": {"type": "integer", "enum": [1, 2, 3]},
            "optional_status": {"type": "string", "enum": ["active", "inactive", "pending"], "default": None},
        },
        "required": ["title", "status", "priority"],
    }


def test_decimal_types() -> None:
    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class Product:
        name: str
        price: decimal.Decimal
        price_with_places: Annotated[decimal.Decimal, mr.decimal_meta(places=2)]
        price_gt: Annotated[decimal.Decimal, mr.decimal_meta(gt=0)]
        price_gte: Annotated[decimal.Decimal, mr.decimal_meta(gte=0)]
        price_lt: Annotated[decimal.Decimal, mr.decimal_meta(lt=1000)]
        price_lte: Annotated[decimal.Decimal, mr.decimal_meta(lte=1000)]
        price_range: Annotated[
            decimal.Decimal, mr.decimal_meta(gte=decimal.Decimal("0.01"), lte=decimal.Decimal("999.99"))
        ]

    schema = mr.json_schema(Product)

    assert schema == {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "title": "Product",
        "properties": {
            "name": {"type": "string"},
            "price": {"type": "string"},
            "price_with_places": {"type": "string"},
            "price_gt": {"type": "string", "exclusiveMinimum": "0"},
            "price_gte": {"type": "string", "minimum": "0"},
            "price_lt": {"type": "string", "exclusiveMaximum": "1000"},
            "price_lte": {"type": "string", "maximum": "1000"},
            "price_range": {"type": "string", "minimum": "0.01", "maximum": "999.99"},
        },
        "required": [
            "name",
            "price",
            "price_with_places",
            "price_gt",
            "price_gte",
            "price_lt",
            "price_lte",
            "price_range",
        ],
    }


def test_int_range_types() -> None:
    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class Limits:
        plain: int
        val_gt: Annotated[int, mr.int_meta(gt=0)]
        val_gte: Annotated[int, mr.int_meta(gte=0)]
        val_lt: Annotated[int, mr.int_meta(lt=100)]
        val_lte: Annotated[int, mr.int_meta(lte=100)]
        val_range: Annotated[int, mr.int_meta(gte=1, lte=99)]

    schema = mr.json_schema(Limits)

    assert schema == {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "title": "Limits",
        "properties": {
            "plain": {"type": "integer"},
            "val_gt": {"type": "integer", "exclusiveMinimum": 0},
            "val_gte": {"type": "integer", "minimum": 0},
            "val_lt": {"type": "integer", "exclusiveMaximum": 100},
            "val_lte": {"type": "integer", "maximum": 100},
            "val_range": {"type": "integer", "minimum": 1, "maximum": 99},
        },
        "required": ["plain", "val_gt", "val_gte", "val_lt", "val_lte", "val_range"],
    }


def test_float_range_types() -> None:
    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class Measurements:
        plain: float
        val_gt: Annotated[float, mr.float_meta(gt=0.0)]
        val_gte: Annotated[float, mr.float_meta(gte=0)]
        val_lt: Annotated[float, mr.float_meta(lt=100.5)]
        val_lte: Annotated[float, mr.float_meta(lte=100)]
        val_range: Annotated[float, mr.float_meta(gte=0.01, lte=99.99)]

    schema = mr.json_schema(Measurements)

    assert schema == {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "title": "Measurements",
        "properties": {
            "plain": {"type": "number"},
            "val_gt": {"type": "number", "exclusiveMinimum": 0.0},
            "val_gte": {"type": "number", "minimum": 0},
            "val_lt": {"type": "number", "exclusiveMaximum": 100.5},
            "val_lte": {"type": "number", "maximum": 100},
            "val_range": {"type": "number", "minimum": 0.01, "maximum": 99.99},
        },
        "required": ["plain", "val_gt", "val_gte", "val_lt", "val_lte", "val_range"],
    }


def test_set_and_frozenset_types() -> None:
    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class UniqueItems:
        tags_set: set[str]
        ids_frozenset: frozenset[int]
        optional_set: set[str] | None = None

    schema = mr.json_schema(UniqueItems)

    assert schema == {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "title": "UniqueItems",
        "properties": {
            "tags_set": {"type": "array", "uniqueItems": True, "items": {"type": "string"}},
            "ids_frozenset": {"type": "array", "uniqueItems": True, "items": {"type": "integer"}},
            "optional_set": {"type": "array", "uniqueItems": True, "items": {"type": "string"}, "default": None},
        },
        "required": ["tags_set", "ids_frozenset"],
    }


def test_dict_types() -> None:
    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class Config:
        simple_dict: dict[str, int]
        any_dict: dict[str, object]
        optional_dict: dict[str, str] | None = None

    schema = mr.json_schema(Config)

    assert schema == {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "title": "Config",
        "properties": {
            "simple_dict": {"type": "object", "additionalProperties": {"type": "integer"}},
            "any_dict": {"type": "object", "additionalProperties": {"type": "object"}},
            "optional_dict": {"type": "object", "additionalProperties": {"type": "string"}, "default": None},
        },
        "required": ["simple_dict", "any_dict"],
    }


def test_non_dataclass_error() -> None:
    class NotADataclass:
        name: str

    with pytest.raises(ValueError, match="is not a dataclass"):
        mr.json_schema(NotADataclass)  # type: ignore


def test_generic_simple() -> None:
    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class Container(Generic[T]):
        value: T

    schema = mr.json_schema(Container[int])

    assert schema == {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "title": "Container[int]",
        "properties": {"value": {"type": "integer"}},
        "required": ["value"],
    }

    schema_str = mr.json_schema(Container[str])

    assert schema_str == {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "title": "Container[str]",
        "properties": {"value": {"type": "string"}},
        "required": ["value"],
    }


def test_generic_with_options() -> None:
    @mr.options(naming_case=mr.CAMEL_CASE, description="A generic container")
    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class Container(Generic[T]):
        item_value: T

    schema = mr.json_schema(Container[int])

    assert schema == {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "title": "Container[int]",
        "description": "A generic container",
        "properties": {"itemValue": {"type": "integer"}},
        "required": ["itemValue"],
    }


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class _GenericInner(Generic[T]):
    value: T


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class _GenericOuter(Generic[T]):
    inner: _GenericInner[T]


def test_generic_nested() -> None:
    schema = mr.json_schema(_GenericOuter[str])

    assert schema == {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "title": "_GenericOuter[str]",
        "properties": {"inner": {"$ref": "#/$defs/_GenericInner[str]"}},
        "required": ["inner"],
        "$defs": {
            "_GenericInner[str]": {
                "type": "object",
                "title": "_GenericInner[str]",
                "properties": {"value": {"type": "string"}},
                "required": ["value"],
            }
        },
    }


def test_generic_in_parents() -> None:
    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class Data(Generic[T]):
        data: T

    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class Parent(Generic[TData]):
        name: str
        content: TData

    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class Child(Parent[Data[int]]):
        pass

    schema = mr.json_schema(Child)

    assert schema == {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "title": "Child",
        "properties": {"name": {"type": "string"}, "content": {"$ref": "#/$defs/Data[int]"}},
        "required": ["name", "content"],
        "$defs": {
            "Data[int]": {
                "type": "object",
                "title": "Data[int]",
                "properties": {"data": {"type": "integer"}},
                "required": ["data"],
            }
        },
    }


def test_generic_with_multiple_type_vars() -> None:
    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class Pair(Generic[K, V]):
        key: K
        value: V

    schema = mr.json_schema(Pair[str, int])

    assert schema == {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "title": "Pair[str, int]",
        "properties": {"key": {"type": "string"}, "value": {"type": "integer"}},
        "required": ["key", "value"],
    }


def test_literal_types() -> None:
    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class WithLiterals:
        str_literal: Literal["a", "b", "c"]
        int_literal: Literal[1, 2, 3]
        bool_literal: Literal[True, False]
        optional_str_literal: Literal["x", "y"] | None = None
        optional_int_literal: Literal[1, 2] | None = None
        optional_bool_literal: Literal[True] | None = None

    schema = mr.json_schema(WithLiterals)

    assert schema == {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "title": "WithLiterals",
        "properties": {
            "str_literal": {"type": "string", "enum": ["a", "b", "c"]},
            "int_literal": {"type": "integer", "enum": [1, 2, 3]},
            "bool_literal": {"type": "boolean", "enum": [True, False]},
            "optional_str_literal": {"type": "string", "enum": ["x", "y"], "default": None},
            "optional_int_literal": {"type": "integer", "enum": [1, 2], "default": None},
            "optional_bool_literal": {"type": "boolean", "enum": [True], "default": None},
        },
        "required": ["str_literal", "int_literal", "bool_literal"],
    }


def test_bytes_field() -> None:
    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class WithBytes:
        data: bytes
        optional_data: bytes | None = None

    schema = mr.json_schema(WithBytes)

    assert schema == {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "title": "WithBytes",
        "properties": {
            "data": {"type": "string", "format": "byte"},
            "optional_data": {"type": "string", "format": "byte", "default": None},
        },
        "required": ["data"],
    }


type StrAlias = str
type OptionalIntAlias = int | None
type UnionAlias = str | int
type ChainedStrAlias = StrAlias
type UnionOfAliases = StrAlias | OptionalIntAlias


def test_type_alias() -> None:
    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class WithTypeAliases:
        name: StrAlias
        count: OptionalIntAlias = None
        value: UnionAlias = "default"

    schema = mr.json_schema(WithTypeAliases)

    assert schema == {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "title": "WithTypeAliases",
        "properties": {
            "name": {"type": "string"},
            "count": {"type": "integer", "default": None},
            "value": {"anyOf": [{"type": "string"}, {"type": "integer"}], "default": "default"},
        },
        "required": ["name"],
    }


def test_type_alias_chained() -> None:
    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class WithChainedAlias:
        name: ChainedStrAlias

    schema = mr.json_schema(WithChainedAlias)
    assert schema == {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "title": "WithChainedAlias",
        "properties": {"name": {"type": "string"}},
        "required": ["name"],
    }


def test_type_alias_union_of_aliases() -> None:
    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class WithUnionOfAliases:
        value: UnionOfAliases

    schema = mr.json_schema(WithUnionOfAliases)
    assert schema == {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "title": "WithUnionOfAliases",
        "properties": {"value": {"anyOf": [{"type": "string"}, {"type": "integer"}]}},
        "required": ["value"],
    }


def test_str_regexp_schema() -> None:
    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class WithRegexp:
        value: str = dataclasses.field(metadata=mr.str_meta(regexp=r"^\d+$"))

    schema = mr.json_schema(WithRegexp)

    assert schema == {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "title": "WithRegexp",
        "properties": {"value": {"type": "string", "pattern": r"^\d+$"}},
        "required": ["value"],
    }


def test_str_all_validators_schema() -> None:
    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class WithAllStr:
        value: str = dataclasses.field(metadata=mr.str_meta(min_length=2, max_length=10, regexp=r"^[a-z]+$"))

    schema = mr.json_schema(WithAllStr)

    assert schema == {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "title": "WithAllStr",
        "properties": {"value": {"type": "string", "minLength": 2, "maxLength": 10, "pattern": r"^[a-z]+$"}},
        "required": ["value"],
    }
