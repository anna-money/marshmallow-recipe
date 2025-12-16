from __future__ import annotations

import dataclasses
import datetime
import decimal
import enum
import uuid
from typing import Annotated

import pytest

import marshmallow_recipe as mr


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

    # Optional fields have simple type, NOT anyOf with null
    # They are just omitted from required array
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

    # Fields with defaults are not required and include default value
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

    # Fields with default_factory should NOT include a "default" key in JSON Schema
    # because factories are dynamic and can't be represented as static JSON values
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

    # Test that title parameter overrides @options title
    schema_override = mr.json_schema(UserWithTitle, title="Overridden Title")
    assert schema_override["title"] == "Overridden Title"
    assert schema_override["description"] == "A user in the system"

    # Test that empty string title overrides @options title (not treated as falsy)
    schema_empty = mr.json_schema(UserWithTitle, title="")
    assert schema_empty["title"] == ""
    assert schema_empty["description"] == "A user in the system"


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


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class _CyclicNode:
    """Test class for cyclic references - defined at module level to avoid forward ref issues"""

    value: int
    next_node: _CyclicNode | None = None


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class _RecursivePerson:
    """Test class for recursive references - defined at module level to avoid forward ref issues"""

    name: str
    spouse: _RecursivePerson | None = None
    friends: list[_RecursivePerson] = dataclasses.field(default_factory=list)


def test_cyclic_references() -> None:
    """Test that cyclic/self-referential dataclasses work correctly"""

    schema = mr.json_schema(_CyclicNode)

    # Should have $defs with Node definition
    assert "$defs" in schema
    assert "_CyclicNode" in schema["$defs"]

    # Top-level schema
    assert schema["type"] == "object"
    assert schema["title"] == "_CyclicNode"
    assert set(schema["properties"].keys()) == {"value", "next_node"}
    assert schema["properties"]["value"] == {"type": "integer"}
    assert schema["properties"]["next_node"] == {"$ref": "#/$defs/_CyclicNode", "default": None}
    assert schema["required"] == ["value"]

    # $defs/_CyclicNode should match the structure
    node_def = schema["$defs"]["_CyclicNode"]
    assert node_def["type"] == "object"
    assert node_def["title"] == "_CyclicNode"
    assert node_def["properties"]["value"] == {"type": "integer"}
    assert node_def["properties"]["next_node"] == {"$ref": "#/$defs/_CyclicNode", "default": None}
    assert node_def["required"] == ["value"]


def test_mutually_recursive_types() -> None:
    """Test mutually recursive dataclasses"""

    schema = mr.json_schema(_RecursivePerson)

    assert "$defs" in schema
    assert "_RecursivePerson" in schema["$defs"]

    # Check self-references work
    assert schema["properties"]["spouse"] == {"$ref": "#/$defs/_RecursivePerson", "default": None}
    # friends has default_factory=list, so no "default" key in schema (it's dynamic)
    assert schema["properties"]["friends"] == {"type": "array", "items": {"$ref": "#/$defs/_RecursivePerson"}}

    # Verify $defs has the same structure
    person_def = schema["$defs"]["_RecursivePerson"]
    assert person_def["properties"]["spouse"] == {"$ref": "#/$defs/_RecursivePerson", "default": None}
    # friends has default_factory=list, so no "default" key in schema (it's dynamic)
    assert person_def["properties"]["friends"] == {"type": "array", "items": {"$ref": "#/$defs/_RecursivePerson"}}


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
    """Test that enum types work correctly"""

    schema = mr.json_schema(_Task)

    assert schema["properties"]["status"] == {"type": "string", "enum": ["active", "inactive", "pending"]}
    assert schema["properties"]["priority"] == {"type": "integer", "enum": [1, 2, 3]}
    assert schema["properties"]["optional_status"] == {
        "type": "string",
        "enum": ["active", "inactive", "pending"],
        "default": None,
    }
    assert schema["required"] == ["title", "status", "priority"]


def test_decimal_types() -> None:
    """Test decimal types with as_string and as_number representations"""

    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class Product:
        name: str
        price_str: Annotated[decimal.Decimal, mr.decimal_meta(as_string=True)]
        price_num: Annotated[decimal.Decimal, mr.decimal_meta(as_string=False)]
        price_default: decimal.Decimal

    schema = mr.json_schema(Product)

    assert schema["properties"]["price_str"] == {"type": "string"}
    assert schema["properties"]["price_num"] == {"type": "number"}
    # Default should be string (as_string=True by default)
    assert schema["properties"]["price_default"] == {"type": "string"}


def test_set_and_frozenset_types() -> None:
    """Test set and frozenset types have uniqueItems"""

    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class UniqueItems:
        tags_set: set[str]
        ids_frozenset: frozenset[int]
        optional_set: set[str] | None = None

    schema = mr.json_schema(UniqueItems)

    assert schema["properties"]["tags_set"] == {"type": "array", "uniqueItems": True, "items": {"type": "string"}}
    assert schema["properties"]["ids_frozenset"] == {"type": "array", "uniqueItems": True, "items": {"type": "integer"}}
    assert schema["properties"]["optional_set"] == {
        "type": "array",
        "uniqueItems": True,
        "items": {"type": "string"},
        "default": None,
    }
    assert schema["required"] == ["tags_set", "ids_frozenset"]


def test_dict_types() -> None:
    """Test dict/mapping types"""

    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class Config:
        simple_dict: dict[str, int]
        any_dict: dict[str, object]
        optional_dict: dict[str, str] | None = None

    schema = mr.json_schema(Config)

    assert schema["properties"]["simple_dict"] == {"type": "object", "additionalProperties": {"type": "integer"}}
    assert schema["properties"]["any_dict"] == {"type": "object", "additionalProperties": {"type": "object"}}
    assert schema["properties"]["optional_dict"] == {
        "type": "object",
        "additionalProperties": {"type": "string"},
        "default": None,
    }
    assert schema["required"] == ["simple_dict", "any_dict"]


def test_non_dataclass_error() -> None:
    """Test that non-dataclass input raises ValueError"""

    class NotADataclass:
        name: str

    with pytest.raises(ValueError, match="is not a dataclass"):
        mr.json_schema(NotADataclass)  # type: ignore


def test_generic_simple() -> None:
    """Test simple generic dataclass with type parameter"""

    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class Container[T]:
        value: T

    # Test with int type parameter
    schema = mr.json_schema(Container[int])

    assert schema == {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "title": "Container[int]",
        "properties": {"value": {"type": "integer"}},
        "required": ["value"],
    }

    # Test with str type parameter
    schema_str = mr.json_schema(Container[str])
    assert schema_str["title"] == "Container[str]"
    assert schema_str["properties"]["value"] == {"type": "string"}


def test_generic_with_options() -> None:
    """Test that @options works correctly with generic types"""

    @mr.options(naming_case=mr.CAMEL_CASE, description="A generic container")
    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class Container[T]:
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
class _GenericInner[T]:
    value: T


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class _GenericOuter[T]:
    inner: _GenericInner[T]


def test_generic_nested() -> None:
    """Test nested generic dataclasses"""

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
    """Test generic type parameters in parent classes"""

    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class Data[T]:
        data: T

    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class Parent[TData]:
        name: str
        content: TData

    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class Child(Parent[Data[int]]):
        pass

    schema = mr.json_schema(Child)

    assert schema["title"] == "Child"
    assert schema["properties"]["name"] == {"type": "string"}
    assert schema["properties"]["content"] == {"$ref": "#/$defs/Data[int]"}
    assert "$defs" in schema
    assert "Data[int]" in schema["$defs"]
    assert schema["$defs"]["Data[int]"]["properties"]["data"] == {"type": "integer"}


def test_generic_with_multiple_type_vars() -> None:
    """Test generic with multiple type parameters"""

    @dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
    class Pair[K, V]:
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
