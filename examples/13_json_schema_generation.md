# JSON Schema Generation

Generate JSON Schema Draft 2020-12 from your dataclasses for API documentation, validation, and tooling integration.

## Basic Usage

```python
import dataclasses
import json

import marshmallow_recipe as mr


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class User:
    id: int
    name: str
    email: str
    age: int | None = None


# Generate JSON Schema
schema = mr.json_schema(User)
print(json.dumps(schema, indent=2))
```

Output:
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "title": "User",
  "properties": {
    "id": {"type": "integer"},
    "name": {"type": "string"},
    "email": {"type": "string"},
    "age": {"type": "integer"}
  },
  "required": ["id", "name", "email"]
}
```

## Field Descriptions

Add documentation to your schema using field descriptions:

```python
from typing import Annotated


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Product:
    id: Annotated[int, mr.meta(description="Unique product identifier")]
    name: Annotated[str, mr.meta(description="Product display name")]
    price: Annotated[float, mr.meta(description="Price in USD")]
    tags: Annotated[
        list[str],
        mr.list_meta(
            description="Product categories and tags",
            item_description="A single tag or category"
        )
    ]


schema = mr.json_schema(Product)
```

Output includes descriptions:
```json
{
  "properties": {
    "id": {
      "type": "integer",
      "description": "Unique product identifier"
    },
    "name": {
      "type": "string",
      "description": "Product display name"
    },
    "tags": {
      "type": "array",
      "items": {
        "type": "string",
        "description": "A single tag or category"
      },
      "description": "Product categories and tags"
    }
  }
}
```

## Schema-Level Documentation

Use `@mr.options()` to add title and description to the entire schema:

```python
@mr.options(
    title="User Profile",
    description="A registered user account in the system"
)
@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class User:
    username: str
    email: str


schema = mr.json_schema(User)
# Title: "User Profile"
# Description: "A registered user account in the system"
```

You can also override the title when generating the schema:

```python
schema = mr.json_schema(User, title="Custom Title")
```

## Supported Types

All standard Python types are automatically mapped to JSON Schema types:

```python
import datetime
import decimal
import enum
import uuid


class Status(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class TypesDemo:
    # Primitives
    text: str                    # "type": "string"
    count: int                   # "type": "integer"
    price: float                 # "type": "number"
    active: bool                 # "type": "boolean"

    # Date/Time with format
    created: datetime.datetime   # "type": "string", "format": "date-time"
    date: datetime.date          # "type": "string", "format": "date"
    time: datetime.time          # "type": "string", "format": "time"
    uid: uuid.UUID               # "type": "string", "format": "uuid"

    # Decimal (as string by default)
    amount: decimal.Decimal      # "type": "string"

    # Enums with values
    status: Status               # "type": "string", "enum": ["active", "inactive"]

    # Collections
    tags: list[str]              # "type": "array", "items": {"type": "string"}
    unique: set[int]             # "type": "array", "uniqueItems": true, "items": {"type": "integer"}
    mapping: dict[str, int]      # "type": "object", "additionalProperties": {"type": "integer"}
```

## Decimal Representation

Control how decimals are represented in the schema:

```python
@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Pricing:
    # As string (default - matches marshmallow behavior)
    price_str: Annotated[decimal.Decimal, mr.decimal_meta(as_string=True)]

    # As number
    price_num: Annotated[decimal.Decimal, mr.decimal_meta(as_string=False)]


schema = mr.json_schema(Pricing)
# price_str: {"type": "string"}
# price_num: {"type": "number"}
```

## Decimal Range Constraints

Use `decimal_meta` range parameters to emit JSON Schema validation keywords:

```python
@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Invoice:
    amount: Annotated[decimal.Decimal, mr.decimal_meta(gt=decimal.Decimal("0"), lte=decimal.Decimal("999999.99"))]


schema = mr.json_schema(Invoice)
```

Output:
```json
{
  "properties": {
    "amount": {
      "type": "string",
      "exclusiveMinimum": "0",
      "maximum": "999999.99"
    }
  },
  "required": ["amount"]
}
```

The mapping is: `gt` → `exclusiveMinimum`, `gte` → `minimum`, `lt` → `exclusiveMaximum`, `lte` → `maximum`. Values are strings to match the decimal `type: "string"` representation.

## Union Types

Union types are mapped to `anyOf`:

```python
@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class FlexibleData:
    value: str | int
    optional: str | None = None


schema = mr.json_schema(FlexibleData)
```

Output:
```json
{
  "properties": {
    "value": {
      "anyOf": [
        {"type": "string"},
        {"type": "integer"}
      ]
    },
    "optional": {
      "type": "string"
    }
  },
  "required": ["value"]
}
```

## Nested Dataclasses

Nested types are automatically handled using `$defs` and `$ref`:

```python
@mr.options(description="Street address")
@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Address:
    street: str
    city: str
    country: str


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Person:
    name: str
    address: Address


schema = mr.json_schema(Person)
```

Output:
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "title": "Person",
  "properties": {
    "name": {"type": "string"},
    "address": {"$ref": "#/$defs/Address"}
  },
  "required": ["name", "address"],
  "$defs": {
    "Address": {
      "type": "object",
      "title": "Address",
      "description": "Street address",
      "properties": {
        "street": {"type": "string"},
        "city": {"type": "string"},
        "country": {"type": "string"}
      },
      "required": ["street", "city", "country"]
    }
  }
}
```

## Cyclic References

Self-referential types work correctly:

```python
@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class TreeNode:
    value: int
    children: list["TreeNode"] = dataclasses.field(default_factory=list)
    parent: "TreeNode | None" = None


schema = mr.json_schema(TreeNode)
# Uses $ref to handle cycles without infinite recursion
```

## Naming Case Conversion

Apply naming conventions consistently:

```python
@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class UserData:
    user_name: str
    email_address: str
    phone_number: str | None = None


# Convert to camelCase
schema = mr.json_schema(UserData, naming_case=mr.CAMEL_CASE)
# Properties: userName, emailAddress, phoneNumber

# Or set it on the class
@mr.options(naming_case=mr.CAMEL_CASE)
@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class UserData:
    user_name: str
    email_address: str
```

## Default Values

Fields with defaults are not in the `required` array and include default values:

```python
@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class Config:
    host: str
    port: int = 8080
    debug: bool = False


schema = mr.json_schema(Config)
```

Output:
```json
{
  "properties": {
    "host": {"type": "string"},
    "port": {"type": "integer", "default": 8080},
    "debug": {"type": "boolean", "default": false}
  },
  "required": ["host"]
}
```

## Integration Examples

### OpenAPI/Swagger

```python
# Generate schema for API documentation
user_schema = mr.json_schema(User)

openapi_spec = {
    "components": {
        "schemas": {
            "User": user_schema
        }
    }
}
```

### FastAPI Integration

```python
from fastapi import FastAPI
from pydantic import BaseModel


# Convert your dataclass schema to Pydantic if needed
# Or use the JSON Schema directly for documentation
app = FastAPI()

@app.get("/users/{user_id}")
async def get_user(user_id: int) -> dict:
    """
    Get user by ID.

    Returns schema matching:
    {json.dumps(mr.json_schema(User), indent=2)}
    """
    return {"id": user_id, "name": "John", "email": "john@example.com"}
```

### JSON Schema Validation

```python
import jsonschema


# Generate schema
schema = mr.json_schema(User)

# Validate data against it
data = {"id": 1, "name": "Alice", "email": "alice@example.com"}
jsonschema.validate(instance=data, schema=schema)
```

## Performance Note

Unlike `mr.schema()` which caches marshmallow Schema objects, `mr.json_schema()` generates fresh dictionaries on each call (similar to `mr.dump()`). This ensures no shared state between calls and prevents mutation issues. The generation is fast enough for typical use cases.
